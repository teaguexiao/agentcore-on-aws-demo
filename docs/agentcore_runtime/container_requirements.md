# Container Deployment 模块迭代需求文档

> 版本: v1.0
> 日期: 2025-01-15
> 状态: 需求确认完成

## 1. 背景

当前 Container Deployment 部分（Runtime 模块的 Tab 2）有多个步骤是 Mock 实现，只是模拟输出预设的日志行，实际上没有真正执行任何命令。

### 1.1 当前状态

| 步骤 | 当前状态 | 说明 |
|------|---------|------|
| Step 1 | **Mock** | 初始化项目 |
| Step 2 | **Mock** | 创建 agent.py |
| Step 3 | **Mock** | 创建 Dockerfile |
| Step 4 | **Mock** | 设置 Docker Buildx |
| Step 5 | **Mock** | 构建并推送镜像 |
| Step 6 | 真实API | 部署 Container Runtime |
| Step 7-9 | 真实API | 查询状态/调用/清理（复用 Direct Code） |

### 1.2 问题

- Mock 步骤无法让用户体验真实的命令执行过程
- 用户无法自定义 Agent 代码或 Dockerfile
- 无法看到真实的 Docker 构建日志
- 无法在自己的 ECR 仓库中看到推送的镜像

## 2. 目标

将 Container Deployment 部分的 Mock 步骤改造为真实后端执行，实现：

1. **独立工作空间**: 与 Direct Code Deployment 分离的工作目录
2. **真实命令执行**: 所有命令在服务器后端真实执行
3. **用户可编辑**: 用户可以修改命令、代码、配置文件
4. **实时输出**: 通过 SSE 流式返回 stdout/stderr（特别是 Docker 构建日志）
5. **文件可视化**: 每步执行后显示工作目录文件变化
6. **可编辑 Python 代码**: Part 8-11 使用可编辑的 Python 代码执行 boto3 API

## 3. 功能需求

### 3.1 工作目录管理（独立于 Direct Code）

#### 3.1.1 初始化工作目录

- **触发**: 用户点击"初始化工作环境"按钮
- **行为**:
  - 生成唯一的 workspace_id（前缀 `container_`）
  - 在 `/tmp/agentcore_container_workspaces/{workspace_id}` 创建目录
  - 关联到当前登录用户的 session_id
- **约束**: 每个用户同时只能有一个 Container 工作目录
- **输出**: 显示 workspace_id 和完整路径

#### 3.1.2 清理工作目录

- **触发**: 用户点击"清理工作环境"按钮
- **前置条件**: 当前用户没有已部署的 Container Runtime 环境
- **行为**: 删除工作目录及所有内容
- **输出**: 清理成功/失败提示

#### 3.1.3 工作目录状态

- **显示**: 工作目录是否已初始化、workspace_id、路径
- **持久化**: 页面刷新后能恢复状态（基于登录用户的 session_id）

### 3.2 命令执行

#### 3.2.1 执行方式

- **环境**: 在服务器本地执行，工作目录为隔离的临时目录
- **输出**: 通过 SSE 流式返回 stdout/stderr
- **心跳**: SSE 连接需要心跳机制防止超时断开
- **超时**: 不设置命令执行超时（Docker 构建可能很长）

#### 3.2.2 用户可编辑

- 用户可以完全自由编辑 shell 命令
- 前端提供默认命令模板
- 安全提示: 显示警告说明命令将在服务器执行

### 3.3 文件写入

#### 3.3.1 代码/配置文件创建

- **触发**: Part 3 (agent.py), Part 4 (requirements.txt), Part 5 (Dockerfile)
- **输入**:
  - 文件路径（相对于工作目录）
  - 文件内容
- **行为**: 后端写入文件到指定路径
- **输出**: 写入成功/失败 + 更新后的文件树

### 3.4 文件展示

#### 3.4.1 展示时机

- 每步执行完成后自动刷新显示

#### 3.4.2 展示内容

- 当前工作目录路径
- 文件树结构（递归显示子目录）
- 文件大小
- 区分文件和目录图标

#### 3.4.3 展示位置

- 在每个步骤卡片的输出区域下方显示

### 3.5 Python 代码编辑与执行

#### 3.5.1 适用步骤

- Part 8: 部署 Container Runtime
- Part 9: 查询 Runtime 状态
- Part 10: 调用 Agent
- Part 11: 清理 Runtime

#### 3.5.2 功能

- 提供默认 Python 代码模板（带变量占位符）
- 用户可以完全编辑代码
- 执行时在工作空间目录下运行
- 返回执行结果（stdout/stderr）
- 支持保存/重置代码模板

### 3.6 登录验证

- 所有 Container API 端点必须添加 `Depends(get_current_user)` 验证
- 未登录用户调用 API 返回 401 错误

### 3.7 步骤流程

改造后的步骤流程：

| Part | 类型 | 用户输入 | 执行方式 | 说明 |
|------|------|---------|---------|------|
| Part 0 | 新增 | 无 | 初始化工作目录 | 创建独立的 Container 工作空间 |
| Part 1 | 保持 | 无 | 静态文本 | 前置要求检查（Docker, ECR, IAM） |
| Part 2 | **改造** | 可编辑命令 | SSE 流式执行 | 初始化项目 (uv init, uv add) |
| Part 3 | **改造** | 可编辑代码 + 文件路径 | 后端写入文件 | 创建 agent.py |
| Part 4 | **改造** | 可编辑内容 + 文件路径 | 后端写入文件 | 创建 requirements.txt |
| Part 5 | **改造** | 可编辑内容 + 文件路径 | 后端写入文件 | 创建 Dockerfile |
| Part 6 | **改造** | 可编辑命令 | SSE 流式执行 | ECR 登录 |
| Part 7 | **改造** | 可编辑命令 | SSE 流式执行 | Docker buildx 构建并推送 |
| Part 8 | **改造** | 可编辑 Python 代码 | 执行 Python | 部署 Container Runtime |
| Part 9 | **改造** | 可编辑 Python 代码 | 执行 Python | 查询 Runtime 状态 |
| Part 10 | **改造** | 可编辑 Python 代码 | 执行 Python | 调用 Agent |
| Part 11 | **改造** | 可编辑 Python 代码 | 执行 Python | 清理 Runtime |
| Part 清理 | 新增 | 无 | 清理工作目录 | 删除 Container 工作空间 |

### 3.8 默认模板内容

#### Part 2: 初始化项目

```bash
uv init --no-readme
uv add strands-agents boto3
```

#### Part 3: agent.py

```python
from strands import Agent
from strands.models import BedrockModel

def handler(event, context):
    """AgentCore Runtime Container 入口函数"""
    prompt = event.get("prompt", "Hello!")

    model = BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name="us-west-2"
    )

    agent = Agent(model=model)
    response = agent(prompt)

    return {
        "statusCode": 200,
        "body": str(response)
    }

if __name__ == "__main__":
    # 本地测试
    result = handler({"prompt": "What is 2+2?"}, None)
    print(result)
```

#### Part 4: requirements.txt

```
strands-agents>=0.1.0
boto3>=1.35.0
```

#### Part 5: Dockerfile

```dockerfile
FROM public.ecr.aws/lambda/python:3.12-arm64

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 Agent 代码
COPY agent.py .

# 设置入口点
CMD ["agent.handler"]
```

#### Part 6: ECR 登录

```bash
aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com
```

#### Part 7: Docker 构建并推送

```bash
docker buildx build --platform linux/arm64 \
  -t {ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{CONTAINER_ECR_REPOSITORY_NAME}:{CONTAINER_IMAGE_TAG} \
  --cache-from type=registry,ref={ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{CONTAINER_ECR_REPOSITORY_NAME}:cache \
  --cache-to type=registry,ref={ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{CONTAINER_ECR_REPOSITORY_NAME}:cache,mode=max \
  --push .
```

#### Part 8-11: Python 代码模板

（类似 Direct Code Deployment 的 Part 5-2, 6, 7, 8）

## 4. 非功能需求

### 4.1 安全性

- **风险等级**: 高（允许执行 Docker 命令）
- **使用场景**: 内部演示 / 客户演示
- **安全措施**:
  - 必须登录才能使用
  - 工作目录隔离在 `/tmp/agentcore_container_workspaces/`
  - 前端显示安全警告提示
  - Docker 构建在用户隔离的工作目录中进行

### 4.2 性能

- SSE 心跳间隔: 15 秒
- 文件树最大深度: 5 层
- 文件树最大文件数: 100 个
- Docker 构建不设超时（可能需要几分钟）

### 4.3 可靠性

- 服务重启后工作目录信息丢失（可接受，因为在 /tmp）
- SSE 断开后需要前端能重连
- Docker 构建中断后需要能重新构建

### 4.4 服务器要求

- **Docker**: 必须安装并运行 Docker daemon
- **Docker Buildx**: 必须配置 buildx（用于 arm64 交叉编译）
- **AWS CLI**: 必须安装并配置（用于 ECR 登录）
- **uv**: 推荐安装（用于 Python 依赖管理）

## 5. 用户识别

- 基于登录系统的 session_id（cookie）
- 每个登录用户有独立的 Container 工作目录配额（1个）
- 不同用户的工作目录完全隔离
- Container 工作空间与 Direct Code 工作空间完全独立

## 6. 约束条件

- 工作目录位置: `/tmp/agentcore_container_workspaces/{workspace_id}`
- 每用户最多 1 个 Container 工作目录
- 清理工作目录前必须先清理 Container Runtime
- ECR 镜像不会被自动删除（用户可以复用）
- 不支持文件下载（本期）
- 不支持在线编辑已有文件（本期）

## 7. 验收标准

1. ✅ 用户可以初始化独立的 Container 工作目录
2. ✅ 用户可以在 Part 2 编辑并执行命令，看到实时输出
3. ✅ 用户可以在 Part 3 编辑代码并写入 agent.py
4. ✅ 用户可以在 Part 4 编辑并写入 requirements.txt
5. ✅ 用户可以在 Part 5 编辑并写入 Dockerfile
6. ✅ 用户可以在 Part 6 执行 ECR 登录命令
7. ✅ 用户可以在 Part 7 执行 Docker 构建并推送，看到构建日志
8. ✅ 用户可以在 Part 8 编辑并执行 Python 代码部署 Runtime
9. ✅ 用户可以在 Part 9 编辑并执行 Python 代码查询状态
10. ✅ 用户可以在 Part 10 编辑并执行 Python 代码调用 Agent
11. ✅ 用户可以在 Part 11 编辑并执行 Python 代码清理 Runtime
12. ✅ 每步执行后显示工作目录文件树
13. ✅ 用户可以清理 Container 工作目录
14. ✅ 所有 API 端点需要登录验证
15. ✅ SSE 连接稳定（心跳机制）

## 8. 与 Direct Code Deployment 的差异

| 方面 | Direct Code | Container |
|------|-------------|-----------|
| 工作目录 | `/tmp/agentcore_workspaces/` | `/tmp/agentcore_container_workspaces/` |
| 部署产物 | zip 包上传 S3 | Docker 镜像推送 ECR |
| 构建时间 | 快（秒级） | 慢（分钟级） |
| 清理范围 | Runtime + S3 文件 | 仅 Runtime（ECR 镜像保留） |
| 服务器要求 | 基本 Python 环境 | Docker + Buildx + AWS CLI |

## 9. API 端点设计

### 9.1 工作空间 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/runtime/container/workspace/init` | POST | 初始化 Container 工作空间 |
| `/api/runtime/container/workspace/cleanup` | POST | 清理 Container 工作空间 |
| `/api/runtime/container/workspace/status` | GET | 获取工作空间状态 |

### 9.2 命令执行 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/runtime/container/execute` | GET (SSE) | 执行 shell 命令 |
| `/api/runtime/container/write-file` | POST | 写入文件 |
| `/api/runtime/container/execute-python` | POST | 执行 Python 代码 |

### 9.3 配置 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/runtime/container/config` | GET | 获取 Container 配置（已有） |

## 10. 确认的决策

1. **buildx 配置检查**: ✅ 在 Part 1 前置要求中检查 `docker buildx` 是否可用
2. **ECR 仓库创建**: ✅ 假设已存在，用户自己提前创建
3. **镜像标签策略**: ✅ 固定 tag（如 `latest`），每次覆盖
4. **构建缓存**: ✅ 使用缓存（`--cache-from`）加速重复构建
5. **工作空间前缀**: ✅ `container_ws_`
6. **Docker 构建超时**: ✅ 不显示预估时间，依赖 SSE 心跳防超时
7. **ECR 登录失败**: ✅ 不需要特殊提示，输出 shell 结果即可
8. **架构方案**: ✅ 方案 A - 独立路由 + 独立存储

## 11. 实现方案

### 11.1 后端架构

```
# Container 工作空间 API（独立于 Direct Code）
POST /api/runtime/demo/container/workspace/init
GET  /api/runtime/demo/container/workspace/status
POST /api/runtime/demo/container/workspace/cleanup
POST /api/runtime/demo/container/workspace/clear-runtime
GET  /api/runtime/demo/container/workspace/execute        # Shell (SSE)
POST /api/runtime/demo/container/workspace/write-file
POST /api/runtime/demo/container/workspace/execute-python # Python (SSE)
```

### 11.2 数据结构

```python
CONTAINER_WORKSPACE_BASE_PATH = "/tmp/agentcore_container_workspaces"

@dataclass
class ContainerWorkspaceInfo:
    workspace_id: str              # 前缀 container_ws_
    user_session_id: str
    workspace_path: str
    created_at: float
    runtime_id: Optional[str] = None
    ecr_image_uri: Optional[str] = None

container_workspaces: Dict[str, ContainerWorkspaceInfo] = {}
```

### 11.3 代码复用

| 功能 | 复用方式 |
|------|---------|
| `get_file_tree()` | 直接复用 |
| 命令执行逻辑 | 复制并修改为使用 container_workspaces |
| 文件写入逻辑 | 复制并修改为使用 container_workspaces |
| Python 执行逻辑 | 复制并修改为使用 container_workspaces |
| 登录验证 | 直接复用 `require_login` |

### 11.4 前端文件

| 文件 | 改造内容 |
|------|---------|
| `runtime-container.js` | 重写，添加工作空间管理、可编辑代码 |
| `agentcore-runtime.html` | 更新 Container Tab HTML |
| `runtime-workspace.css` | 复用现有样式 |
