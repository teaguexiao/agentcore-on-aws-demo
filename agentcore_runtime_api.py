"""
AgentCore Runtime Demo API Module

提供 Runtime 演示的所有 API 端点:
- Mock API: Step 2, 3, 5-package
- 真实 API: Step 5-deploy, 6, 7, 8
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator
import boto3
import os
import json
from typing import Optional, Dict, Any, AsyncGenerator
import logging
import time
import asyncio

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

def init_clients():
    """初始化 boto3 客户端"""
    global s3_client, agentcore_control_client, agentcore_client

    if s3_client is None:
        s3_client = boto3.client('s3', region_name=REGION)
        agentcore_control_client = boto3.client('bedrock-agentcore-control', region_name=REGION)
        agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)
        logger.info("Boto3 clients initialized")

def init_runtime_vars(cm):
    """初始化 Runtime API 变量 (从 app.py 调用)"""
    global connection_manager
    connection_manager = cm
    init_clients()
    logger.info("Runtime API variables initialized")

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

@router.get("/container/step1-stream")
async def container_step1_init_project_stream(session_id: str):
    """Container Step 1: 模拟初始化项目 - SSE 流式输出"""
    logger.info(f"Session {session_id}: 执行 Container Step 1 - 初始化项目 (SSE)")

    async def generate():
        output_lines = [
            "Creating project directory: my-custom-agent",
            "Initializing Python 3.11 project...",
            "Created pyproject.toml",
            "Created uv.lock",
            "Created .venv directory",
            "",
            "Adding dependencies:",
            "  - fastapi",
            "  - uvicorn[standard]",
            "  - pydantic",
            "  - httpx",
            "  - strands-agents",
            "",
            "Installing packages...",
            "✓ All dependencies installed successfully!",
            "✓ Project setup completed!"
        ]

        for line in output_lines:
            await asyncio.sleep(0.5)
            data = json.dumps({"line": line, "done": False})
            yield f"data: {data}\n\n"

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

@router.get("/container/step2-stream")
async def container_step2_create_agent_stream(session_id: str):
    """Container Step 2: 模拟创建 Agent 应用 - SSE 流式输出"""
    logger.info(f"Session {session_id}: 执行 Container Step 2 - 创建 Agent 应用 (SSE)")

    async def generate():
        output_lines = [
            "Creating FastAPI application...",
            "Writing agent.py with endpoints:",
            "  - POST /invocations (Agent invocation)",
            "  - GET /ping (Health check)",
            "",
            "Configuring Strands Agent...",
            "Setting up request/response models:",
            "  - InvocationRequest",
            "  - InvocationResponse",
            "",
            "Adding error handling...",
            "Configuring uvicorn server...",
            "",
            "✓ File created: my-custom-agent/agent.py",
            "✓ Agent application ready for containerization"
        ]

        for line in output_lines:
            await asyncio.sleep(0.5)
            data = json.dumps({"line": line, "done": False})
            yield f"data: {data}\n\n"

        final_data = json.dumps({
            "done": True,
            "message": "agent.py 创建完成",
            "file_path": "my-custom-agent/agent.py",
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

@router.get("/container/step3-stream")
async def container_step3_create_dockerfile_stream(session_id: str):
    """Container Step 3: 模拟创建 Dockerfile - SSE 流式输出"""
    logger.info(f"Session {session_id}: 执行 Container Step 3 - 创建 Dockerfile (SSE)")

    async def generate():
        output_lines = [
            "Creating Dockerfile for ARM64 architecture...",
            "Base image: ghcr.io/astral-sh/uv:python3.11-bookworm-slim",
            "Platform: linux/arm64",
            "",
            "Configuring workdir: /app",
            "Adding dependency files: pyproject.toml, uv.lock",
            "Installing dependencies with uv sync...",
            "Copying agent.py...",
            "",
            "Exposing port 8080...",
            "Setting CMD: uvicorn agent:app --host 0.0.0.0 --port 8080",
            "",
            "✓ Dockerfile created: my-custom-agent/Dockerfile",
            "✓ Container configuration ready"
        ]

        for line in output_lines:
            await asyncio.sleep(0.5)
            data = json.dumps({"line": line, "done": False})
            yield f"data: {data}\n\n"

        final_data = json.dumps({
            "done": True,
            "message": "Dockerfile 创建完成",
            "file_path": "my-custom-agent/Dockerfile",
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

@router.get("/container/step4-stream")
async def container_step4_buildx_setup_stream(session_id: str):
    """Container Step 4: 模拟设置 Docker Buildx - SSE 流式输出"""
    logger.info(f"Session {session_id}: 执行 Container Step 4 - Buildx 设置 (SSE)")

    async def generate():
        output_lines = [
            "Setting up Docker Buildx...",
            "Creating new builder instance: agentcore-builder",
            "",
            "$ docker buildx create --use",
            "agentcore-builder",
            "",
            "$ docker buildx inspect --bootstrap",
            "Name:   agentcore-builder",
            "Driver: docker-container",
            "",
            "Platforms:",
            "  - linux/amd64",
            "  - linux/arm64",
            "  - linux/arm/v7",
            "  - linux/arm/v6",
            "",
            "✓ Buildx configured successfully",
            "✓ Ready to build multi-platform images"
        ]

        for line in output_lines:
            await asyncio.sleep(0.4)
            data = json.dumps({"line": line, "done": False})
            yield f"data: {data}\n\n"

        final_data = json.dumps({
            "done": True,
            "message": "Docker Buildx 设置完成",
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

@router.get("/container/step5-stream")
async def container_step5_build_push_stream(session_id: str):
    """Container Step 5: 模拟构建并推送到 ECR - SSE 流式输出"""
    logger.info(f"Session {session_id}: 执行 Container Step 5 - 构建推送镜像 (SSE)")

    async def generate():
        try:
            ecr_image_uri = build_container_image_uri()
        except ValueError as e:
            error_data = json.dumps({
                "done": True,
                "error": str(e)
            })
            yield f"data: {error_data}\n\n"
            return

        output_lines = [
            "Logging in to Amazon ECR...",
            f"$ aws ecr get-login-password --region {REGION} | docker login ...",
            "Login Succeeded",
            "",
            f"Building Docker image for platform linux/arm64...",
            f"Target: {ecr_image_uri}",
            "",
            "$ docker buildx build --platform linux/arm64 --push .",
            "[+] Building 45.2s (12/12) FINISHED",
            " => [internal] load build definition from Dockerfile",
            " => [internal] load .dockerignore",
            " => [1/6] FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim",
            " => [2/6] WORKDIR /app",
            " => [3/6] COPY pyproject.toml uv.lock ./",
            " => [4/6] RUN uv sync --frozen --no-cache",
            " => [5/6] COPY agent.py ./",
            " => [6/6] EXPOSE 8080",
            " => exporting to image",
            " => pushing layers",
            f" => pushing manifest for {ecr_image_uri}",
            "",
            "✓ Image built and pushed successfully!",
            f"✓ Image URI: {ecr_image_uri}"
        ]

        for line in output_lines:
            await asyncio.sleep(0.3)
            data = json.dumps({"line": line, "done": False})
            yield f"data: {data}\n\n"

        final_data = json.dumps({
            "done": True,
            "message": "Docker 镜像构建推送完成",
            "ecr_image_uri": ecr_image_uri,
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

@router.get("/container/step6-stream")
async def container_step6_deploy_stream(session_id: str, agent_name: Optional[str] = None):
    """Container Step 6: 真实部署 Runtime - SSE 流式输出"""
    init_clients()
    agent_name = agent_name or f"container_demo_{int(time.time())}"
    logger.info(f"Session {session_id}: 开始部署 Container Runtime {agent_name} (SSE)")

    async def generate():
        try:
            ecr_image_uri = build_container_image_uri()
            start_msg = json.dumps({"line": f"正在创建 AgentCore Runtime: {agent_name}", "done": False})
            yield f"data: {start_msg}\n\n"

            image_msg = json.dumps({"line": f"使用容器镜像: {ecr_image_uri}", "done": False})
            yield f"data: {image_msg}\n\n"

            logger.info(f"创建 Container Runtime: {agent_name}")
            response = agentcore_control_client.create_agent_runtime(
                agentRuntimeName=agent_name,
                agentRuntimeArtifact={'containerConfiguration': {'containerUri': ecr_image_uri}},
                networkConfiguration={"networkMode": "PUBLIC"},
                roleArn=CONTAINER_ROLE_ARN
            )

            runtime_arn = response['agentRuntimeArn']
            runtime_id = response['agentRuntimeId']

            runtime_sessions[session_id] = {
                "deployment_type": "container",
                "runtime_arn": runtime_arn,
                "runtime_id": runtime_id,
                "agent_name": agent_name,
                "ecr_image_uri": ecr_image_uri,
                "ecr_repository_name": CONTAINER_ECR_REPOSITORY,
                "image_tag": CONTAINER_IMAGE_TAG,
                "created_at": time.time()
            }

            logger.info(f"Container Runtime 创建成功: {runtime_arn}")
            complete_msg = json.dumps({
                "line": f"\n✓ Runtime 创建成功!\n\nRuntime ARN: {runtime_arn}\nRuntime ID: {runtime_id}\nStatus: CREATING",
                "done": False
            })
            yield f"data: {complete_msg}\n\n"

            final_data = json.dumps({
                "done": True,
                "status": "success",
                "runtime_arn": runtime_arn,
                "runtime_id": runtime_id,
                "runtime_version": "1",
                "agent_name": agent_name,
                "ecr_image_uri": ecr_image_uri,
                "message": "Container Runtime 部署成功！"
            })
            yield f"data: {final_data}\n\n"

        except Exception as e:
            logger.error(f"Container 部署失败: {str(e)}")
            error_data = json.dumps({"done": True, "error": f"部署失败: {str(e)}"})
            yield f"data: {error_data}\n\n"

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
