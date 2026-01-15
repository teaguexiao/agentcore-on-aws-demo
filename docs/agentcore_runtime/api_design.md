# Runtime 模块 API 设计文档

> 版本: v1.0
> 日期: 2025-01-14

## 1. 概述

本文档定义 Runtime 模块迭代所需的后端 API 设计，包括数据模型、端点定义、请求/响应格式。

## 2. 数据模型

### 2.1 WorkspaceInfo

工作空间信息结构：

```python
from dataclasses import dataclass, field
from typing import Optional
import time

@dataclass
class WorkspaceInfo:
    workspace_id: str              # 唯一ID，也是目录名
    user_session_id: str           # 关联的用户 session_id (来自 cookie)
    workspace_path: str            # 完整路径: /tmp/agentcore_workspaces/{workspace_id}
    created_at: float = field(default_factory=time.time)
    runtime_id: Optional[str] = None  # 如果有部署的 runtime，记录其 ID
```

### 2.2 全局存储

```python
# 用户工作空间映射
# key: user_session_id (来自登录 cookie)
# value: WorkspaceInfo
user_workspaces: Dict[str, WorkspaceInfo] = {}
```

### 2.3 常量定义

```python
WORKSPACE_BASE_PATH = "/tmp/agentcore_workspaces"
SSE_HEARTBEAT_INTERVAL = 15  # 秒
FILE_TREE_MAX_DEPTH = 5
FILE_TREE_MAX_FILES = 100
```

## 3. API 端点设计

### 3.1 工作空间管理

#### 3.1.1 初始化工作空间

**端点**: `POST /api/runtime/workspace/init`

**认证**: 需要登录 (`Depends(get_current_user)`)

**请求**: 无请求体

**响应**:
```json
// 成功
{
    "success": true,
    "workspace_id": "ws_1705234567_a1b2c3d4",
    "workspace_path": "/tmp/agentcore_workspaces/ws_1705234567_a1b2c3d4",
    "message": "工作目录初始化成功"
}

// 失败 - 已存在
{
    "success": false,
    "message": "已存在工作目录，请先清理",
    "existing_workspace_id": "ws_1705234567_a1b2c3d4"
}
```

**后端逻辑**:
```python
@runtime_router.post("/workspace/init")
async def init_workspace(request: Request, user: dict = Depends(get_current_user)):
    user_session_id = request.cookies.get("session_id")

    # 检查是否已有工作目录
    if user_session_id in user_workspaces:
        existing = user_workspaces[user_session_id]
        return JSONResponse({
            "success": False,
            "message": "已存在工作目录，请先清理",
            "existing_workspace_id": existing.workspace_id
        })

    # 生成唯一 ID
    workspace_id = f"ws_{int(time.time())}_{secrets.token_hex(4)}"
    workspace_path = os.path.join(WORKSPACE_BASE_PATH, workspace_id)

    # 创建目录
    os.makedirs(workspace_path, exist_ok=True)

    # 保存信息
    user_workspaces[user_session_id] = WorkspaceInfo(
        workspace_id=workspace_id,
        user_session_id=user_session_id,
        workspace_path=workspace_path
    )

    return JSONResponse({
        "success": True,
        "workspace_id": workspace_id,
        "workspace_path": workspace_path,
        "message": "工作目录初始化成功"
    })
```

---

#### 3.1.2 获取工作空间状态

**端点**: `GET /api/runtime/workspace/status`

**认证**: 需要登录

**响应**:
```json
// 已初始化
{
    "initialized": true,
    "workspace_id": "ws_1705234567_a1b2c3d4",
    "workspace_path": "/tmp/agentcore_workspaces/ws_1705234567_a1b2c3d4",
    "created_at": 1705234567.123,
    "runtime_id": null,
    "has_runtime": false
}

// 未初始化
{
    "initialized": false,
    "workspace_id": null,
    "workspace_path": null
}
```

---

#### 3.1.3 清理工作空间

**端点**: `POST /api/runtime/workspace/cleanup`

**认证**: 需要登录

**响应**:
```json
// 成功
{
    "success": true,
    "message": "工作目录已清理"
}

// 失败 - 存在 Runtime
{
    "success": false,
    "message": "请先清理 Runtime 环境",
    "runtime_id": "RUNTIME123456789"
}

// 失败 - 不存在
{
    "success": false,
    "message": "没有工作目录"
}
```

**后端逻辑**:
```python
@runtime_router.post("/workspace/cleanup")
async def cleanup_workspace(request: Request, user: dict = Depends(get_current_user)):
    user_session_id = request.cookies.get("session_id")
    workspace = user_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "没有工作目录"})

    # 检查是否有部署的 runtime
    if workspace.runtime_id:
        return JSONResponse({
            "success": False,
            "message": "请先清理 Runtime 环境",
            "runtime_id": workspace.runtime_id
        })

    # 删除目录
    if os.path.exists(workspace.workspace_path):
        shutil.rmtree(workspace.workspace_path)

    del user_workspaces[user_session_id]

    return JSONResponse({"success": True, "message": "工作目录已清理"})
```

---

### 3.2 命令执行

#### 3.2.1 执行命令（SSE 流式）

**端点**: `GET /api/runtime/workspace/execute`

**认证**: 需要登录

**查询参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| command | string | 是 | 要执行的 shell 命令（URL 编码） |

**响应**: SSE 流

**SSE 消息格式**:
```json
// 输出行
{"type": "stdout", "line": "Initialized project...", "timestamp": 1705234567.123}
{"type": "stderr", "line": "Warning: ...", "timestamp": 1705234567.456}

// 心跳（每 15 秒）
{"type": "heartbeat", "timestamp": 1705234567.789}

// 完成
{
    "type": "done",
    "success": true,
    "return_code": 0,
    "duration": 5.234,
    "files": [
        {"name": "main.py", "type": "file", "size": 1234},
        {"name": "build", "type": "directory", "children": [...]}
    ]
}

// 错误
{
    "type": "error",
    "message": "请先初始化工作环境"
}
```

**后端逻辑**:
```python
@runtime_router.get("/workspace/execute")
async def execute_command_stream(
    request: Request,
    command: str,
    user: dict = Depends(get_current_user)
):
    user_session_id = request.cookies.get("session_id")
    workspace = user_workspaces.get(user_session_id)

    if not workspace:
        async def error_generator():
            yield f"data: {json.dumps({'type': 'error', 'message': '请先初始化工作环境'})}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")

    async def generate():
        start_time = time.time()
        last_heartbeat = time.time()

        # 创建子进程
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=workspace.workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async def read_stream(stream, stream_type):
            while True:
                line = await stream.readline()
                if not line:
                    break
                yield {
                    "type": stream_type,
                    "line": line.decode('utf-8', errors='replace').rstrip('\n'),
                    "timestamp": time.time()
                }

        # 并发读取 stdout 和 stderr
        stdout_task = asyncio.create_task(read_output(process.stdout, "stdout"))
        stderr_task = asyncio.create_task(read_output(process.stderr, "stderr"))

        # 合并输出流并发送，同时检查心跳
        # ... (完整实现见下方)

        await process.wait()

        # 获取文件树
        files = get_file_tree(workspace.workspace_path)

        # 发送完成消息
        yield f"data: {json.dumps({
            'type': 'done',
            'success': process.returncode == 0,
            'return_code': process.returncode,
            'duration': time.time() - start_time,
            'files': files
        })}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

### 3.3 文件操作

#### 3.3.1 写入文件

**端点**: `POST /api/runtime/workspace/write-file`

**认证**: 需要登录

**请求体**:
```json
{
    "file_path": "agentcore_runtime_direct_deploy/main.py",
    "content": "from bedrock_agentcore import ...\n\n@app.entrypoint\ndef handler(...):\n    ..."
}
```

**响应**:
```json
// 成功
{
    "success": true,
    "file_path": "/tmp/agentcore_workspaces/ws_xxx/agentcore_runtime_direct_deploy/main.py",
    "size": 1234,
    "message": "文件写入成功",
    "files": [...]  // 更新后的文件树
}

// 失败
{
    "success": false,
    "message": "请先初始化工作环境"
}
```

**后端逻辑**:
```python
class WriteFileRequest(BaseModel):
    file_path: str
    content: str

@runtime_router.post("/workspace/write-file")
async def write_file(
    request: Request,
    body: WriteFileRequest,
    user: dict = Depends(get_current_user)
):
    user_session_id = request.cookies.get("session_id")
    workspace = user_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "请先初始化工作环境"})

    # 构建完整路径
    full_path = os.path.join(workspace.workspace_path, body.file_path)

    # 安全检查：确保路径在工作空间内
    if not os.path.abspath(full_path).startswith(workspace.workspace_path):
        return JSONResponse({"success": False, "message": "非法文件路径"})

    # 创建父目录
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # 写入文件
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(body.content)

    # 获取文件树
    files = get_file_tree(workspace.workspace_path)

    return JSONResponse({
        "success": True,
        "file_path": full_path,
        "size": len(body.content.encode('utf-8')),
        "message": "文件写入成功",
        "files": files
    })
```

---

#### 3.3.2 获取文件树

**端点**: `GET /api/runtime/workspace/files`

**认证**: 需要登录

**响应**:
```json
{
    "success": true,
    "workspace_path": "/tmp/agentcore_workspaces/ws_xxx",
    "files": [
        {
            "name": "agentcore_runtime_direct_deploy",
            "type": "directory",
            "children": [
                {"name": "main.py", "type": "file", "size": 1234},
                {"name": "requirements.txt", "type": "file", "size": 256},
                {
                    "name": "build",
                    "type": "directory",
                    "children": [
                        {"name": "strands_agents", "type": "directory", "children": [...]},
                        {"name": "deployment_package.zip", "type": "file", "size": 15728640}
                    ]
                }
            ]
        }
    ],
    "total_files": 15,
    "total_size": 16000000
}
```

**后端逻辑**:
```python
def get_file_tree(base_path: str, max_depth: int = 5, max_files: int = 100) -> List[dict]:
    """递归获取文件树结构"""
    result = []
    file_count = [0]  # 使用列表以便在递归中修改

    def scan_dir(path: str, depth: int) -> List[dict]:
        if depth > max_depth or file_count[0] >= max_files:
            return []

        items = []
        try:
            entries = sorted(os.listdir(path))
            for entry in entries:
                if file_count[0] >= max_files:
                    break

                full_path = os.path.join(path, entry)
                file_count[0] += 1

                if os.path.isdir(full_path):
                    children = scan_dir(full_path, depth + 1)
                    items.append({
                        "name": entry,
                        "type": "directory",
                        "children": children
                    })
                else:
                    items.append({
                        "name": entry,
                        "type": "file",
                        "size": os.path.getsize(full_path)
                    })
        except PermissionError:
            pass

        return items

    return scan_dir(base_path, 0)
```

---

### 3.4 登录验证修复

需要为现有端点添加登录验证：

```python
# 需要修改的现有端点：

@runtime_router.get("/demo/step2-stream")
async def step2_init_project_stream(
    session_id: str,
    request: Request,
    user: dict = Depends(get_current_user)  # 添加
):
    ...

@runtime_router.get("/demo/step3-stream")
async def step3_create_agent_stream(
    session_id: str,
    request: Request,
    user: dict = Depends(get_current_user)  # 添加
):
    ...

# 以此类推，所有端点都需要添加
```

---

## 4. SSE 协议详细设计

### 4.1 消息类型

| type | 说明 | 字段 |
|------|------|------|
| stdout | 标准输出 | line, timestamp |
| stderr | 标准错误 | line, timestamp |
| heartbeat | 心跳 | timestamp |
| done | 执行完成 | success, return_code, duration, files |
| error | 错误 | message |

### 4.2 心跳机制

```python
async def generate_with_heartbeat():
    last_heartbeat = time.time()

    while not done:
        # 检查是否需要发送心跳
        if time.time() - last_heartbeat > SSE_HEARTBEAT_INTERVAL:
            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
            last_heartbeat = time.time()

        # 处理输出...
        await asyncio.sleep(0.1)  # 短暂等待，避免 CPU 占用过高
```

### 4.3 前端 SSE 处理

```javascript
const eventSource = new EventSource(url);

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);

    switch (data.type) {
        case 'stdout':
            appendLog(data.line, 'stdout');
            break;
        case 'stderr':
            appendLog(data.line, 'stderr');
            break;
        case 'heartbeat':
            // 忽略或更新"连接中"状态
            break;
        case 'done':
            eventSource.close();
            showResult(data);
            updateFileTree(data.files);
            break;
        case 'error':
            eventSource.close();
            showError(data.message);
            break;
    }
};

eventSource.onerror = function(event) {
    // 连接错误处理
    eventSource.close();
    showError('连接断开');
};
```

---

## 5. 与现有 API 的集成

### 5.1 Runtime 部署时关联工作空间

当 `step5-deploy-stream` 成功创建 Runtime 后，需要将 runtime_id 关联到工作空间：

```python
# 在 step5_deploy_runtime_stream 中添加：
user_session_id = request.cookies.get("session_id")
if user_session_id in user_workspaces:
    user_workspaces[user_session_id].runtime_id = runtime_id
```

### 5.2 Runtime 清理时解除关联

当 `step8-cleanup` 删除 Runtime 后，清除工作空间的 runtime_id：

```python
# 在 step8_cleanup_runtime 中添加：
user_session_id = request.cookies.get("session_id")
if user_session_id in user_workspaces:
    user_workspaces[user_session_id].runtime_id = None
```

---

## 6. 错误处理

### 6.1 HTTP 错误码

| 场景 | 状态码 | 消息 |
|------|--------|------|
| 未登录 | 401 | Unauthorized |
| 工作空间不存在 | 400 | 请先初始化工作环境 |
| 工作空间已存在 | 400 | 已存在工作目录，请先清理 |
| 存在 Runtime | 400 | 请先清理 Runtime 环境 |
| 非法文件路径 | 400 | 非法文件路径 |
| 服务器错误 | 500 | Internal Server Error |

### 6.2 日志记录

所有 API 调用需要记录日志：

```python
logger.info(f"[Workspace Init] user={user_session_id}, workspace={workspace_id}")
logger.info(f"[Execute Command] user={user_session_id}, command={command[:50]}...")
logger.error(f"[Execute Error] user={user_session_id}, error={str(e)}")
```
