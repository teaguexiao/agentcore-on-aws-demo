"""
AgentCore Runtime Demo API Module

提供 Runtime 演示的所有 API 端点:
- Mock API: Step 2, 3, 5-package
- 真实 API: Step 5-deploy, 6, 7, 8
- 工作空间管理 API: init, status, cleanup, execute, write-file, files
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends, Cookie
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, validator
import boto3
import os
import json
from typing import Optional, Dict, Any, AsyncGenerator, List
import logging
import time
import asyncio
import secrets
import shutil
from dataclasses import dataclass, field

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/runtime/demo", tags=["runtime"])

# 配置信息 (from environment variables)
ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID")
REGION = os.getenv("AWS_REGION", "us-west-2")

# Direct Code Deployment 配置
DEPLOYMENT_PACKAGE_PATH = os.getenv("DEPLOYMENT_PACKAGE_PATH", "deployment_packages/strands_agent/deployment_package.zip")
S3_BUCKET = os.getenv("S3_BUCKET")
ROLE_ARN = os.getenv("EXECUTION_ROLE_ARN")

# 如果没有配置，则使用默认格式（向后兼容）
if not S3_BUCKET:
    S3_BUCKET = f"bedrock-agentcore-code-{ACCOUNT_ID}-{REGION}"
    logger.warning(f"S3_BUCKET not configured, using default: {S3_BUCKET}")

if not ROLE_ARN:
    ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/AmazonBedrockAgentCoreSDKRuntime-{REGION}"
    logger.warning(f"EXECUTION_ROLE_ARN not configured, using default: {ROLE_ARN}")

# Container Deployment 配置
CONTAINER_ECR_REPOSITORY = os.getenv("CONTAINER_ECR_REPOSITORY_NAME")
CONTAINER_IMAGE_TAG = os.getenv("CONTAINER_IMAGE_TAG", "latest")
CONTAINER_ROLE_ARN = os.getenv("CONTAINER_EXECUTION_ROLE_ARN")

def build_container_image_uri():
    """构建完整的 ECR 镜像 URI"""
    if not CONTAINER_ECR_REPOSITORY or not ACCOUNT_ID or not REGION:
        raise ValueError("缺少必需的环境变量: CONTAINER_ECR_REPOSITORY_NAME, AWS_ACCOUNT_ID, AWS_REGION")
    return f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/{CONTAINER_ECR_REPOSITORY}:{CONTAINER_IMAGE_TAG}"

# 会话状态存储 (内存，生产环境应使用Redis)
runtime_sessions: Dict[str, Dict[str, Any]] = {}

# boto3 客户端 (延迟初始化)
s3_client = None
agentcore_control_client = None
agentcore_client = None
connection_manager = None  # WebSocket 管理器，由 app.py 注入

# ==================== 工作空间管理 ====================

# Direct Code 工作空间常量
WORKSPACE_BASE_PATH = "/tmp/agentcore_workspaces"
SSE_HEARTBEAT_INTERVAL = 15  # 秒
FILE_TREE_MAX_DEPTH = 1
FILE_TREE_MAX_FILES = 100

# Container 工作空间常量
CONTAINER_WORKSPACE_BASE_PATH = "/tmp/agentcore_container_workspaces"

@dataclass
class WorkspaceInfo:
    """Direct Code 工作空间信息"""
    workspace_id: str              # 唯一ID，也是目录名
    user_session_id: str           # 关联的用户 session_id (来自 cookie)
    workspace_path: str            # 完整路径: /tmp/agentcore_workspaces/{workspace_id}
    created_at: float = field(default_factory=time.time)
    runtime_id: Optional[str] = None  # 如果有部署的 runtime，记录其 ID

@dataclass
class ContainerWorkspaceInfo:
    """Container 工作空间信息"""
    workspace_id: str              # 唯一ID，前缀 container_ws_
    user_session_id: str           # 关联的用户 session_id (来自 cookie)
    workspace_path: str            # 完整路径: /tmp/agentcore_container_workspaces/{workspace_id}
    created_at: float = field(default_factory=time.time)
    runtime_id: Optional[str] = None  # 如果有部署的 runtime，记录其 ID
    runtime_arn: Optional[str] = None  # Runtime ARN
    ecr_image_uri: Optional[str] = None  # Container 特有：ECR 镜像 URI

# Direct Code 用户工作空间映射
# key: user_session_id (来自登录 cookie)
# value: WorkspaceInfo
user_workspaces: Dict[str, WorkspaceInfo] = {}

# Container 用户工作空间映射
# key: user_session_id (来自登录 cookie)
# value: ContainerWorkspaceInfo
container_workspaces: Dict[str, ContainerWorkspaceInfo] = {}

# 登录验证相关（从 app.py 注入）
_sessions_dict = None  # 存储 app.py 的 sessions 字典引用

def init_auth(sessions_dict):
    """初始化认证相关变量（从 app.py 调用）"""
    global _sessions_dict
    _sessions_dict = sessions_dict
    logger.info("Runtime API auth initialized")

def get_current_user_for_runtime(request: Request, session_token: str = Cookie(None)):
    """获取当前用户（用于 runtime API 的登录验证）"""
    # 检查是否启用登录
    login_enabled = os.getenv("LOGIN_ENABLE", "true").lower() == "true"

    # 如果登录禁用，返回默认用户
    if not login_enabled:
        return {"username": "default_user", "aws_login": "", "customer_name": "", "session_id": "default_session"}

    # 检查有效会话
    if _sessions_dict and session_token and session_token in _sessions_dict:
        return _sessions_dict[session_token]

    return None

def require_login(request: Request, session_token: str = Cookie(None)):
    """要求登录的依赖项"""
    user = get_current_user_for_runtime(request, session_token)
    if not user:
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    return user

def init_clients():
    """初始化 boto3 客户端"""
    global s3_client, agentcore_control_client, agentcore_client

    if s3_client is None:
        s3_client = boto3.client('s3', region_name=REGION)
        agentcore_control_client = boto3.client('bedrock-agentcore-control', region_name=REGION)
        agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)
        logger.info("Boto3 clients initialized")

def init_runtime_vars(cm, sessions_dict=None):
    """初始化 Runtime API 变量 (从 app.py 调用)"""
    global connection_manager
    connection_manager = cm
    init_clients()
    if sessions_dict is not None:
        init_auth(sessions_dict)
    # 确保工作空间基础目录存在
    os.makedirs(WORKSPACE_BASE_PATH, exist_ok=True)
    os.makedirs(CONTAINER_WORKSPACE_BASE_PATH, exist_ok=True)
    logger.info("Runtime API variables initialized (Direct Code + Container)")

# ==================== 数据模型 ====================

class RuntimeRequest(BaseModel):
    """基础请求模型"""
    session_id: str

class Step2Request(RuntimeRequest):
    """Step 2: 初始化项目"""
    pass

class Step3Request(RuntimeRequest):
    """Step 3: 创建 Agent 代码"""
    pass

class Step5PackageRequest(RuntimeRequest):
    """Step 5: 创建部署包"""
    pass

class Step5DeployRequest(RuntimeRequest):
    """Step 5: 部署 Runtime"""
    agent_name: Optional[str] = None

class Step6StatusRequest(RuntimeRequest):
    """Step 6: 检查 Runtime 状态"""
    runtime_id: str
    runtime_version: str = "1"

class Step7InvokeRequest(RuntimeRequest):
    """Step 7: 调用 Agent"""
    runtime_arn: str
    runtime_session_id: str  # Runtime 的 session ID (至少33个字符)
    prompt: str
    deployment_type: Optional[str] = "code"  # "code" 或 "container"

    @validator('prompt')
    def validate_prompt(cls, v):
        if len(v) > 10000:
            raise ValueError('Prompt 长度不能超过 10000 字符')
        if not v.strip():
            raise ValueError('Prompt 不能为空')
        return v

    @validator('runtime_session_id')
    def validate_runtime_session_id(cls, v):
        if len(v) < 33:
            raise ValueError('Runtime Session ID 长度必须至少 33 个字符')
        return v

    @validator('deployment_type')
    def validate_deployment_type(cls, v):
        if v not in ["code", "container"]:
            raise ValueError('deployment_type 必须是 "code" 或 "container"')
        return v

class Step8CleanupRequest(RuntimeRequest):
    """Step 8: 清理 Runtime"""
    runtime_id: str

# ==================== Helper Functions ====================

async def send_ws_message(session_id: str, message_type: str, data: Any):
    """发送 WebSocket 消息"""
    if connection_manager:
        try:
            await connection_manager.send_to_session(session_id, {
                "type": message_type,
                "data": data,
                "timestamp": time.strftime("%H:%M:%S")
            })
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")

# ==================== Mock API 端点 ====================

@router.get("/step2-stream")
async def step2_init_project_stream(session_id: str):
    """Step 2: 模拟初始化项目 - SSE 流式输出"""
    logger.info(f"Session {session_id}: 执行 Step 2 - 初始化项目 (SSE)")

    async def generate():
        output_lines = [
            "Initialized Python 3.13 project",
            "Created pyproject.toml",
            "Created uv.lock",
            "Created .venv directory",
            "",
            "Added dependencies:",
            "  - bedrock-agentcore",
            "  - strands-agents",
            "",
            "Project setup completed successfully!"
        ]

        for line in output_lines:
            await asyncio.sleep(0.5)  # 每行延迟 0.5 秒
            data = json.dumps({"line": line, "done": False})
            yield f"data: {data}\n\n"

        # 发送完成信号
        final_data = json.dumps({
            "done": True,
            "message": "项目初始化完成",
            "output": "\n".join(output_lines)
        })
        yield f"data: {final_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/step3-stream")
async def step3_create_agent_stream(session_id: str):
    """Step 3: 模拟创建 Agent 代码文件 - SSE 流式输出"""
    logger.info(f"Session {session_id}: 执行 Step 3 - 创建 Agent 代码 (SSE)")

    async def generate():
        output_lines = [
            "Creating Agent code file...",
            "Writing main.py with @app.entrypoint decorator",
            "Setting up BedrockAgentCoreApp instance",
            "Configuring Strands Agent",
            "Adding invoke function",
            "",
            "✓ File created: agentcore_runtime_direct_deploy/main.py",
            "✓ Agent code ready for deployment"
        ]

        for line in output_lines:
            await asyncio.sleep(0.5)  # 每行延迟 0.5 秒
            data = json.dumps({"line": line, "done": False})
            yield f"data: {data}\n\n"

        # 发送完成信号
        final_data = json.dumps({
            "done": True,
            "message": "main.py 创建完成",
            "file_path": "agentcore_runtime_direct_deploy/main.py",
            "output": "\n".join(output_lines)
        })
        yield f"data: {final_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/step5-package-stream")
async def step5_create_package_stream(session_id: str):
    """Step 5: 模拟创建部署包 - SSE 流式输出"""
    logger.info(f"Session {session_id}: 执行 Step 5 (package) - 创建部署包 (SSE)")

    async def generate():
        # 检查预制包是否存在
        if not os.path.exists(DEPLOYMENT_PACKAGE_PATH):
            error_data = json.dumps({
                "done": True,
                "error": f"部署包不存在: {DEPLOYMENT_PACKAGE_PATH}。请先准备 deployment_package.zip"
            })
            yield f"data: {error_data}\n\n"
            return

        file_size = os.path.getsize(DEPLOYMENT_PACKAGE_PATH) / (1024 * 1024)

        output_lines = [
            "Installing dependencies for aarch64-manylinux2014...",
            "Resolving package versions...",
            "Downloading bedrock-agentcore...",
            "Downloading strands-agents...",
            "Installing packages to deployment_package/...",
            "",
            "Creating deployment archive...",
            f"Compressing files... ({file_size:.2f} MB)",
            "",
            "✓ Deployment package created successfully!",
            f"✓ Package location: {DEPLOYMENT_PACKAGE_PATH}",
            f"✓ Package size: {file_size:.2f} MB"
        ]

        for line in output_lines:
            await asyncio.sleep(0.5)  # 每行延迟 0.5 秒
            data = json.dumps({"line": line, "done": False})
            yield f"data: {data}\n\n"

        # 发送完成信号
        final_data = json.dumps({
            "done": True,
            "message": "deployment_package.zip 创建完成",
            "package_size": f"{file_size:.2f} MB",
            "package_path": DEPLOYMENT_PACKAGE_PATH,
            "output": "\n".join(output_lines)
        })
        yield f"data: {final_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# ==================== 真实 API 端点 ====================

@router.get("/step5-deploy-stream")
async def step5_deploy_runtime_stream(session_id: str, agent_name: Optional[str] = None):
    """Step 5: 真实部署 Runtime - SSE 流式输出"""
    init_clients()  # 确保客户端已初始化

    agent_name = agent_name or f"runtime_demo_{int(time.time())}"
    logger.info(f"Session {session_id}: 开始部署 Runtime {agent_name} (SSE)")

    async def generate():
        try:
            # 检查部署包
            if not os.path.exists(DEPLOYMENT_PACKAGE_PATH):
                error_data = json.dumps({
                    "done": True,
                    "error": f"部署包不存在: {DEPLOYMENT_PACKAGE_PATH}"
                })
                yield f"data: {error_data}\n\n"
                return

            # 1. 上传到 S3
            s3_key = f"{agent_name}/deployment_package.zip"
            logger.info(f"上传到 S3: {S3_BUCKET}/{s3_key}")

            # 发送上传进度
            upload_msg = json.dumps({
                "line": f"正在上传到 S3: {S3_BUCKET}/{s3_key}...",
                "done": False
            })
            yield f"data: {upload_msg}\n\n"

            with open(DEPLOYMENT_PACKAGE_PATH, 'rb') as f:
                s3_client.upload_fileobj(
                    f,
                    S3_BUCKET,
                    s3_key,
                    ExtraArgs={'ExpectedBucketOwner': ACCOUNT_ID} if ACCOUNT_ID else {}
                )

            logger.info(f"S3 上传完成: {s3_key}")

            # 上传完成消息
            upload_complete_msg = json.dumps({
                "line": f"✓ S3 上传完成: s3://{S3_BUCKET}/{s3_key}",
                "done": False
            })
            yield f"data: {upload_complete_msg}\n\n"

            # 2. 创建 Runtime
            create_msg = json.dumps({
                "line": f"\n正在创建 AgentCore Runtime: {agent_name}...",
                "done": False
            })
            yield f"data: {create_msg}\n\n"

            logger.info(f"创建 AgentCore Runtime: {agent_name}")
            response = agentcore_control_client.create_agent_runtime(
                agentRuntimeName=agent_name,
                agentRuntimeArtifact={
                    'codeConfiguration': {
                        'code': {
                            's3': {
                                'bucket': S3_BUCKET,
                                'prefix': s3_key
                            }
                        },
                        'runtime': 'PYTHON_3_13',
                        'entryPoint': ['main.py']
                    }
                },
                networkConfiguration={"networkMode": "PUBLIC"},
                roleArn=ROLE_ARN
            )

            runtime_arn = response['agentRuntimeArn']
            runtime_id = response['agentRuntimeId']

            # 保存到会话
            runtime_sessions[session_id] = {
                "deployment_type": "code",
                "runtime_arn": runtime_arn,
                "runtime_id": runtime_id,
                "agent_name": agent_name,
                "s3_key": s3_key,
                "created_at": time.time()
            }

            # 关联到工作空间（如果存在）- 通过遍历查找
            for ws_user_id, ws_info in user_workspaces.items():
                # 工作空间没有关联 runtime 的才关联
                if ws_info.runtime_id is None:
                    ws_info.runtime_id = runtime_id
                    logger.info(f"Workspace {ws_user_id} associated with runtime {runtime_id}")
                    break

            logger.info(f"Runtime 创建成功: {runtime_arn}")

            # 创建完成消息
            create_complete_msg = json.dumps({
                "line": f"✓ Runtime 创建成功!\n\nRuntime ARN: {runtime_arn}\nRuntime ID: {runtime_id}",
                "done": False
            })
            yield f"data: {create_complete_msg}\n\n"

            # 发送完成信号
            final_data = json.dumps({
                "done": True,
                "status": "success",
                "runtime_arn": runtime_arn,
                "runtime_id": runtime_id,
                "runtime_version": "1",
                "agent_name": agent_name,
                "message": "Runtime 部署成功！"
            })
            yield f"data: {final_data}\n\n"

        except Exception as e:
            logger.error(f"部署失败: {str(e)}")
            error_data = json.dumps({
                "done": True,
                "error": f"部署失败: {str(e)}"
            })
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/step6-status")
async def step6_check_status(request: Step6StatusRequest):
    """Step 6: 检查 Runtime 状态

    状态可选值:
    - CREATING: 创建中
    - CREATE_FAILED: 创建失败
    - UPDATING: 更新中
    - UPDATE_FAILED: 更新失败
    - READY: 就绪，可以调用
    - DELETING: 删除中
    """
    init_clients()

    logger.info(f"Session {request.session_id}: 检查 Runtime 状态 - {request.runtime_id}")

    try:
        response = agentcore_control_client.get_agent_runtime(
            agentRuntimeId=request.runtime_id,
            agentRuntimeVersion=request.runtime_version
        )

        runtime_status = response['status']
        logger.info(f"Runtime {request.runtime_id} 状态: {runtime_status}")

        return {
            "status": "success",
            "runtime_status": runtime_status,
            "details": {
                "agentRuntimeArn": response.get('agentRuntimeArn', ''),
                "agentRuntimeId": response.get('agentRuntimeId', ''),
                "status": runtime_status,
                "createdAt": str(response.get('createdAt', '')),
                "updatedAt": str(response.get('updatedAt', ''))
            }
        }

    except Exception as e:
        logger.error(f"查询状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@router.post("/step7-invoke")
async def step7_invoke_agent(request: Step7InvokeRequest):
    """Step 7: 调用 Runtime"""
    init_clients()

    logger.info(f"Session {request.session_id}: 调用 Runtime ({request.deployment_type}) - {request.runtime_arn}")
    logger.info(f"完整请求参数: deployment_type={request.deployment_type}, runtime_session_id={request.runtime_session_id}, prompt_length={len(request.prompt)}")

    start_time = time.time()

    try:
        # 根据 deployment_type 构建不同的 payload
        if request.deployment_type == "container":
            # Container Deployment: FastAPI 端点需要 {"input": {"prompt": "..."}}
            payload = json.dumps({
                "input": {"prompt": request.prompt}
            })
            logger.info(f"使用 Container payload 格式: {payload}")
        else:
            # Direct Code Deployment: BedrockAgentCoreApp 需要 {"prompt": "..."}
            payload = json.dumps({
                "prompt": request.prompt
            })
            logger.info(f"使用 Direct Code payload 格式: {payload}")

        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=request.runtime_arn,
            runtimeSessionId=request.runtime_session_id,
            payload=payload,
            qualifier="DEFAULT"
        )

        response_body = response['response'].read()
        response_data = json.loads(response_body)

        execution_time = time.time() - start_time

        logger.info(f"Runtime 调用成功，耗时: {execution_time:.2f}s")

        return {
            "status": "success",
            "response": response_data,
            "execution_time": f"{execution_time:.2f}s",
            "prompt": request.prompt,
            "deployment_type": request.deployment_type
        }

    except Exception as e:
        logger.error(f"调用失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"调用失败: {str(e)}")

@router.post("/step8-cleanup")
async def step8_cleanup_runtime(request: Step8CleanupRequest):
    """Step 8: 删除 Runtime"""
    init_clients()

    session_id = request.session_id
    runtime_id = request.runtime_id

    logger.info(f"Session {session_id}: 删除 Runtime {runtime_id}")

    try:
        # 删除 Runtime
        response = agentcore_control_client.delete_agent_runtime(
            agentRuntimeId=runtime_id
        )

        logger.info(f"Runtime 删除请求已发送: {runtime_id}")

        # 删除 S3 文件（可选）
        if session_id in runtime_sessions:
            session_data = runtime_sessions[session_id]
            s3_key = session_data.get('s3_key')
            if s3_key:
                try:
                    s3_client.delete_object(
                        Bucket=S3_BUCKET,
                        Key=s3_key
                    )
                    logger.info(f"S3 文件已删除: {s3_key}")
                except Exception as e:
                    logger.warning(f"删除 S3 文件失败: {str(e)}")

            # 清除会话
            del runtime_sessions[session_id]

        # 清除工作空间的 runtime_id 关联
        for ws_user_id, ws_info in user_workspaces.items():
            if ws_info.runtime_id == runtime_id:
                ws_info.runtime_id = None
                logger.info(f"Workspace {ws_user_id} runtime association cleared")
                break

        return {
            "status": "success",
            "message": "Runtime 已删除",
            "runtime_id": runtime_id
        }

    except Exception as e:
        logger.error(f"删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

# ==================== 辅助端点 ====================

@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """获取会话信息"""
    if session_id in runtime_sessions:
        return {
            "status": "success",
            "data": runtime_sessions[session_id]
        }
    else:
        return {
            "status": "success",
            "data": None,
            "message": "No runtime found for this session"
        }

@router.get("/config")
async def get_environment_config():
    """获取环境配置（用于前端动态替换代码变量）"""
    return {
        "status": "success",
        "config": {
            "ACCOUNT_ID": ACCOUNT_ID or "YOUR_ACCOUNT_ID",
            "REGION": REGION,
            "S3_BUCKET": S3_BUCKET or "YOUR_S3_BUCKET",
            "EXECUTION_ROLE_ARN": ROLE_ARN or "YOUR_EXECUTION_ROLE_ARN"
        }
    }

# ==================== Container Deployment 端点 ====================

# Container 工作空间管理 API

@router.post("/container/workspace/init")
async def init_container_workspace(request: Request, user: dict = Depends(require_login)):
    """初始化 Container 工作空间"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    logger.info(f"[Container Workspace Init] user_session_id={user_session_id}")

    # 检查是否已有工作目录
    if user_session_id in container_workspaces:
        existing = container_workspaces[user_session_id]
        return JSONResponse({
            "success": False,
            "message": "已存在 Container 工作目录，请先清理",
            "existing_workspace_id": existing.workspace_id
        })

    # 生成唯一 ID
    workspace_id = f"container_ws_{int(time.time())}_{secrets.token_hex(4)}"
    workspace_path = os.path.join(CONTAINER_WORKSPACE_BASE_PATH, workspace_id)

    # 创建目录
    try:
        os.makedirs(workspace_path, exist_ok=True)
    except OSError as e:
        logger.error(f"[Container Workspace Init] Failed to create directory: {e}")
        return JSONResponse({
            "success": False,
            "message": f"创建目录失败: {str(e)}"
        }, status_code=500)

    # 保存信息
    container_workspaces[user_session_id] = ContainerWorkspaceInfo(
        workspace_id=workspace_id,
        user_session_id=user_session_id,
        workspace_path=workspace_path
    )

    logger.info(f"[Container Workspace Init] Created workspace {workspace_id} at {workspace_path}")

    return JSONResponse({
        "success": True,
        "workspace_id": workspace_id,
        "workspace_path": workspace_path,
        "message": "Container 工作目录初始化成功"
    })


@router.get("/container/workspace/status")
async def get_container_workspace_status(request: Request, user: dict = Depends(require_login)):
    """获取 Container 工作空间状态"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = container_workspaces.get(user_session_id)

    if workspace:
        return JSONResponse({
            "initialized": True,
            "workspace_id": workspace.workspace_id,
            "workspace_path": workspace.workspace_path,
            "created_at": workspace.created_at,
            "runtime_id": workspace.runtime_id,
            "runtime_arn": workspace.runtime_arn,
            "ecr_image_uri": workspace.ecr_image_uri,
            "has_runtime": workspace.runtime_id is not None
        })
    else:
        return JSONResponse({
            "initialized": False,
            "workspace_id": None,
            "workspace_path": None
        })


@router.post("/container/workspace/cleanup")
async def cleanup_container_workspace(request: Request, user: dict = Depends(require_login)):
    """清理 Container 工作空间"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = container_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "没有 Container 工作目录"})

    # 检查是否有部署的 runtime
    if workspace.runtime_id:
        return JSONResponse({
            "success": False,
            "message": "请先清理 Container Runtime 环境",
            "runtime_id": workspace.runtime_id
        })

    # 删除目录
    try:
        if os.path.exists(workspace.workspace_path):
            shutil.rmtree(workspace.workspace_path)
            logger.info(f"[Container Workspace Cleanup] Deleted directory {workspace.workspace_path}")
    except OSError as e:
        logger.error(f"[Container Workspace Cleanup] Failed to delete directory: {e}")
        return JSONResponse({
            "success": False,
            "message": f"删除目录失败: {str(e)}"
        }, status_code=500)

    del container_workspaces[user_session_id]

    return JSONResponse({"success": True, "message": "Container 工作目录已清理"})


@router.post("/container/workspace/clear-runtime")
async def clear_container_workspace_runtime(request: Request, user: dict = Depends(require_login)):
    """清除 Container 工作空间的 Runtime 关联"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = container_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "没有 Container 工作目录"})

    old_runtime_id = workspace.runtime_id
    old_runtime_arn = workspace.runtime_arn
    workspace.runtime_id = None
    workspace.runtime_arn = None
    logger.info(f"[Container Workspace] Cleared runtime association: {old_runtime_id}, {old_runtime_arn}")

    return JSONResponse({
        "success": True,
        "message": "Container Runtime 关联已清除",
        "cleared_runtime_id": old_runtime_id
    })


# Container 执行 API

@router.get("/container/workspace/execute")
async def execute_container_command_stream(request: Request, command: str, user: dict = Depends(require_login)):
    """执行 Container 工作空间命令 - SSE 流式输出"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = container_workspaces.get(user_session_id)

    if not workspace:
        async def error_generator():
            yield f"data: {json.dumps({'type': 'error', 'message': '请先初始化 Container 工作环境'})}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")

    logger.info(f"[Container Execute] user={user_session_id}, command={command[:100]}...")

    async def generate():
        start_time = time.time()
        last_heartbeat = time.time()

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=workspace.workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )

            stdout_queue = asyncio.Queue()
            stderr_queue = asyncio.Queue()

            async def read_to_queue(stream, queue, stream_type):
                while True:
                    line = await stream.readline()
                    if not line:
                        await queue.put(None)
                        break
                    text = line.decode('utf-8', errors='replace').rstrip('\n\r')
                    await queue.put({"type": stream_type, "line": text, "timestamp": time.time()})

            stdout_task = asyncio.create_task(read_to_queue(process.stdout, stdout_queue, "stdout"))
            stderr_task = asyncio.create_task(read_to_queue(process.stderr, stderr_queue, "stderr"))

            stdout_done = False
            stderr_done = False

            while not (stdout_done and stderr_done):
                current_time = time.time()
                if current_time - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                    heartbeat_data = json.dumps({"type": "heartbeat", "timestamp": current_time})
                    yield f"data: {heartbeat_data}\n\n"
                    last_heartbeat = current_time

                try:
                    try:
                        item = stdout_queue.get_nowait()
                        if item is None:
                            stdout_done = True
                        else:
                            yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.QueueEmpty:
                        pass

                    try:
                        item = stderr_queue.get_nowait()
                        if item is None:
                            stderr_done = True
                        else:
                            yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.QueueEmpty:
                        pass

                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"Error reading output: {e}")
                    break

            await process.wait()
            await stdout_task
            await stderr_task

            duration = time.time() - start_time
            files = get_file_tree(workspace.workspace_path)

            done_data = {
                "type": "done",
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "duration": duration,
                "files": files
            }
            yield f"data: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.error(f"[Container Execute] Error: {e}")
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


class ContainerWriteFileRequest(BaseModel):
    """Container 写入文件请求"""
    file_path: str
    content: str


@router.post("/container/workspace/write-file")
async def write_container_file(request: Request, body: ContainerWriteFileRequest, user: dict = Depends(require_login)):
    """写入文件到 Container 工作空间"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = container_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "请先初始化 Container 工作环境"}, status_code=400)

    full_path = os.path.join(workspace.workspace_path, body.file_path)

    # 安全检查
    abs_full_path = os.path.abspath(full_path)
    abs_workspace_path = os.path.abspath(workspace.workspace_path)
    if not abs_full_path.startswith(abs_workspace_path):
        logger.warning(f"[Container Write File] Path traversal attempt: {body.file_path}")
        return JSONResponse({"success": False, "message": "非法文件路径"}, status_code=400)

    try:
        dir_path = os.path.dirname(full_path)
        if dir_path:  # 只有当目录路径非空时才创建
            os.makedirs(dir_path, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(body.content)

        file_size = len(body.content.encode('utf-8'))
        logger.info(f"[Container Write File] Written {file_size} bytes to {full_path}")

        files = get_file_tree(workspace.workspace_path)

        return JSONResponse({
            "success": True,
            "file_path": full_path,
            "size": file_size,
            "message": "文件写入成功",
            "files": files
        })

    except OSError as e:
        logger.error(f"[Container Write File] Error: {e}")
        return JSONResponse({"success": False, "message": f"写入失败: {str(e)}"}, status_code=500)


class ContainerExecutePythonRequest(BaseModel):
    """Container 执行 Python 代码请求"""
    code: str
    session_id: str


@router.post("/container/workspace/execute-python")
async def execute_container_python_stream(request: Request, body: ContainerExecutePythonRequest, user: dict = Depends(require_login)):
    """执行 Container Python 代码 - SSE 流式输出"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = container_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "请先初始化 Container 工作环境"}, status_code=400)

    logger.info(f"[Container Execute Python] User {user_session_id}, code length: {len(body.code)}")

    async def generate():
        try:
            script_path = os.path.join(workspace.workspace_path, "_container_deploy.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(body.code)

            logger.info(f"[Container Execute Python] Script saved to {script_path}")

            start_data = {"type": "start", "message": "开始执行 Python 脚本..."}
            yield f"data: {json.dumps(start_data)}\n\n"

            start_time = time.time()
            last_heartbeat = start_time

            process = await asyncio.create_subprocess_exec(
                "python", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace.workspace_path,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )

            full_stdout = []
            full_stderr = []
            stdout_queue = asyncio.Queue()
            stderr_queue = asyncio.Queue()

            async def read_stream(stream, queue, stream_type, output_list):
                try:
                    while True:
                        line = await stream.readline()
                        if not line:
                            await queue.put(None)
                            break
                        decoded = line.decode('utf-8', errors='replace').rstrip()
                        output_list.append(decoded)
                        await queue.put({"type": stream_type, "line": decoded})
                except Exception as e:
                    logger.error(f"Error reading {stream_type}: {e}")
                    await queue.put(None)

            stdout_task = asyncio.create_task(read_stream(process.stdout, stdout_queue, "stdout", full_stdout))
            stderr_task = asyncio.create_task(read_stream(process.stderr, stderr_queue, "stderr", full_stderr))

            stdout_done = False
            stderr_done = False

            while not (stdout_done and stderr_done):
                current_time = time.time()
                if current_time - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                    heartbeat_data = json.dumps({"type": "heartbeat", "timestamp": current_time})
                    yield f"data: {heartbeat_data}\n\n"
                    last_heartbeat = current_time

                try:
                    try:
                        item = stdout_queue.get_nowait()
                        if item is None:
                            stdout_done = True
                        else:
                            yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.QueueEmpty:
                        pass

                    try:
                        item = stderr_queue.get_nowait()
                        if item is None:
                            stderr_done = True
                        else:
                            yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.QueueEmpty:
                        pass

                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"Error in output loop: {e}")
                    break

            await process.wait()
            await stdout_task
            await stderr_task

            duration = time.time() - start_time

            # 解析结果
            result_data = None
            for line in full_stdout:
                if line.startswith("__RESULT__:"):
                    try:
                        result_data = json.loads(line[11:])
                        # 更新工作空间的 runtime 信息
                        if result_data.get("runtime_id"):
                            workspace.runtime_id = result_data["runtime_id"]
                        if result_data.get("runtime_arn"):
                            workspace.runtime_arn = result_data["runtime_arn"]
                        if result_data.get("ecr_image_uri"):
                            workspace.ecr_image_uri = result_data["ecr_image_uri"]
                    except json.JSONDecodeError:
                        pass

            files = get_file_tree(workspace.workspace_path)

            done_data = {
                "type": "done",
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "duration": duration,
                "stdout": "\n".join(full_stdout),
                "stderr": "\n".join(full_stderr),
                "result": result_data,
                "files": files
            }
            yield f"data: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.error(f"[Container Execute Python] Error: {e}")
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


@router.get("/container/config")
async def get_container_config():
    """获取 Container 配置信息（用于前端动态替换代码变量）"""
    try:
        ecr_image_uri = build_container_image_uri()
    except ValueError:
        ecr_image_uri = "YOUR_ECR_IMAGE_URI"

    return {
        "status": "success",
        "config": {
            "ACCOUNT_ID": ACCOUNT_ID or "YOUR_ACCOUNT_ID",
            "REGION": REGION,
            "CONTAINER_ECR_REPOSITORY_NAME": CONTAINER_ECR_REPOSITORY or "YOUR_REPOSITORY",
            "CONTAINER_IMAGE_TAG": CONTAINER_IMAGE_TAG,
            "CONTAINER_EXECUTION_ROLE_ARN": CONTAINER_ROLE_ARN or "YOUR_CONTAINER_ROLE_ARN",
            "ECR_IMAGE_URI": ecr_image_uri
        }
    }

# ==================== 工作空间管理 API ====================

class WriteFileRequest(BaseModel):
    """写入文件请求"""
    file_path: str
    content: str

def get_file_tree(base_path: str, max_depth: int = FILE_TREE_MAX_DEPTH, max_files: int = FILE_TREE_MAX_FILES) -> List[dict]:
    """递归获取文件树结构"""
    file_count = [0]  # 使用列表以便在递归中修改
    # 忽略的目录
    ignore_dirs = {'.git', '.venv', '__pycache__', 'node_modules', '.pytest_cache'}

    def scan_dir(path: str, depth: int) -> List[dict]:
        if depth > max_depth or file_count[0] >= max_files:
            return []

        items = []
        try:
            entries = sorted(os.listdir(path))
            for entry in entries:
                if file_count[0] >= max_files:
                    break

                # 跳过忽略的目录
                if entry in ignore_dirs:
                    continue

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
                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        size = 0
                    items.append({
                        "name": entry,
                        "type": "file",
                        "size": size
                    })
        except PermissionError:
            pass
        except OSError as e:
            logger.warning(f"Error scanning directory {path}: {e}")

        return items

    return scan_dir(base_path, 0)

@router.post("/workspace/init")
async def init_workspace(request: Request, user: dict = Depends(require_login)):
    """初始化工作空间"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    logger.info(f"[Workspace Init] user_session_id={user_session_id}")

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
    try:
        os.makedirs(workspace_path, exist_ok=True)
    except OSError as e:
        logger.error(f"[Workspace Init] Failed to create directory: {e}")
        return JSONResponse({
            "success": False,
            "message": f"创建目录失败: {str(e)}"
        }, status_code=500)

    # 保存信息
    user_workspaces[user_session_id] = WorkspaceInfo(
        workspace_id=workspace_id,
        user_session_id=user_session_id,
        workspace_path=workspace_path
    )

    logger.info(f"[Workspace Init] Created workspace {workspace_id} at {workspace_path}")

    return JSONResponse({
        "success": True,
        "workspace_id": workspace_id,
        "workspace_path": workspace_path,
        "message": "工作目录初始化成功"
    })

@router.get("/workspace/status")
async def get_workspace_status(request: Request, user: dict = Depends(require_login)):
    """获取工作空间状态"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = user_workspaces.get(user_session_id)

    if workspace:
        return JSONResponse({
            "initialized": True,
            "workspace_id": workspace.workspace_id,
            "workspace_path": workspace.workspace_path,
            "created_at": workspace.created_at,
            "runtime_id": workspace.runtime_id,
            "has_runtime": workspace.runtime_id is not None
        })
    else:
        return JSONResponse({
            "initialized": False,
            "workspace_id": None,
            "workspace_path": None
        })

@router.post("/workspace/clear-runtime")
async def clear_workspace_runtime(request: Request, user: dict = Depends(require_login)):
    """清除工作空间的 Runtime 关联（在 Part 8 删除 Runtime 后调用）"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = user_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "没有工作目录"})

    old_runtime_id = workspace.runtime_id
    workspace.runtime_id = None
    logger.info(f"[Workspace] Cleared runtime association: {old_runtime_id}")

    return JSONResponse({
        "success": True,
        "message": "Runtime 关联已清除",
        "cleared_runtime_id": old_runtime_id
    })


@router.post("/workspace/cleanup")
async def cleanup_workspace(request: Request, user: dict = Depends(require_login)):
    """清理工作空间"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

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
    try:
        if os.path.exists(workspace.workspace_path):
            shutil.rmtree(workspace.workspace_path)
            logger.info(f"[Workspace Cleanup] Deleted directory {workspace.workspace_path}")
    except OSError as e:
        logger.error(f"[Workspace Cleanup] Failed to delete directory: {e}")
        return JSONResponse({
            "success": False,
            "message": f"删除目录失败: {str(e)}"
        }, status_code=500)

    del user_workspaces[user_session_id]

    return JSONResponse({"success": True, "message": "工作目录已清理"})

@router.get("/workspace/execute")
async def execute_command_stream(request: Request, command: str, user: dict = Depends(require_login)):
    """执行命令 - SSE 流式输出"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = user_workspaces.get(user_session_id)

    if not workspace:
        async def error_generator():
            yield f"data: {json.dumps({'type': 'error', 'message': '请先初始化工作环境'})}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")

    logger.info(f"[Execute Command] user={user_session_id}, command={command[:100]}...")

    async def generate():
        start_time = time.time()
        last_heartbeat = time.time()

        try:
            # 创建子进程
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=workspace.workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )

            async def read_stream(stream, stream_type):
                """读取流并生成输出"""
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text = line.decode('utf-8', errors='replace').rstrip('\n\r')
                    yield {
                        "type": stream_type,
                        "line": text,
                        "timestamp": time.time()
                    }

            # 创建读取任务
            stdout_queue = asyncio.Queue()
            stderr_queue = asyncio.Queue()

            async def read_to_queue(stream, queue, stream_type):
                async for item in read_stream(stream, stream_type):
                    await queue.put(item)
                await queue.put(None)  # 结束标记

            # 启动读取任务
            stdout_task = asyncio.create_task(read_to_queue(process.stdout, stdout_queue, "stdout"))
            stderr_task = asyncio.create_task(read_to_queue(process.stderr, stderr_queue, "stderr"))

            stdout_done = False
            stderr_done = False

            while not (stdout_done and stderr_done):
                # 检查心跳
                current_time = time.time()
                if current_time - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                    heartbeat_data = json.dumps({"type": "heartbeat", "timestamp": current_time})
                    yield f"data: {heartbeat_data}\n\n"
                    last_heartbeat = current_time

                # 非阻塞检查队列
                try:
                    # 尝试从 stdout 队列获取
                    try:
                        item = stdout_queue.get_nowait()
                        if item is None:
                            stdout_done = True
                        else:
                            yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.QueueEmpty:
                        pass

                    # 尝试从 stderr 队列获取
                    try:
                        item = stderr_queue.get_nowait()
                        if item is None:
                            stderr_done = True
                        else:
                            yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.QueueEmpty:
                        pass

                    # 短暂等待
                    await asyncio.sleep(0.05)

                except Exception as e:
                    logger.error(f"Error reading output: {e}")
                    break

            # 等待进程结束
            await process.wait()
            await stdout_task
            await stderr_task

            duration = time.time() - start_time

            # 获取文件树
            files = get_file_tree(workspace.workspace_path)

            # 发送完成消息
            done_data = {
                "type": "done",
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "duration": duration,
                "files": files
            }
            yield f"data: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.error(f"[Execute Command] Error: {e}")
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/workspace/write-file")
async def write_file(request: Request, body: WriteFileRequest, user: dict = Depends(require_login)):
    """写入文件到工作空间"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = user_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "请先初始化工作环境"}, status_code=400)

    # 构建完整路径
    full_path = os.path.join(workspace.workspace_path, body.file_path)

    # 安全检查：确保路径在工作空间内
    abs_full_path = os.path.abspath(full_path)
    abs_workspace_path = os.path.abspath(workspace.workspace_path)
    if not abs_full_path.startswith(abs_workspace_path):
        logger.warning(f"[Write File] Path traversal attempt: {body.file_path}")
        return JSONResponse({"success": False, "message": "非法文件路径"}, status_code=400)

    try:
        # 创建父目录
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # 写入文件
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(body.content)

        file_size = len(body.content.encode('utf-8'))
        logger.info(f"[Write File] Written {file_size} bytes to {full_path}")

        # 获取文件树
        files = get_file_tree(workspace.workspace_path)

        return JSONResponse({
            "success": True,
            "file_path": full_path,
            "size": file_size,
            "message": "文件写入成功",
            "files": files
        })

    except OSError as e:
        logger.error(f"[Write File] Error: {e}")
        return JSONResponse({"success": False, "message": f"写入失败: {str(e)}"}, status_code=500)


class ExecutePythonRequest(BaseModel):
    """执行 Python 代码请求"""
    code: str
    session_id: str


@router.post("/workspace/execute-python")
async def execute_python_stream(request: Request, body: ExecutePythonRequest, user: dict = Depends(require_login)):
    """执行 Python 代码 - SSE 流式输出

    用于执行部署 Runtime 的 Python 脚本，支持：
    - boto3 API 调用
    - 流式输出执行日志
    - 解析 runtime_arn 和 runtime_id
    """
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = user_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "请先初始化工作环境"}, status_code=400)

    logger.info(f"[Execute Python] User {user_session_id}, code length: {len(body.code)}")

    async def generate():
        try:
            # 创建临时 Python 文件
            script_path = os.path.join(workspace.workspace_path, "_deploy_runtime.py")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(body.code)

            logger.info(f"[Execute Python] Script saved to {script_path}")

            # 发送开始消息
            start_data = {"type": "start", "message": "开始执行 Python 脚本..."}
            yield f"data: {json.dumps(start_data)}\n\n"

            start_time = time.time()
            last_heartbeat = start_time

            # 使用 asyncio subprocess 执行
            process = await asyncio.create_subprocess_exec(
                "python", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace.workspace_path,
                env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )

            # 收集完整输出用于解析
            full_stdout = []
            full_stderr = []

            # 异步读取 stdout 和 stderr
            stdout_queue = asyncio.Queue()
            stderr_queue = asyncio.Queue()

            async def read_stream(stream, queue, stream_type):
                try:
                    while True:
                        line = await stream.readline()
                        if not line:
                            await queue.put(None)
                            break
                        decoded = line.decode('utf-8', errors='replace').rstrip()
                        if stream_type == "stdout":
                            full_stdout.append(decoded)
                        else:
                            full_stderr.append(decoded)
                        await queue.put({"type": stream_type, "line": decoded})
                except Exception as e:
                    logger.error(f"Error reading {stream_type}: {e}")
                    await queue.put(None)

            stdout_task = asyncio.create_task(read_stream(process.stdout, stdout_queue, "stdout"))
            stderr_task = asyncio.create_task(read_stream(process.stderr, stderr_queue, "stderr"))

            stdout_done = False
            stderr_done = False

            while not (stdout_done and stderr_done):
                current_time = time.time()

                # 心跳
                if current_time - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                    yield f": heartbeat\n\n"
                    last_heartbeat = current_time

                try:
                    # 读取 stdout
                    try:
                        item = stdout_queue.get_nowait()
                        if item is None:
                            stdout_done = True
                        else:
                            yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.QueueEmpty:
                        pass

                    # 读取 stderr
                    try:
                        item = stderr_queue.get_nowait()
                        if item is None:
                            stderr_done = True
                        else:
                            yield f"data: {json.dumps(item)}\n\n"
                    except asyncio.QueueEmpty:
                        pass

                    await asyncio.sleep(0.05)

                except Exception as e:
                    logger.error(f"Error reading output: {e}")
                    break

            # 等待进程结束
            await process.wait()
            await stdout_task
            await stderr_task

            duration = time.time() - start_time

            # 尝试从输出中解析 runtime_arn 和 runtime_id
            runtime_arn = None
            runtime_id = None
            agent_name = None

            all_output = "\n".join(full_stdout + full_stderr)

            # 解析 RUNTIME_ARN=xxx 格式
            import re
            arn_match = re.search(r'RUNTIME_ARN=(\S+)', all_output)
            if arn_match:
                runtime_arn = arn_match.group(1)

            id_match = re.search(r'RUNTIME_ID=(\S+)', all_output)
            if id_match:
                runtime_id = id_match.group(1)

            name_match = re.search(r'AGENT_NAME=(\S+)', all_output)
            if name_match:
                agent_name = name_match.group(1)

            # 如果成功获取到 runtime 信息，保存到会话
            if runtime_arn and runtime_id and process.returncode == 0:
                runtime_sessions[body.session_id] = {
                    "deployment_type": "code",
                    "runtime_arn": runtime_arn,
                    "runtime_id": runtime_id,
                    "agent_name": agent_name,
                    "created_at": time.time()
                }

                # 关联到工作空间
                workspace.runtime_id = runtime_id
                logger.info(f"[Execute Python] Runtime created: {runtime_id}")

            # 清理临时脚本
            try:
                os.remove(script_path)
            except:
                pass

            # 获取文件树
            files = get_file_tree(workspace.workspace_path)

            # 发送完成消息
            done_data = {
                "type": "done",
                "success": process.returncode == 0,
                "return_code": process.returncode,
                "duration": duration,
                "files": files,
                "runtime_arn": runtime_arn,
                "runtime_id": runtime_id,
                "agent_name": agent_name
            }
            yield f"data: {json.dumps(done_data)}\n\n"

        except Exception as e:
            logger.error(f"[Execute Python] Error: {e}")
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/workspace/files")
async def get_files(request: Request, user: dict = Depends(require_login)):
    """获取工作空间文件树"""
    user_session_id = request.cookies.get("session_id")
    if not user_session_id:
        user_session_id = user.get("session_id", "default_session")

    workspace = user_workspaces.get(user_session_id)

    if not workspace:
        return JSONResponse({"success": False, "message": "请先初始化工作环境"}, status_code=400)

    files = get_file_tree(workspace.workspace_path)

    # 计算总文件数和大小
    def count_files(items):
        total_count = 0
        total_size = 0
        for item in items:
            if item["type"] == "file":
                total_count += 1
                total_size += item.get("size", 0)
            elif item["type"] == "directory":
                c, s = count_files(item.get("children", []))
                total_count += c
                total_size += s
        return total_count, total_size

    total_files, total_size = count_files(files)

    return JSONResponse({
        "success": True,
        "workspace_path": workspace.workspace_path,
        "files": files,
        "total_files": total_files,
        "total_size": total_size
    })
