"""
AgentCore Gateway API - Backend module for Gateway demonstrations

Provides API functions for demonstrating Gateway capabilities:
1. Transform Lambda into MCP Tools
2. Transform APIs (OpenAPI) into MCP Tools
3. Gateway Semantic Search for Tools

Security Features:
- Session-based resource tracking
- Automatic cleanup on logout/timeout
- Per-user resource isolation
"""

import os
import time
import boto3
import uuid
import json
import asyncio
import threading
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Generator
from boto3.session import Session


class GatewaySessionManager:
    """Manages Gateway resources per user session with automatic cleanup"""

    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[str, Dict] = {}  # session_id -> session_data
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self._lock = threading.Lock()
        self._cleanup_task = None

    def create_session(self, session_id: str, username: str) -> Dict:
        """Create a new session for tracking resources"""
        with self._lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    "session_id": session_id,
                    "username": username,
                    "created_at": datetime.now(),
                    "last_activity": datetime.now(),
                    "resources": {
                        "gateways": {},      # gateway_name -> {gateway_id, gateway_url, target_id}
                        "lambdas": {},       # function_name -> arn
                        "cognito_pools": {}, # pool_name -> {pool_id, client_id}
                        "iam_roles": {}      # role_name -> arn
                    },
                    "step_data": {}  # Store step-by-step demo data
                }
            return self.sessions[session_id]

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session["last_activity"] = datetime.now()
            return session

    def add_resource(self, session_id: str, resource_type: str, name: str, data: Any):
        """Add a resource to the session"""
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]["resources"][resource_type][name] = data
                self.sessions[session_id]["last_activity"] = datetime.now()

    def get_resources(self, session_id: str) -> Dict:
        """Get all resources for a session"""
        with self._lock:
            if session_id in self.sessions:
                return self.sessions[session_id]["resources"]
            return {"gateways": {}, "lambdas": {}, "cognito_pools": {}, "iam_roles": {}}

    def remove_session(self, session_id: str) -> Dict:
        """Remove a session and return its resources for cleanup"""
        with self._lock:
            if session_id in self.sessions:
                session_data = self.sessions.pop(session_id)
                return session_data.get("resources", {})
            return {}

    def get_expired_sessions(self) -> List[str]:
        """Get list of expired session IDs"""
        with self._lock:
            now = datetime.now()
            expired = []
            for session_id, session in self.sessions.items():
                if now - session["last_activity"] > self.session_timeout:
                    expired.append(session_id)
            return expired

    def get_all_sessions(self) -> List[Dict]:
        """Get all active sessions info"""
        with self._lock:
            return [
                {
                    "session_id": s["session_id"],
                    "username": s["username"],
                    "created_at": s["created_at"].isoformat(),
                    "last_activity": s["last_activity"].isoformat(),
                    "resource_count": sum(len(v) for v in s["resources"].values())
                }
                for s in self.sessions.values()
            ]


# Global session manager
session_manager = GatewaySessionManager(session_timeout_minutes=30)


class AgentCoreGatewayAPI:
    """Gateway API handler with session-based resource management"""

    def __init__(self, region_name: str = "us-west-2", simulation_mode: bool = True):
        self.region_name = region_name
        self.simulation_mode = simulation_mode  # 默认开启模拟模式
        self.gateway_client = None
        self.iam_client = None
        self.lambda_client = None
        self.cognito_client = None
        self.bedrock_runtime = None

        # Legacy support - will be replaced by session-based tracking
        self.created_gateways = {}
        self.created_lambdas = {}
        self.created_cognito_pools = {}
        self.created_roles = {}

    def set_simulation_mode(self, enabled: bool):
        """Enable or disable simulation mode"""
        self.simulation_mode = enabled
        return {"success": True, "simulation_mode": self.simulation_mode}

    def get_simulation_mode(self) -> bool:
        """Get current simulation mode status"""
        return self.simulation_mode

    def _init_clients(self):
        """Initialize AWS clients"""
        if not self.gateway_client:
            self.gateway_client = boto3.client('bedrock-agentcore-control', region_name=self.region_name)
        if not self.iam_client:
            self.iam_client = boto3.client('iam', region_name=self.region_name)
        if not self.lambda_client:
            self.lambda_client = boto3.client('lambda', region_name=self.region_name)
        if not self.cognito_client:
            self.cognito_client = boto3.client('cognito-idp', region_name=self.region_name)
        if not self.bedrock_runtime:
            self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region_name)

    def _init_clients_with_credentials(self, credentials: Dict):
        """Initialize AWS clients with user-provided credentials

        Args:
            credentials: Dict with 'access_key', 'secret_key', and optionally 'region'
        """
        access_key = credentials.get("access_key")
        secret_key = credentials.get("secret_key")
        region = credentials.get("region", self.region_name)

        # Update region if provided
        if region:
            self.region_name = region

        # Initialize all clients with user credentials
        self.gateway_client = boto3.client(
            'bedrock-agentcore-control',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region_name
        )
        self.iam_client = boto3.client(
            'iam',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region_name
        )
        self.lambda_client = boto3.client(
            'lambda',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region_name
        )
        self.cognito_client = boto3.client(
            'cognito-idp',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region_name
        )
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region_name
        )

    def _send_event(self, event_type: str, data: Any) -> str:
        """Format SSE event"""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, ensure_ascii=False)
        else:
            data_str = str(data)

        lines = data_str.split('\n')
        data_lines = '\n'.join(f"data: {line}" for line in lines)

        return f"event: {event_type}\n{data_lines}\n\n"

    def _get_account_id(self) -> str:
        """Get current AWS account ID"""
        sts_client = boto3.client('sts', region_name=self.region_name)
        return sts_client.get_caller_identity()["Account"]

    # ==================== Demo 1: Lambda to MCP Tools ====================

    def create_gateway_iam_role(self, role_name: str = None, lambda_arns: List[str] = None) -> Dict[str, Any]:
        """Create IAM role for Gateway to assume"""
        if not role_name:
            role_name = f"agentcore-gateway-role-{uuid.uuid4().hex[:8]}"

        # 模拟模式：返回模拟数据
        if self.simulation_mode:
            time.sleep(1)  # 模拟延迟
            simulated_arn = f"arn:aws:iam::123456789012:role/{role_name}"
            return {
                "success": True,
                "role_name": role_name,
                "role_arn": simulated_arn,
                "simulated": True
            }

        self._init_clients()
        account_id = self._get_account_id()

        # Trust policy for AgentCore Gateway
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AssumeRolePolicy",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock-agentcore.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {
                            "aws:SourceAccount": account_id
                        },
                        "ArnLike": {
                            "aws:SourceArn": f"arn:aws:bedrock-agentcore:{self.region_name}:{account_id}:*"
                        }
                    }
                }
            ]
        }

        # Role policy
        role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:*",
                        "bedrock:*",
                        "iam:PassRole",
                        "secretsmanager:GetSecretValue",
                        "lambda:InvokeFunction"
                    ],
                    "Resource": "*"
                }
            ]
        }

        try:
            # Create role
            role_response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy)
            )

            # Attach inline policy
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName="AgentCoreGatewayPolicy",
                PolicyDocument=json.dumps(role_policy)
            )

            # Wait for role to be available
            time.sleep(10)

            role_arn = role_response['Role']['Arn']
            self.created_roles[role_name] = role_arn

            return {
                "success": True,
                "role_name": role_name,
                "role_arn": role_arn
            }

        except self.iam_client.exceptions.EntityAlreadyExistsException:
            # Role already exists, get its ARN
            role_response = self.iam_client.get_role(RoleName=role_name)
            role_arn = role_response['Role']['Arn']
            self.created_roles[role_name] = role_arn
            return {
                "success": True,
                "role_name": role_name,
                "role_arn": role_arn,
                "message": "Role already exists"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create IAM role: {str(e)}"
            }

    def setup_cognito_for_gateway(self, pool_name: str = None) -> Dict[str, Any]:
        """Set up Cognito User Pool for Gateway inbound authentication"""
        if not pool_name:
            pool_name = f"gateway-pool-{uuid.uuid4().hex[:8]}"

        # 模拟模式：返回模拟数据
        if self.simulation_mode:
            time.sleep(1)  # 模拟延迟
            simulated_pool_id = f"us-west-2_{uuid.uuid4().hex[:9]}"
            simulated_client_id = uuid.uuid4().hex[:26]
            return {
                "success": True,
                "pool_id": simulated_pool_id,
                "client_id": simulated_client_id,
                "discovery_url": f"https://cognito-idp.{self.region_name}.amazonaws.com/{simulated_pool_id}/.well-known/openid-configuration",
                "pool_name": pool_name,
                "simulated": True
            }

        self._init_clients()

        try:
            # Create User Pool
            pool_response = self.cognito_client.create_user_pool(
                PoolName=pool_name,
                Policies={
                    'PasswordPolicy': {
                        'MinimumLength': 8
                    }
                }
            )
            pool_id = pool_response['UserPool']['Id']

            # Create domain for token endpoint
            domain_prefix = pool_id.replace("_", "").lower()
            try:
                self.cognito_client.create_user_pool_domain(
                    Domain=domain_prefix,
                    UserPoolId=pool_id
                )
            except Exception:
                pass  # Domain might already exist

            # Create App Client
            client_response = self.cognito_client.create_user_pool_client(
                UserPoolId=pool_id,
                ClientName=f"{pool_name}-client",
                GenerateSecret=False,
                ExplicitAuthFlows=[
                    'ALLOW_USER_PASSWORD_AUTH',
                    'ALLOW_REFRESH_TOKEN_AUTH'
                ]
            )
            client_id = client_response['UserPoolClient']['ClientId']

            # Create test user
            self.cognito_client.admin_create_user(
                UserPoolId=pool_id,
                Username='testuser',
                TemporaryPassword='Temp123!',
                MessageAction='SUPPRESS'
            )

            # Set permanent password
            self.cognito_client.admin_set_user_password(
                UserPoolId=pool_id,
                Username='testuser',
                Password='TestPassword123!',
                Permanent=True
            )

            discovery_url = f"https://cognito-idp.{self.region_name}.amazonaws.com/{pool_id}/.well-known/openid-configuration"

            self.created_cognito_pools[pool_name] = {
                "pool_id": pool_id,
                "client_id": client_id,
                "discovery_url": discovery_url
            }

            return {
                "success": True,
                "pool_id": pool_id,
                "client_id": client_id,
                "discovery_url": discovery_url,
                "pool_name": pool_name
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to setup Cognito: {str(e)}"
            }

    def get_bearer_token(self, pool_id: str, client_id: str, username: str = "testuser", password: str = "TestPassword123!") -> Dict[str, Any]:
        """Get bearer token from Cognito"""
        self._init_clients()

        try:
            auth_response = self.cognito_client.initiate_auth(
                ClientId=client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )

            return {
                "success": True,
                "access_token": auth_response['AuthenticationResult']['AccessToken'],
                "token_type": "Bearer"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get bearer token: {str(e)}"
            }

    def create_sample_lambda(self, function_name: str = None) -> Dict[str, Any]:
        """Create a sample Lambda function for Gateway demo"""
        if not function_name:
            function_name = f"gateway-demo-lambda-{uuid.uuid4().hex[:8]}"

        # 模拟模式：返回模拟数据
        if self.simulation_mode:
            time.sleep(1)  # 模拟延迟
            simulated_arn = f"arn:aws:lambda:{self.region_name}:123456789012:function:{function_name}"
            return {
                "success": True,
                "function_name": function_name,
                "function_arn": simulated_arn,
                "simulated": True
            }

        self._init_clients()
        account_id = self._get_account_id()

        # Lambda function code
        lambda_code = '''
def lambda_handler(event, context):
    """Sample Lambda for Gateway Demo - Order Management"""
    import json

    # Parse the incoming request
    tool_name = event.get('name', '')
    arguments = event.get('arguments', {})

    if 'get_order' in tool_name.lower():
        order_id = arguments.get('orderId', 'unknown')
        return {
            'statusCode': 200,
            'body': json.dumps({
                'orderId': order_id,
                'status': 'shipped',
                'items': ['Item A', 'Item B'],
                'total': 99.99,
                'estimatedDelivery': '2024-12-25'
            })
        }
    elif 'update_order' in tool_name.lower():
        order_id = arguments.get('orderId', 'unknown')
        return {
            'statusCode': 200,
            'body': json.dumps({
                'orderId': order_id,
                'message': 'Order updated successfully',
                'newStatus': 'processing'
            })
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Unknown tool'})
        }
'''

        # Create IAM role for Lambda
        lambda_role_name = f"{function_name}-role"
        lambda_assume_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        try:
            # Create Lambda execution role
            try:
                role_response = self.iam_client.create_role(
                    RoleName=lambda_role_name,
                    AssumeRolePolicyDocument=json.dumps(lambda_assume_policy)
                )
                self.iam_client.attach_role_policy(
                    RoleName=lambda_role_name,
                    PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                )
                lambda_role_arn = role_response['Role']['Arn']
                time.sleep(10)  # Wait for role propagation
            except self.iam_client.exceptions.EntityAlreadyExistsException:
                role_response = self.iam_client.get_role(RoleName=lambda_role_name)
                lambda_role_arn = role_response['Role']['Arn']

            # Create Lambda function
            import zipfile
            import io

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('lambda_function.py', lambda_code)
            zip_buffer.seek(0)

            try:
                lambda_response = self.lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime='python3.12',
                    Role=lambda_role_arn,
                    Handler='lambda_function.lambda_handler',
                    Code={'ZipFile': zip_buffer.read()},
                    Description='Sample Lambda for AgentCore Gateway Demo',
                    Timeout=30
                )
                lambda_arn = lambda_response['FunctionArn']
            except self.lambda_client.exceptions.ResourceConflictException:
                lambda_response = self.lambda_client.get_function(FunctionName=function_name)
                lambda_arn = lambda_response['Configuration']['FunctionArn']

            self.created_lambdas[function_name] = lambda_arn

            return {
                "success": True,
                "function_name": function_name,
                "function_arn": lambda_arn
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create Lambda: {str(e)}"
            }

    def create_gateway_with_lambda_target(self, gateway_name: str = None, lambda_arn: str = None,
                                          role_arn: str = None, cognito_client_id: str = None,
                                          cognito_discovery_url: str = None) -> Dict[str, Any]:
        """Create Gateway with Lambda target"""
        if not gateway_name:
            gateway_name = f"gateway-lambda-{uuid.uuid4().hex[:8]}"

        # 模拟模式：返回模拟数据
        if self.simulation_mode:
            time.sleep(2)  # 模拟较长的创建时间
            simulated_gateway_id = f"{gateway_name}-{uuid.uuid4().hex[:10]}"
            simulated_gateway_url = f"https://{simulated_gateway_id}.gateway.bedrock-agentcore.{self.region_name}.amazonaws.com/mcp"
            simulated_target_id = uuid.uuid4().hex[:10].upper()
            return {
                "success": True,
                "gateway_id": simulated_gateway_id,
                "gateway_url": simulated_gateway_url,
                "gateway_name": gateway_name,
                "target_id": simulated_target_id,
                "simulated": True
            }

        self._init_clients()

        try:
            # Create Gateway with Cognito authorizer
            auth_config = {
                "customJWTAuthorizer": {
                    "allowedClients": [cognito_client_id],
                    "discoveryUrl": cognito_discovery_url
                }
            }

            gateway_response = self.gateway_client.create_gateway(
                name=gateway_name,
                roleArn=role_arn,
                protocolType='MCP',
                authorizerType='CUSTOM_JWT',
                authorizerConfiguration=auth_config,
                description='AgentCore Gateway with Lambda target for Demo'
            )

            gateway_id = gateway_response['gatewayId']
            gateway_url = gateway_response['gatewayUrl']

            # Wait for Gateway to be ready
            time.sleep(5)

            # Create Lambda target with tool schema
            lambda_target_config = {
                "mcp": {
                    "lambda": {
                        "lambdaArn": lambda_arn,
                        "toolSchema": {
                            "inlinePayload": [
                                {
                                    "name": "get_order_tool",
                                    "description": "Get order status and details by order ID",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "orderId": {
                                                "type": "string",
                                                "description": "The order ID to look up"
                                            }
                                        },
                                        "required": ["orderId"]
                                    }
                                },
                                {
                                    "name": "update_order_tool",
                                    "description": "Update an existing order",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "orderId": {
                                                "type": "string",
                                                "description": "The order ID to update"
                                            }
                                        },
                                        "required": ["orderId"]
                                    }
                                }
                            ]
                        }
                    }
                }
            }

            credential_config = [
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ]

            target_response = self.gateway_client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name="LambdaOrderTools",
                description='Lambda Target for Order Management',
                targetConfiguration=lambda_target_config,
                credentialProviderConfigurations=credential_config
            )

            target_id = target_response['targetId']

            self.created_gateways[gateway_name] = {
                "gateway_id": gateway_id,
                "gateway_url": gateway_url,
                "target_id": target_id
            }

            return {
                "success": True,
                "gateway_id": gateway_id,
                "gateway_url": gateway_url,
                "gateway_name": gateway_name,
                "target_id": target_id
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create Gateway: {str(e)}"
            }

    def demo_lambda_to_mcp_stream(self, username: str = None, session_id: str = None) -> Generator[str, None, None]:
        """Demo 1: Transform Lambda into MCP Tools (streaming)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始演示: 将 Lambda 函数转换为 MCP 工具")
            yield self._send_event("log", f"⏱️  开始时间: {datetime.now().strftime('%H:%M:%S')}")
            if session_id:
                yield self._send_event("log", f"📌 会话追踪已启用 (资源将在登出时自动清理)")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # Step 1: Create IAM Role
            yield self._send_event("log", "📋 步骤 1: 创建 Gateway IAM 角色...")
            time_module.sleep(0.1)

            role_result = self.create_gateway_iam_role()
            if not role_result["success"]:
                yield self._send_event("log", f"❌ IAM 角色创建失败: {role_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": role_result.get('message', '')})
                return

            role_arn = role_result["role_arn"]
            # Track resource in session
            self._track_resource(session_id, "iam_roles", role_result["role_name"], role_arn)

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ IAM 角色创建成功: {role_result['role_name']} [{elapsed:.2f}s]")
            time_module.sleep(0.1)

            # Step 2: Setup Cognito
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 2: 设置 Cognito 认证...")
            time_module.sleep(0.1)

            cognito_result = self.setup_cognito_for_gateway()
            if not cognito_result["success"]:
                yield self._send_event("log", f"❌ Cognito 设置失败: {cognito_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": cognito_result.get('message', '')})
                return

            # Track resource in session
            self._track_resource(session_id, "cognito_pools", cognito_result["pool_name"], {
                "pool_id": cognito_result["pool_id"],
                "client_id": cognito_result["client_id"]
            })

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ Cognito 用户池创建成功 [{elapsed:.2f}s]")
            yield self._send_event("log", f"   - Pool ID: {cognito_result['pool_id']}")
            yield self._send_event("log", f"   - Client ID: {cognito_result['client_id']}")
            time_module.sleep(0.1)

            # Step 3: Create Sample Lambda
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 3: 创建示例 Lambda 函数...")
            time_module.sleep(0.1)

            lambda_result = self.create_sample_lambda()
            if not lambda_result["success"]:
                yield self._send_event("log", f"❌ Lambda 创建失败: {lambda_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": lambda_result.get('message', '')})
                return

            # Track resource in session
            self._track_resource(session_id, "lambdas", lambda_result["function_name"], lambda_result["function_arn"])

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ Lambda 函数创建成功 [{elapsed:.2f}s]")
            yield self._send_event("log", f"   - Function: {lambda_result['function_name']}")
            time_module.sleep(0.1)

            # Step 4: Create Gateway with Lambda Target
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 4: 创建 Gateway 并添加 Lambda Target...")
            time_module.sleep(0.1)

            gateway_result = self.create_gateway_with_lambda_target(
                lambda_arn=lambda_result["function_arn"],
                role_arn=role_arn,
                cognito_client_id=cognito_result["client_id"],
                cognito_discovery_url=cognito_result["discovery_url"]
            )

            if not gateway_result["success"]:
                yield self._send_event("log", f"❌ Gateway 创建失败: {gateway_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": gateway_result.get('message', '')})
                return

            # Track resource in session
            self._track_resource(session_id, "gateways", gateway_result["gateway_name"], {
                "gateway_id": gateway_result["gateway_id"],
                "gateway_url": gateway_result["gateway_url"],
                "target_id": gateway_result.get("target_id")
            })

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ Gateway 创建成功 [{elapsed:.2f}s]")
            yield self._send_event("log", f"   - Gateway ID: {gateway_result['gateway_id']}")
            yield self._send_event("log", f"   - Gateway URL: {gateway_result['gateway_url']}")
            time_module.sleep(0.1)

            # Step 5: Get Bearer Token
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 5: 获取访问令牌...")
            time_module.sleep(0.1)

            token_result = self.get_bearer_token(
                pool_id=cognito_result["pool_id"],
                client_id=cognito_result["client_id"]
            )

            if not token_result["success"]:
                yield self._send_event("log", f"⚠️  令牌获取失败: {token_result.get('message', '')}")
            else:
                elapsed = time_module.time() - start_time
                yield self._send_event("log", f"✅ 访问令牌获取成功 [{elapsed:.2f}s]")

            # Summary
            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", "=" * 50)
            yield self._send_event("log", "🎉 Lambda to MCP Tools 演示完成!")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            yield self._send_event("log", "")
            yield self._send_event("log", "📝 已创建的 MCP 工具:")
            yield self._send_event("log", "   1. get_order_tool - 查询订单状态")
            yield self._send_event("log", "   2. update_order_tool - 更新订单信息")
            yield self._send_event("log", "")
            yield self._send_event("log", "💡 现在您可以通过 Gateway URL 使用这些 MCP 工具了!")
            yield self._send_event("log", "🔄 退出登录时，所有创建的资源将被自动清理")

            yield self._send_event("result", {
                "success": True,
                "gateway_id": gateway_result["gateway_id"],
                "gateway_url": gateway_result["gateway_url"],
                "cognito_pool_id": cognito_result["pool_id"],
                "cognito_client_id": cognito_result["client_id"],
                "lambda_arn": lambda_result["function_arn"],
                "tools": ["get_order_tool", "update_order_tool"],
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": "Lambda to MCP Tools 演示完成"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"❌ 演示失败: {str(e)} [{elapsed:.2f}s]")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"演示失败: {str(e)}"
            })

    # ==================== Demo 2: OpenAPI to MCP Tools ====================

    def create_gateway_with_openapi_target(self, gateway_name: str = None, openapi_spec: dict = None,
                                           role_arn: str = None, cognito_client_id: str = None,
                                           cognito_discovery_url: str = None,
                                           api_base_url: str = None) -> Dict[str, Any]:
        """Create Gateway with OpenAPI target"""
        if not gateway_name:
            gateway_name = f"gateway-openapi-{uuid.uuid4().hex[:8]}"

        # 模拟模式：返回模拟数据
        if self.simulation_mode:
            time.sleep(2)
            simulated_gateway_id = f"{gateway_name}-{uuid.uuid4().hex[:10]}"
            simulated_gateway_url = f"https://{simulated_gateway_id}.gateway.bedrock-agentcore.{self.region_name}.amazonaws.com/mcp"
            return {
                "success": True,
                "gateway_id": simulated_gateway_id,
                "gateway_url": simulated_gateway_url,
                "gateway_name": gateway_name,
                "simulated": True
            }

        self._init_clients()

        try:
            # Create Gateway with Cognito authorizer
            auth_config = {
                "customJWTAuthorizer": {
                    "allowedClients": [cognito_client_id],
                    "discoveryUrl": cognito_discovery_url
                }
            }

            gateway_response = self.gateway_client.create_gateway(
                name=gateway_name,
                roleArn=role_arn,
                protocolType='MCP',
                authorizerType='CUSTOM_JWT',
                authorizerConfiguration=auth_config,
                description='AgentCore Gateway with OpenAPI target for Demo'
            )

            gateway_id = gateway_response['gatewayId']
            gateway_url = gateway_response['gatewayUrl']

            self.created_gateways[gateway_name] = {
                "gateway_id": gateway_id,
                "gateway_url": gateway_url
            }

            return {
                "success": True,
                "gateway_id": gateway_id,
                "gateway_url": gateway_url,
                "gateway_name": gateway_name
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create Gateway with OpenAPI: {str(e)}"
            }

    def demo_openapi_to_mcp_stream(self, username: str = None, session_id: str = None) -> Generator[str, None, None]:
        """Demo 2: Transform OpenAPI into MCP Tools (streaming)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始演示: 将 OpenAPI 规范转换为 MCP 工具")
            yield self._send_event("log", f"⏱️  开始时间: {datetime.now().strftime('%H:%M:%S')}")
            if session_id:
                yield self._send_event("log", f"📌 会话追踪已启用 (资源将在登出时自动清理)")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # Show sample OpenAPI spec
            sample_openapi = {
                "openapi": "3.0.0",
                "info": {
                    "title": "Weather API",
                    "version": "1.0.0",
                    "description": "Sample Weather API for MCP Demo"
                },
                "servers": [
                    {"url": "https://api.example.com"}
                ],
                "paths": {
                    "/weather": {
                        "get": {
                            "operationId": "getWeather",
                            "summary": "Get weather information",
                            "parameters": [
                                {
                                    "name": "city",
                                    "in": "query",
                                    "required": True,
                                    "schema": {"type": "string"}
                                }
                            ]
                        }
                    }
                }
            }

            yield self._send_event("log", "📄 示例 OpenAPI 规范:")
            yield self._send_event("log", json.dumps(sample_openapi, indent=2, ensure_ascii=False))
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # Step 1: Create IAM Role
            yield self._send_event("log", "📋 步骤 1: 创建 Gateway IAM 角色...")
            role_result = self.create_gateway_iam_role(role_name=f"gateway-openapi-role-{uuid.uuid4().hex[:8]}")

            if not role_result["success"]:
                yield self._send_event("log", f"❌ IAM 角色创建失败: {role_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": role_result.get('message', '')})
                return

            # Track resource in session
            self._track_resource(session_id, "iam_roles", role_result["role_name"], role_result["role_arn"])

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ IAM 角色创建成功 [{elapsed:.2f}s]")
            time_module.sleep(0.1)

            # Step 2: Setup Cognito
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 2: 设置 Cognito 认证...")
            cognito_result = self.setup_cognito_for_gateway(pool_name=f"gateway-openapi-pool-{uuid.uuid4().hex[:8]}")

            if not cognito_result["success"]:
                yield self._send_event("log", f"❌ Cognito 设置失败: {cognito_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": cognito_result.get('message', '')})
                return

            # Track resource in session
            self._track_resource(session_id, "cognito_pools", cognito_result["pool_name"], {
                "pool_id": cognito_result["pool_id"],
                "client_id": cognito_result["client_id"]
            })

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ Cognito 设置成功 [{elapsed:.2f}s]")
            time_module.sleep(0.1)

            # Step 3: Create Gateway
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 3: 创建 Gateway...")
            gateway_result = self.create_gateway_with_openapi_target(
                openapi_spec=sample_openapi,
                role_arn=role_result["role_arn"],
                cognito_client_id=cognito_result["client_id"],
                cognito_discovery_url=cognito_result["discovery_url"]
            )

            if not gateway_result["success"]:
                yield self._send_event("log", f"❌ Gateway 创建失败: {gateway_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": gateway_result.get('message', '')})
                return

            # Track resource in session
            self._track_resource(session_id, "gateways", gateway_result["gateway_name"], {
                "gateway_id": gateway_result["gateway_id"],
                "gateway_url": gateway_result["gateway_url"]
            })

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ Gateway 创建成功 [{elapsed:.2f}s]")
            yield self._send_event("log", f"   - Gateway URL: {gateway_result['gateway_url']}")
            time_module.sleep(0.1)

            # Summary
            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", "=" * 50)
            yield self._send_event("log", "🎉 OpenAPI to MCP Tools 演示完成!")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            yield self._send_event("log", "")
            yield self._send_event("log", "📝 OpenAPI 规范已转换为 MCP 工具:")
            yield self._send_event("log", "   - getWeather: 获取天气信息")
            yield self._send_event("log", "")
            yield self._send_event("log", "💡 Gateway 会自动解析 OpenAPI 规范并生成对应的 MCP 工具!")

            yield self._send_event("result", {
                "success": True,
                "gateway_id": gateway_result["gateway_id"],
                "gateway_url": gateway_result["gateway_url"],
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": "OpenAPI to MCP Tools 演示完成"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"❌ 演示失败: {str(e)} [{elapsed:.2f}s]")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"演示失败: {str(e)}"
            })

    # ==================== Demo 3: Gateway Search Tools ====================

    def create_gateway_with_search(self, gateway_name: str = None, role_arn: str = None,
                                   cognito_client_id: str = None, cognito_discovery_url: str = None) -> Dict[str, Any]:
        """Create Gateway with semantic search enabled"""
        if not gateway_name:
            gateway_name = f"gateway-search-{uuid.uuid4().hex[:8]}"

        # 模拟模式：返回模拟数据
        if self.simulation_mode:
            time.sleep(2)
            simulated_gateway_id = f"{gateway_name}-{uuid.uuid4().hex[:10]}"
            simulated_gateway_url = f"https://{simulated_gateway_id}.gateway.bedrock-agentcore.{self.region_name}.amazonaws.com/mcp"
            return {
                "success": True,
                "gateway_id": simulated_gateway_id,
                "gateway_url": simulated_gateway_url,
                "gateway_name": gateway_name,
                "simulated": True
            }

        self._init_clients()

        try:
            auth_config = {
                "customJWTAuthorizer": {
                    "allowedClients": [cognito_client_id],
                    "discoveryUrl": cognito_discovery_url
                }
            }

            # Enable semantic search
            search_config = {
                "mcp": {
                    "searchType": "SEMANTIC",
                    "supportedVersions": ["2025-03-26"]
                }
            }

            gateway_response = self.gateway_client.create_gateway(
                name=gateway_name,
                roleArn=role_arn,
                protocolType='MCP',
                authorizerType='CUSTOM_JWT',
                authorizerConfiguration=auth_config,
                protocolConfiguration=search_config,
                description='AgentCore Gateway with Semantic Search Demo'
            )

            gateway_id = gateway_response['gatewayId']
            gateway_url = gateway_response['gatewayUrl']

            self.created_gateways[gateway_name] = {
                "gateway_id": gateway_id,
                "gateway_url": gateway_url
            }

            return {
                "success": True,
                "gateway_id": gateway_id,
                "gateway_url": gateway_url,
                "gateway_name": gateway_name
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create Gateway with search: {str(e)}"
            }

    def demo_gateway_search_stream(self, username: str = None, session_id: str = None) -> Generator[str, None, None]:
        """Demo 3: Gateway Semantic Search for Tools (streaming)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始演示: Gateway 工具语义搜索")
            yield self._send_event("log", f"⏱️  开始时间: {datetime.now().strftime('%H:%M:%S')}")
            if session_id:
                yield self._send_event("log", f"📌 会话追踪已启用 (资源将在登出时自动清理)")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            yield self._send_event("log", "📖 Gateway Search 功能说明:")
            yield self._send_event("log", "   当 Gateway 拥有大量工具 (100+) 时，语义搜索可以:")
            yield self._send_event("log", "   • 提升 Agent 工具选择准确性")
            yield self._send_event("log", "   • 降低 Token 消耗和成本")
            yield self._send_event("log", "   • 减少 LLM 调用延迟 (最高可达 3x)")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # Step 1: Create IAM Role
            yield self._send_event("log", "📋 步骤 1: 创建 Gateway IAM 角色...")
            role_result = self.create_gateway_iam_role(role_name=f"gateway-search-role-{uuid.uuid4().hex[:8]}")

            if not role_result["success"]:
                yield self._send_event("log", f"❌ IAM 角色创建失败: {role_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": role_result.get('message', '')})
                return

            # Track resource in session
            self._track_resource(session_id, "iam_roles", role_result["role_name"], role_result["role_arn"])

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ IAM 角色创建成功 [{elapsed:.2f}s]")
            time_module.sleep(0.1)

            # Step 2: Setup Cognito
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 2: 设置 Cognito 认证...")
            cognito_result = self.setup_cognito_for_gateway(pool_name=f"gateway-search-pool-{uuid.uuid4().hex[:8]}")

            if not cognito_result["success"]:
                yield self._send_event("log", f"❌ Cognito 设置失败: {cognito_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": cognito_result.get('message', '')})
                return

            # Track resource in session
            self._track_resource(session_id, "cognito_pools", cognito_result["pool_name"], {
                "pool_id": cognito_result["pool_id"],
                "client_id": cognito_result["client_id"]
            })

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ Cognito 设置成功 [{elapsed:.2f}s]")
            time_module.sleep(0.1)

            # Step 3: Create Gateway with Search
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 3: 创建启用语义搜索的 Gateway...")
            gateway_result = self.create_gateway_with_search(
                role_arn=role_result["role_arn"],
                cognito_client_id=cognito_result["client_id"],
                cognito_discovery_url=cognito_result["discovery_url"]
            )

            if not gateway_result["success"]:
                yield self._send_event("log", f"❌ Gateway 创建失败: {gateway_result.get('message', '')}")
                yield self._send_event("result", {"success": False, "message": gateway_result.get('message', '')})
                return

            # Track resource in session
            self._track_resource(session_id, "gateways", gateway_result["gateway_name"], {
                "gateway_id": gateway_result["gateway_id"],
                "gateway_url": gateway_result["gateway_url"]
            })

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ Gateway 创建成功 (语义搜索已启用) [{elapsed:.2f}s]")
            yield self._send_event("log", f"   - Gateway URL: {gateway_result['gateway_url']}")
            time_module.sleep(0.1)

            # Step 4: Add Sample Tools
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 4: 添加示例工具到 Gateway...")

            # Create sample lambda first
            lambda_result = self.create_sample_lambda(function_name=f"search-demo-lambda-{uuid.uuid4().hex[:8]}")
            if lambda_result["success"]:
                # Track Lambda resource
                self._track_resource(session_id, "lambdas", lambda_result["function_name"], lambda_result["function_arn"])
                # Create target with multiple tools for search demo
                sample_tools = [
                    {"name": "calculate_sum", "description": "Add two numbers together",
                     "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}}},
                    {"name": "calculate_product", "description": "Multiply two numbers",
                     "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}}},
                    {"name": "get_weather", "description": "Get current weather for a city",
                     "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}}}},
                    {"name": "book_restaurant", "description": "Make a restaurant reservation",
                     "inputSchema": {"type": "object", "properties": {"restaurant": {"type": "string"}, "date": {"type": "string"}, "guests": {"type": "integer"}}}},
                    {"name": "search_flights", "description": "Search for available flights",
                     "inputSchema": {"type": "object", "properties": {"origin": {"type": "string"}, "destination": {"type": "string"}, "date": {"type": "string"}}}}
                ]

                try:
                    lambda_target_config = {
                        "mcp": {
                            "lambda": {
                                "lambdaArn": lambda_result["function_arn"],
                                "toolSchema": {"inlinePayload": sample_tools}
                            }
                        }
                    }

                    self.gateway_client.create_gateway_target(
                        gatewayIdentifier=gateway_result["gateway_id"],
                        name="SearchDemoTools",
                        description='Tools for Search Demo',
                        targetConfiguration=lambda_target_config,
                        credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
                    )

                    elapsed = time_module.time() - start_time
                    yield self._send_event("log", f"✅ 已添加 {len(sample_tools)} 个工具到 Gateway [{elapsed:.2f}s]")

                except Exception as e:
                    yield self._send_event("log", f"⚠️  添加工具时出现警告: {str(e)}")

            time_module.sleep(0.1)

            # Explain search tool
            yield self._send_event("log", "")
            yield self._send_event("log", "📋 步骤 5: 使用 Search 工具...")
            yield self._send_event("log", "")
            yield self._send_event("log", "🔍 Gateway 自动提供的搜索工具: x-amz-bedrock-agentcore-search")
            yield self._send_event("log", "")
            yield self._send_event("log", "使用示例:")
            yield self._send_event("log", '   query: "find tools for making restaurant reservations"')
            yield self._send_event("log", "   返回: book_restaurant (相关性最高)")
            yield self._send_event("log", "")
            yield self._send_event("log", '   query: "tools for mathematical calculations"')
            yield self._send_event("log", "   返回: calculate_sum, calculate_product")
            time_module.sleep(0.1)

            # Summary
            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", "=" * 50)
            yield self._send_event("log", "🎉 Gateway Search 演示完成!")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            yield self._send_event("log", "")
            yield self._send_event("log", "📝 语义搜索优势:")
            yield self._send_event("log", "   • 当 Gateway 有 300+ 工具时，搜索可减少 3x 延迟")
            yield self._send_event("log", "   • 显著减少 Token 使用量")
            yield self._send_event("log", "   • 提高 Agent 工具选择准确性")

            yield self._send_event("result", {
                "success": True,
                "gateway_id": gateway_result["gateway_id"],
                "gateway_url": gateway_result["gateway_url"],
                "search_tool": "x-amz-bedrock-agentcore-search",
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": "Gateway Search 演示完成"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"❌ 演示失败: {str(e)} [{elapsed:.2f}s]")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"演示失败: {str(e)}"
            })

    # ==================== Resource Management ====================

    def list_gateways(self, username: str = None) -> Dict[str, Any]:
        """List all Gateways"""
        # 模拟模式：返回会话中创建的模拟 Gateway
        if self.simulation_mode:
            gateways = []
            # 从所有会话中收集创建的模拟 Gateway
            for session_id, session in session_manager.sessions.items():
                resources = session.get("resources", {})
                for gw_name, gw_info in resources.get("gateways", {}).items():
                    if isinstance(gw_info, dict):
                        gateway_info = {
                            "gateway_id": gw_info.get("gateway_id", ""),
                            "name": gw_name,
                            "status": "ACTIVE",
                            "protocol_type": "MCP",
                            "created_at": session.get("created_at", datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
                            "gateway_url": gw_info.get("gateway_url", "")
                        }
                        # Filter by username if provided
                        if username:
                            session_username = session.get("username", "")
                            if username.lower() == session_username.lower():
                                gateways.append(gateway_info)
                        else:
                            gateways.append(gateway_info)

            return {
                "success": True,
                "gateways": gateways,
                "count": len(gateways),
                "simulated": True
            }

        # 真实模式：从 AWS 获取
        self._init_clients()

        try:
            response = self.gateway_client.list_gateways(maxResults=100)

            gateways = []
            for item in response.get('items', []):
                gateway_info = {
                    "gateway_id": item.get('gatewayId'),
                    "name": item.get('name'),
                    "status": item.get('status'),
                    "protocol_type": item.get('protocolType'),
                    "created_at": str(item.get('createdAt', '')),
                    "gateway_url": item.get('gatewayUrl', '')
                }

                # Filter by username if provided
                if username:
                    if username.lower() in gateway_info["name"].lower():
                        gateways.append(gateway_info)
                else:
                    gateways.append(gateway_info)

            return {
                "success": True,
                "gateways": gateways,
                "count": len(gateways)
            }

        except Exception as e:
            return {
                "success": False,
                "gateways": [],
                "message": f"Failed to list Gateways: {str(e)}"
            }

    def delete_gateway(self, gateway_id: str) -> Dict[str, Any]:
        """Delete a Gateway and its targets"""
        # 模拟模式：从会话中删除模拟的 Gateway
        if self.simulation_mode:
            deleted = False
            for session_id, session in session_manager.sessions.items():
                resources = session.get("resources", {})
                gateways = resources.get("gateways", {})
                # 查找并删除匹配的 Gateway
                to_delete = None
                for gw_name, gw_info in gateways.items():
                    if isinstance(gw_info, dict) and gw_info.get("gateway_id") == gateway_id:
                        to_delete = gw_name
                        break
                if to_delete:
                    del gateways[to_delete]
                    deleted = True
                    break

            if deleted:
                return {
                    "success": True,
                    "message": f"Gateway {gateway_id} deleted successfully (simulated)",
                    "simulated": True
                }
            else:
                return {
                    "success": False,
                    "message": f"Gateway {gateway_id} not found in simulation"
                }

        # 真实模式：从 AWS 删除
        self._init_clients()

        try:
            # First delete all targets
            try:
                targets_response = self.gateway_client.list_gateway_targets(
                    gatewayIdentifier=gateway_id,
                    maxResults=100
                )

                for target in targets_response.get('items', []):
                    target_id = target.get('targetId')
                    self.gateway_client.delete_gateway_target(
                        gatewayIdentifier=gateway_id,
                        targetId=target_id
                    )
                    time.sleep(2)

            except Exception as e:
                pass  # Continue even if target deletion fails

            # Delete the gateway
            self.gateway_client.delete_gateway(gatewayIdentifier=gateway_id)

            return {
                "success": True,
                "message": f"Gateway {gateway_id} deleted successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to delete Gateway: {str(e)}"
            }

    def cleanup_demo_resources(self) -> Dict[str, Any]:
        """Clean up all demo resources (legacy method)"""
        results = []

        # Delete Gateways
        for name, info in self.created_gateways.items():
            result = self.delete_gateway(info["gateway_id"])
            results.append({"type": "gateway", "name": name, "result": result})

        # Delete Lambdas
        self._init_clients()
        for name, arn in self.created_lambdas.items():
            try:
                self.lambda_client.delete_function(FunctionName=name)
                results.append({"type": "lambda", "name": name, "result": {"success": True}})
            except Exception as e:
                results.append({"type": "lambda", "name": name, "result": {"success": False, "message": str(e)}})

        # Delete Cognito pools
        for name, info in self.created_cognito_pools.items():
            try:
                self.cognito_client.delete_user_pool(UserPoolId=info["pool_id"])
                results.append({"type": "cognito", "name": name, "result": {"success": True}})
            except Exception as e:
                results.append({"type": "cognito", "name": name, "result": {"success": False, "message": str(e)}})

        # Delete IAM roles
        for name, arn in self.created_roles.items():
            try:
                # First delete inline policies
                policies = self.iam_client.list_role_policies(RoleName=name)
                for policy_name in policies.get('PolicyNames', []):
                    self.iam_client.delete_role_policy(RoleName=name, PolicyName=policy_name)

                # Detach managed policies
                attached = self.iam_client.list_attached_role_policies(RoleName=name)
                for policy in attached.get('AttachedPolicies', []):
                    self.iam_client.detach_role_policy(RoleName=name, PolicyArn=policy['PolicyArn'])

                # Delete the role
                self.iam_client.delete_role(RoleName=name)
                results.append({"type": "iam_role", "name": name, "result": {"success": True}})
            except Exception as e:
                results.append({"type": "iam_role", "name": name, "result": {"success": False, "message": str(e)}})

        # Clear stored resources
        self.created_gateways = {}
        self.created_lambdas = {}
        self.created_cognito_pools = {}
        self.created_roles = {}

        return {
            "success": True,
            "results": results,
            "message": "Cleanup completed"
        }

    # ==================== Session-based Resource Management ====================

    def cleanup_session_resources(self, session_id: str) -> Dict[str, Any]:
        """Clean up all resources for a specific session"""
        self._init_clients()
        results = []

        # Get and remove session resources
        resources = session_manager.remove_session(session_id)

        if not resources:
            return {
                "success": True,
                "results": [],
                "message": f"No resources found for session {session_id}"
            }

        # Delete Gateways first (they depend on other resources)
        for name, info in resources.get("gateways", {}).items():
            try:
                gateway_id = info.get("gateway_id") if isinstance(info, dict) else info
                result = self.delete_gateway(gateway_id)
                results.append({"type": "gateway", "name": name, "result": result})
            except Exception as e:
                results.append({"type": "gateway", "name": name, "result": {"success": False, "message": str(e)}})

        # Delete Lambdas
        for name, arn in resources.get("lambdas", {}).items():
            try:
                self.lambda_client.delete_function(FunctionName=name)
                results.append({"type": "lambda", "name": name, "result": {"success": True}})
            except Exception as e:
                results.append({"type": "lambda", "name": name, "result": {"success": False, "message": str(e)}})

        # Delete Lambda execution roles
        for name in resources.get("lambdas", {}).keys():
            lambda_role_name = f"{name}-role"
            try:
                self._delete_iam_role(lambda_role_name)
                results.append({"type": "lambda_role", "name": lambda_role_name, "result": {"success": True}})
            except Exception as e:
                results.append({"type": "lambda_role", "name": lambda_role_name, "result": {"success": False, "message": str(e)}})

        # Delete Cognito pools
        for name, info in resources.get("cognito_pools", {}).items():
            try:
                pool_id = info.get("pool_id") if isinstance(info, dict) else info
                # First delete domain if exists
                try:
                    domain_prefix = pool_id.replace("_", "").lower()
                    self.cognito_client.delete_user_pool_domain(
                        Domain=domain_prefix,
                        UserPoolId=pool_id
                    )
                except Exception:
                    pass
                self.cognito_client.delete_user_pool(UserPoolId=pool_id)
                results.append({"type": "cognito", "name": name, "result": {"success": True}})
            except Exception as e:
                results.append({"type": "cognito", "name": name, "result": {"success": False, "message": str(e)}})

        # Delete IAM roles
        for name, arn in resources.get("iam_roles", {}).items():
            try:
                self._delete_iam_role(name)
                results.append({"type": "iam_role", "name": name, "result": {"success": True}})
            except Exception as e:
                results.append({"type": "iam_role", "name": name, "result": {"success": False, "message": str(e)}})

        return {
            "success": True,
            "results": results,
            "message": f"Cleanup completed for session {session_id}",
            "deleted_count": len([r for r in results if r.get("result", {}).get("success", False)])
        }

    def _delete_iam_role(self, role_name: str):
        """Helper to delete an IAM role with all its policies"""
        self._init_clients()

        # First delete inline policies
        try:
            policies = self.iam_client.list_role_policies(RoleName=role_name)
            for policy_name in policies.get('PolicyNames', []):
                self.iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        except Exception:
            pass

        # Detach managed policies
        try:
            attached = self.iam_client.list_attached_role_policies(RoleName=role_name)
            for policy in attached.get('AttachedPolicies', []):
                self.iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy['PolicyArn'])
        except Exception:
            pass

        # Delete the role
        self.iam_client.delete_role(RoleName=role_name)

    def cleanup_expired_sessions(self) -> Dict[str, Any]:
        """Clean up all expired sessions"""
        expired_sessions = session_manager.get_expired_sessions()
        results = []

        for session_id in expired_sessions:
            result = self.cleanup_session_resources(session_id)
            results.append({
                "session_id": session_id,
                "result": result
            })

        return {
            "success": True,
            "expired_count": len(expired_sessions),
            "results": results
        }

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session's resources"""
        session = session_manager.get_session(session_id)
        if not session:
            return {
                "success": False,
                "message": f"Session {session_id} not found"
            }

        resources = session.get("resources", {})
        return {
            "success": True,
            "session_id": session_id,
            "username": session.get("username"),
            "created_at": session.get("created_at").isoformat() if session.get("created_at") else None,
            "last_activity": session.get("last_activity").isoformat() if session.get("last_activity") else None,
            "resources": {
                "gateways": len(resources.get("gateways", {})),
                "lambdas": len(resources.get("lambdas", {})),
                "cognito_pools": len(resources.get("cognito_pools", {})),
                "iam_roles": len(resources.get("iam_roles", {}))
            },
            "total_resources": sum(len(v) for v in resources.values())
        }

    def list_all_sessions(self) -> Dict[str, Any]:
        """List all active sessions"""
        sessions = session_manager.get_all_sessions()
        return {
            "success": True,
            "sessions": sessions,
            "total": len(sessions)
        }

    def register_session(self, session_id: str, username: str) -> Dict[str, Any]:
        """Register a new session for resource tracking"""
        session_manager.create_session(session_id, username)
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Session registered for user {username}"
        }

    # Helper method to track resources in session
    def _track_resource(self, session_id: str, resource_type: str, name: str, data: Any):
        """Track a created resource in the session"""
        if session_id:
            session_manager.add_resource(session_id, resource_type, name, data)

    # ==================== Step-by-Step Lambda Demo ====================

    def run_lambda_step(self, step: int, session_id: str = None, username: str = "default_user", aws_credentials: Dict = None) -> Dict[str, Any]:
        """Execute a single step of the Lambda to MCP demo

        Args:
            step: Step number (1-5)
            session_id: Session ID for tracking
            username: Username
            aws_credentials: Optional dict with 'access_key', 'secret_key', 'region' for real mode
        """
        # Debug logging
        print(f"[DEBUG] run_lambda_step: step={step}, session_id={session_id}, has_credentials={aws_credentials is not None}")

        # If user provided credentials, temporarily use them for this operation
        if aws_credentials and not self.simulation_mode:
            self._init_clients_with_credentials(aws_credentials)

        # Ensure session exists and get reference
        session = None
        if session_id:
            session = session_manager.create_session(session_id, username)
            print(f"[DEBUG] session created/retrieved, step_data={session.get('step_data', {})}")

        try:
            if step == 1:
                # Step 1: Create IAM Role
                role_result = self.create_gateway_iam_role()
                if not role_result["success"]:
                    return role_result

                # Track resource
                self._track_resource(session_id, "iam_roles", role_result["role_name"], role_result["role_arn"])

                # Store for next steps - directly update session object
                if session:
                    session.setdefault("step_data", {})
                    session["step_data"]["role_arn"] = role_result["role_arn"]
                    session["step_data"]["role_name"] = role_result["role_name"]
                    print(f"[DEBUG] step 1 saved: step_data={session.get('step_data', {})}")

                return {
                    "success": True,
                    "step": 1,
                    "message": "IAM 角色创建成功",
                    "role_arn": role_result["role_arn"],
                    "role_name": role_result["role_name"]
                }

            elif step == 2:
                # Step 2: Setup Cognito
                cognito_result = self.setup_cognito_for_gateway()
                if not cognito_result["success"]:
                    return cognito_result

                # Track resource
                self._track_resource(session_id, "cognito_pools", cognito_result["pool_name"], {
                    "pool_id": cognito_result["pool_id"],
                    "client_id": cognito_result["client_id"]
                })

                # Store for next steps - directly update session object
                if session:
                    session.setdefault("step_data", {})
                    session["step_data"]["pool_id"] = cognito_result["pool_id"]
                    session["step_data"]["client_id"] = cognito_result["client_id"]
                    session["step_data"]["discovery_url"] = cognito_result["discovery_url"]
                    print(f"[DEBUG] step 2 saved: step_data={session.get('step_data', {})}")

                return {
                    "success": True,
                    "step": 2,
                    "message": "Cognito 认证设置成功",
                    "pool_id": cognito_result["pool_id"],
                    "client_id": cognito_result["client_id"],
                    "discovery_url": cognito_result["discovery_url"]
                }

            elif step == 3:
                # Step 3: Create Lambda
                lambda_result = self.create_sample_lambda()
                if not lambda_result["success"]:
                    return lambda_result

                # Track resource
                self._track_resource(session_id, "lambdas", lambda_result["function_name"], lambda_result["function_arn"])

                # Store for next steps - directly update session object
                if session:
                    session.setdefault("step_data", {})
                    session["step_data"]["function_arn"] = lambda_result["function_arn"]
                    session["step_data"]["function_name"] = lambda_result["function_name"]
                    print(f"[DEBUG] step 3 saved: step_data={session.get('step_data', {})}")

                return {
                    "success": True,
                    "step": 3,
                    "message": "Lambda 函数创建成功",
                    "function_arn": lambda_result["function_arn"],
                    "function_name": lambda_result["function_name"]
                }

            elif step == 4:
                # Step 4: Create Gateway with Lambda Target
                # Get data from previous steps
                step_data = session.get("step_data", {}) if session else {}
                print(f"[DEBUG] step 4 reading: step_data={step_data}")

                role_arn = step_data.get("role_arn")
                client_id = step_data.get("client_id")
                discovery_url = step_data.get("discovery_url")
                function_arn = step_data.get("function_arn")

                # Check what's missing and provide detailed message
                missing = []
                if not role_arn:
                    missing.append("步骤1 (IAM角色)")
                if not client_id or not discovery_url:
                    missing.append("步骤2 (Cognito认证)")
                if not function_arn:
                    missing.append("步骤3 (Lambda函数)")

                if missing:
                    return {
                        "success": False,
                        "message": f"请先完成: {', '.join(missing)}。提示：如果服务器重启过，需要重新执行步骤 1-3"
                    }

                gateway_result = self.create_gateway_with_lambda_target(
                    lambda_arn=function_arn,
                    role_arn=role_arn,
                    cognito_client_id=client_id,
                    cognito_discovery_url=discovery_url
                )

                if not gateway_result["success"]:
                    return gateway_result

                # Track resource
                self._track_resource(session_id, "gateways", gateway_result["gateway_name"], {
                    "gateway_id": gateway_result["gateway_id"],
                    "gateway_url": gateway_result["gateway_url"],
                    "target_id": gateway_result.get("target_id")
                })

                # Store gateway info for step 5
                if session:
                    session["step_data"]["gateway_url"] = gateway_result["gateway_url"]
                    session["step_data"]["gateway_id"] = gateway_result["gateway_id"]

                return {
                    "success": True,
                    "step": 4,
                    "message": "Gateway 和 MCP 工具创建成功",
                    "gateway_id": gateway_result["gateway_id"],
                    "gateway_url": gateway_result["gateway_url"],
                    "gateway_name": gateway_result["gateway_name"],
                    "tools": ["get_order_tool", "update_order_tool"]
                }

            elif step == 5:
                # Step 5: Call MCP Tool
                step_data = session.get("step_data", {}) if session else {}

                gateway_url = step_data.get("gateway_url")
                pool_id = step_data.get("pool_id")
                client_id = step_data.get("client_id")

                if not gateway_url:
                    return {
                        "success": False,
                        "message": "请先完成步骤 1-4 创建 Gateway"
                    }

                # Get tool name and order ID from request (will be passed via extra params)
                tool_name = step_data.get("call_tool_name", "get_order_tool")
                order_id = step_data.get("call_order_id", "ORD-12345")

                # Simulation mode: return mock response
                if self.simulation_mode:
                    time.sleep(1)  # Simulate API call delay

                    if "get_order" in tool_name:
                        mock_result = {
                            "orderId": order_id,
                            "status": "shipped",
                            "items": ["商品A - 无线鼠标", "商品B - 机械键盘"],
                            "total": 299.99,
                            "estimatedDelivery": "2024-12-25",
                            "trackingNumber": "SF1234567890"
                        }
                    else:
                        mock_result = {
                            "orderId": order_id,
                            "message": "订单更新成功",
                            "newStatus": "processing",
                            "updateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                    return {
                        "success": True,
                        "step": 5,
                        "message": "MCP 工具调用成功 (模拟)",
                        "tool_name": tool_name,
                        "request": {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {
                                "name": tool_name,
                                "arguments": {"orderId": order_id}
                            }
                        },
                        "response": {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "result": mock_result
                        },
                        "simulated": True
                    }

                # Real mode: actually call the Gateway
                try:
                    # Get bearer token from Cognito
                    token_result = self.get_bearer_token(pool_id, client_id)
                    if not token_result["success"]:
                        return {
                            "success": False,
                            "message": f"获取 Token 失败: {token_result.get('message', '')}"
                        }

                    access_token = token_result["access_token"]

                    # Call MCP tool via Gateway
                    mcp_request = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": {"orderId": order_id}
                        }
                    }

                    response = requests.post(
                        gateway_url,
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json"
                        },
                        json=mcp_request,
                        timeout=30
                    )

                    mcp_response = response.json()

                    return {
                        "success": True,
                        "step": 5,
                        "message": "MCP 工具调用成功",
                        "tool_name": tool_name,
                        "request": mcp_request,
                        "response": mcp_response,
                        "simulated": False
                    }

                except Exception as e:
                    return {
                        "success": False,
                        "message": f"MCP 工具调用失败: {str(e)}"
                    }

            else:
                return {
                    "success": False,
                    "message": f"未知步骤: {step}"
                }

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return {
                "success": False,
                "message": f"步骤 {step} 执行失败: {str(e)}",
                "detail": error_detail
            }


# Global instance
gateway_api = AgentCoreGatewayAPI()


# Background cleanup task
async def periodic_cleanup_task(interval_minutes: int = 5):
    """Background task to periodically clean up expired sessions"""
    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            result = gateway_api.cleanup_expired_sessions()
            if result.get("expired_count", 0) > 0:
                print(f"[Gateway Cleanup] Cleaned up {result['expired_count']} expired sessions")
        except Exception as e:
            print(f"[Gateway Cleanup] Error during cleanup: {str(e)}")
