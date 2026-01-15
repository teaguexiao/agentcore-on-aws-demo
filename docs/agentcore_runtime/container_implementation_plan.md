# Container Deployment 实现计划

> 日期: 2025-01-15
> 基于: container_requirements.md

## 实现概览

将 Container Deployment 从 Mock 改造为真实执行，共涉及 3 个文件的修改。

## 任务拆分

### Phase 1: 后端 API (agentcore_runtime_api.py)

#### Task 1.1: 新增数据结构和常量
- 新增 `CONTAINER_WORKSPACE_BASE_PATH = "/tmp/agentcore_container_workspaces"`
- 新增 `ContainerWorkspaceInfo` dataclass
- 新增 `container_workspaces: Dict[str, ContainerWorkspaceInfo]` 存储
- 在 `init_runtime_vars()` 中创建 Container 工作空间基础目录

#### Task 1.2: 新增 Container 工作空间管理 API
- `POST /container/workspace/init` - 初始化工作空间
- `GET /container/workspace/status` - 获取状态
- `POST /container/workspace/cleanup` - 清理工作空间
- `POST /container/workspace/clear-runtime` - 清除 Runtime 关联

#### Task 1.3: 新增 Container 执行 API
- `GET /container/workspace/execute` - Shell 命令执行 (SSE)
- `POST /container/workspace/write-file` - 文件写入
- `POST /container/workspace/execute-python` - Python 代码执行 (SSE)

#### Task 1.4: 删除旧的 Mock API
- 删除 `container_step1_init_project_stream`
- 删除 `container_step2_create_agent_stream`
- 删除 `container_step3_create_dockerfile_stream`
- 删除 `container_step4_buildx_setup_stream`
- 删除 `container_step5_build_push_stream`
- 删除 `container_step6_deploy_stream`

---

### Phase 2: 前端 HTML (templates/agentcore-runtime.html)

#### Task 2.1: 更新 Container Tab 结构
重写 `#container-tab` 内容，按以下结构：

```
Part 0: 工作空间管理
  - 初始化/清理按钮
  - 工作空间状态显示

Part 1: 前置要求 (静态文本)
  - Docker 环境检查
  - ECR 仓库要求
  - IAM 权限说明
  - buildx 检查说明

Part 2: 初始化项目
  - 可编辑命令输入框 (textarea)
  - 执行按钮
  - 日志输出区
  - 文件树显示区

Part 3: 创建 agent.py
  - 文件路径输入框
  - 可编辑代码输入框 (textarea)
  - 写入按钮
  - 文件树显示区

Part 4: 创建 requirements.txt
  - 文件路径输入框
  - 可编辑内容输入框 (textarea)
  - 写入按钮
  - 文件树显示区

Part 5: 创建 Dockerfile
  - 文件路径输入框
  - 可编辑内容输入框 (textarea)
  - 写入按钮
  - 文件树显示区

Part 6: ECR 登录
  - 可编辑命令输入框 (textarea)
  - 执行按钮
  - 日志输出区

Part 7: Docker 构建并推送
  - 可编辑命令输入框 (textarea)
  - 执行按钮
  - 日志输出区 (构建日志会很长)
  - 文件树显示区

Part 8: 部署 Container Runtime
  - 可编辑 Python 代码 (textarea)
  - 执行按钮
  - 保存/重置按钮
  - 日志输出区
  - 结果显示区

Part 9: 查询 Runtime 状态
  - Runtime ID 输入框 (自动填充)
  - 可编辑 Python 代码 (textarea)
  - 执行按钮
  - 结果显示区

Part 10: 调用 Agent
  - Runtime ARN 输入框 (自动填充)
  - Session ID 输入框
  - Prompt 输入框
  - 可编辑 Python 代码 (textarea)
  - 执行按钮
  - 结果显示区

Part 11: 清理 Runtime
  - Runtime ID 输入框 (自动填充)
  - 可编辑 Python 代码 (textarea)
  - 执行按钮
  - 结果显示区
```

---

### Phase 3: 前端 JS (static/js/runtime-container.js)

#### Task 3.1: 重写状态管理
```javascript
const ContainerWorkspaceState = {
    initialized: false,
    workspace_id: null,
    workspace_path: null,
    runtime_id: null,
    runtime_arn: null,
    ecr_image_uri: null
};
```

#### Task 3.2: 实现工作空间管理函数
- `initContainerWorkspace()` - 初始化
- `cleanupContainerWorkspace()` - 清理
- `loadContainerWorkspaceStatus()` - 加载状态
- `updateContainerWorkspaceUI()` - 更新 UI

#### Task 3.3: 实现命令执行函数
- `executeContainerCommand(partId, command)` - Shell 命令 (SSE)
- `writeContainerFile(partId, filePath, content)` - 文件写入
- `executeContainerPython(partId, code)` - Python 代码 (SSE)

#### Task 3.4: 实现各 Part 执行函数
- `executeContainerPart2()` - 初始化项目
- `executeContainerPart3()` - 写入 agent.py
- `executeContainerPart4()` - 写入 requirements.txt
- `executeContainerPart5()` - 写入 Dockerfile
- `executeContainerPart6()` - ECR 登录
- `executeContainerPart7()` - Docker 构建推送
- `executeContainerPart8()` - 部署 Runtime
- `executeContainerPart9()` - 查询状态
- `executeContainerPart10()` - 调用 Agent
- `executeContainerPart11()` - 清理 Runtime

#### Task 3.5: 实现辅助函数
- `renderContainerFileTree(files, containerId)` - 渲染文件树
- `autoFillContainerRuntimeInfo()` - 自动填充 Runtime 信息
- `updateContainerDemoCodeVariables()` - 更新代码模板变量
- `saveContainerCodeTemplate(partId)` - 保存代码模板
- `resetContainerCodeTemplate(partId)` - 重置代码模板

#### Task 3.6: 实现页面初始化
- 页面加载时检查工作空间状态
- 自动填充已保存的信息
- 更新代码模板中的环境变量

---

## 默认模板内容

### Part 2: 初始化项目命令
```bash
uv init --no-readme
uv add strands-agents boto3
```

### Part 3: agent.py
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
    result = handler({"prompt": "What is 2+2?"}, None)
    print(result)
```

### Part 4: requirements.txt
```
strands-agents>=0.1.0
boto3>=1.35.0
```

### Part 5: Dockerfile
```dockerfile
FROM public.ecr.aws/lambda/python:3.12-arm64

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent.py .

CMD ["agent.handler"]
```

### Part 6: ECR 登录命令
```bash
aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com
```

### Part 7: Docker 构建推送命令
```bash
docker buildx build --platform linux/arm64 \
  -t {ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{CONTAINER_ECR_REPOSITORY_NAME}:{CONTAINER_IMAGE_TAG} \
  --cache-from type=registry,ref={ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{CONTAINER_ECR_REPOSITORY_NAME}:cache \
  --cache-to type=registry,ref={ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{CONTAINER_ECR_REPOSITORY_NAME}:cache,mode=max \
  --push .
```

### Part 8: 部署 Runtime Python 代码
```python
import boto3
import json

# 配置
REGION = "{REGION}"
CONTAINER_IMAGE_URI = "{ECR_IMAGE_URI}"
ROLE_ARN = "{CONTAINER_EXECUTION_ROLE_ARN}"
AGENT_NAME = "container_demo_{timestamp}"

# 创建客户端
client = boto3.client('bedrock-agentcore-control', region_name=REGION)

print(f"正在创建 Container Runtime: {AGENT_NAME}")
print(f"镜像 URI: {CONTAINER_IMAGE_URI}")

# 创建 Runtime
response = client.create_agent_runtime(
    agentRuntimeName=AGENT_NAME,
    agentRuntimeArtifact={
        'containerConfiguration': {
            'containerUri': CONTAINER_IMAGE_URI
        }
    },
    networkConfiguration={"networkMode": "PUBLIC"},
    roleArn=ROLE_ARN
)

runtime_arn = response['agentRuntimeArn']
runtime_id = response['agentRuntimeId']

print(f"\n✓ Runtime 创建成功!")
print(f"Runtime ARN: {runtime_arn}")
print(f"Runtime ID: {runtime_id}")
print(f"Status: CREATING")

# 输出结果供前端解析
print(f"\n__RESULT__:{json.dumps({'runtime_arn': runtime_arn, 'runtime_id': runtime_id, 'agent_name': AGENT_NAME})}")
```

### Part 9-11: (类似 Direct Code 的 Part 6-8)

---

## 执行顺序

建议按以下顺序实现：

1. **Phase 1** (后端) - 先完成 API，可以用 curl 测试
2. **Phase 2** (HTML) - 搭建 UI 结构
3. **Phase 3** (JS) - 实现交互逻辑

---

## 预估工作量

| Phase | 任务数 | 复杂度 |
|-------|-------|--------|
| Phase 1 后端 | 4 | 中（大部分是复制修改） |
| Phase 2 HTML | 1 | 中（结构较长） |
| Phase 3 JS | 6 | 高（逻辑较多） |

---

## 测试要点

1. **工作空间隔离**: Direct Code 和 Container 工作空间独立
2. **SSE 心跳**: Docker 构建时连接不断开
3. **文件树更新**: 每步执行后正确显示
4. **Runtime 信息传递**: Part 8 结果正确填充到 Part 9-11
5. **登录验证**: 未登录时返回 401
