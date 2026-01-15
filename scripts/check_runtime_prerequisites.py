#!/usr/bin/env python3
"""
AgentCore Runtime 部署前置条件检查脚本

检查项：
1. AWS 凭证配置
2. .env 文件配置
3. S3 Bucket 是否存在
4. IAM 角色是否存在
5. Bedrock 模型访问权限
6. deployment_package.zip 是否存在
7. 工作空间环境（目录权限、命令可用性、磁盘空间）
"""

import os
import sys
import shutil
import subprocess
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def print_status(check_name, passed, message=""):
    """打印检查状态"""
    status = "✓" if passed else "✗"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"{color}[{status}]{reset} {check_name}")
    if message:
        print(f"    {message}")

def check_env_variables():
    """检查环境变量"""
    print("\n========== 检查环境变量 (Direct Code Deployment) ==========")
    required_vars = {
        "AWS_REGION": os.getenv("AWS_REGION"),
        "AWS_ACCOUNT_ID": os.getenv("AWS_ACCOUNT_ID"),
        "S3_BUCKET": os.getenv("S3_BUCKET"),
        "EXECUTION_ROLE_ARN": os.getenv("EXECUTION_ROLE_ARN"),
        "DEPLOYMENT_PACKAGE_PATH": os.getenv("DEPLOYMENT_PACKAGE_PATH")
    }

    all_passed = True
    for var_name, var_value in required_vars.items():
        if var_value and var_value not in ["123456789012", "bedrock-agentcore-code-123456789012-us-west-2", "arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreSDKRuntime-us-west-2"]:
            print_status(f"{var_name}", True, var_value)
        else:
            print_status(f"{var_name}", False, "未配置或使用示例值")
            all_passed = False

    # 可选: 显示 AK/SK 配置状态（但不作为必需项）
    ak = os.getenv("AWS_ACCESS_KEY_ID")
    sk = os.getenv("AWS_SECRET_ACCESS_KEY")
    if ak and sk and ak not in ["your_aws_access_key_id_here"]:
        print_status("AWS_ACCESS_KEY_ID (可选)", True, "已配置")
        print_status("AWS_SECRET_ACCESS_KEY (可选)", True, "已配置")
    else:
        print_status("AWS_ACCESS_KEY_ID (可选)", True, "未配置，将使用 IAM Role")
        print_status("AWS_SECRET_ACCESS_KEY (可选)", True, "未配置，将使用 IAM Role")

    return all_passed

def check_container_env_variables():
    """检查 Container Deployment 环境变量（可选）"""
    print("\n========== 检查环境变量 (Container Deployment - 可选) ==========")

    container_vars = {
        "CONTAINER_ECR_REPOSITORY_NAME": os.getenv("CONTAINER_ECR_REPOSITORY_NAME"),
        "CONTAINER_IMAGE_TAG": os.getenv("CONTAINER_IMAGE_TAG", "latest"),
        "CONTAINER_EXECUTION_ROLE_ARN": os.getenv("CONTAINER_EXECUTION_ROLE_ARN")
    }

    all_configured = True
    for var_name, var_value in container_vars.items():
        if var_value and var_value not in ["arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreContainerRuntime-us-west-2"]:
            print_status(f"{var_name}", True, var_value)
        else:
            print_status(f"{var_name}", False, "未配置或使用示例值")
            all_configured = False

    if not all_configured:
        print("    提示: Container Deployment 是可选功能，如不使用可忽略")

    return all_configured

def check_aws_credentials():
    """检查 AWS 凭证 (支持 IAM Role, Instance Profile, 或 AK/SK)"""
    print("\n========== 检查 AWS 凭证 ==========")
    try:
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        account = identity['Account']
        arn = identity['Arn']

        # 判断凭证来源
        if 'assumed-role' in arn:
            cred_type = "IAM Role"
        elif 'user' in arn:
            cred_type = "IAM User (AK/SK)"
        else:
            cred_type = "Unknown"

        print_status("AWS 凭证有效", True, f"Account: {account}, 类型: {cred_type}")
        print_status("ARN", True, arn)
        return True
    except NoCredentialsError:
        print_status("AWS 凭证有效", False, "未找到 AWS 凭证 (需要配置 IAM Role 或 AK/SK)")
        return False
    except Exception as e:
        print_status("AWS 凭证有效", False, str(e))
        return False

def check_s3_bucket():
    """检查 S3 Bucket 是否存在"""
    print("\n========== 检查 S3 Bucket ==========")
    bucket_name = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_REGION", "us-west-2")

    if not bucket_name or bucket_name in ["bedrock-agentcore-code-123456789012-us-west-2"]:
        print_status("S3 Bucket", False, "未配置或使用示例值")
        return False

    try:
        s3_client = boto3.client('s3', region_name=region)
        s3_client.head_bucket(Bucket=bucket_name)
        print_status(f"S3 Bucket: {bucket_name}", True, "Bucket 存在且可访问")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print_status(f"S3 Bucket: {bucket_name}", False, "Bucket 不存在")
        elif error_code == '403':
            print_status(f"S3 Bucket: {bucket_name}", False, "无权限访问")
        else:
            print_status(f"S3 Bucket: {bucket_name}", False, str(e))
        return False

def check_iam_role():
    """检查 IAM 角色是否存在"""
    print("\n========== 检查 IAM 角色 ==========")
    role_arn = os.getenv("EXECUTION_ROLE_ARN")

    if not role_arn or role_arn == "arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreSDKRuntime-us-west-2":
        print_status("IAM 角色", False, "未配置或使用示例值")
        return False

    # 从 ARN 中提取 role name
    try:
        role_name = role_arn.split('/')[-1]
        iam_client = boto3.client('iam')
        iam_client.get_role(RoleName=role_name)
        print_status(f"IAM 角色: {role_name}", True, f"角色存在\n    ARN: {role_arn}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print_status(f"IAM 角色: {role_arn}", False, "角色不存在")
        else:
            print_status(f"IAM 角色: {role_arn}", False, str(e))
        return False
    except Exception as e:
        print_status(f"IAM 角色: {role_arn}", False, f"无法解析 ARN: {str(e)}")
        return False

def check_bedrock_model_access():
    """检查 Bedrock 模型访问权限（可选检查）"""
    print("\n========== 检查 Bedrock 模型访问（可选）==========")
    region = os.getenv("AWS_REGION", "us-west-2")

    try:
        bedrock_client = boto3.client('bedrock', region_name=region)
        # 列出可用的基础模型
        response = bedrock_client.list_foundation_models()
        models = response.get('modelSummaries', [])

        # 检查 Claude 模型
        claude_models = [m for m in models if 'claude' in m.get('modelId', '').lower()]
        if claude_models:
            print_status("Bedrock 模型访问", True, f"找到 {len(claude_models)} 个 Claude 模型")
            return True
        else:
            print_status("Bedrock 模型访问", True, "未找到 Claude 模型（非必需）")
            return True  # 改为 True，作为可选检查
    except Exception as e:
        print_status("Bedrock 模型访问", True, f"跳过检查: {str(e)}")
        return True  # 改为 True，作为可选检查

def check_deployment_package():
    """检查部署包是否存在"""
    print("\n========== 检查部署包 (Direct Code Deployment) ==========")
    package_path = os.getenv("DEPLOYMENT_PACKAGE_PATH", "deployment_packages/strands_agent/deployment_package.zip")

    if os.path.exists(package_path):
        size_mb = os.path.getsize(package_path) / (1024 * 1024)
        print_status(f"部署包: {package_path}", True, f"大小: {size_mb:.2f} MB")
        return True
    else:
        print_status(f"部署包: {package_path}", False, "文件不存在，请准备部署包")
        return False

def check_ecr_image():
    """检查 ECR 镜像是否存在（Container Deployment - 可选）"""
    print("\n========== 检查 ECR 镜像 (Container Deployment - 可选) ==========")

    repository_name = os.getenv("CONTAINER_ECR_REPOSITORY_NAME")
    image_tag = os.getenv("CONTAINER_IMAGE_TAG", "latest")
    region = os.getenv("AWS_REGION", "us-west-2")
    account_id = os.getenv("AWS_ACCOUNT_ID")

    if not repository_name or repository_name == "my-strands-agent":
        print_status("ECR 镜像", False, "CONTAINER_ECR_REPOSITORY_NAME 未配置或使用示例值")
        print("    提示: 如不使用 Container Deployment 可忽略")
        return True  # 返回 True 因为这是可选检查

    if not account_id or account_id == "123456789012":
        print_status("ECR 镜像", False, "AWS_ACCOUNT_ID 未正确配置")
        return True  # 返回 True 因为这是可选检查

    try:
        ecr_client = boto3.client('ecr', region_name=region)

        # 检查仓库是否存在
        try:
            ecr_client.describe_repositories(repositoryNames=[repository_name])
            print_status(f"ECR 仓库: {repository_name}", True, "仓库存在")
        except ClientError as e:
            if e.response['Error']['Code'] == 'RepositoryNotFoundException':
                print_status(f"ECR 仓库: {repository_name}", False, "仓库不存在")
                print(f"    创建命令: aws ecr create-repository --repository-name {repository_name} --region {region}")
                return True  # 返回 True 因为这是可选检查
            else:
                raise

        # 检查镜像是否存在
        try:
            response = ecr_client.describe_images(
                repositoryName=repository_name,
                imageIds=[{'imageTag': image_tag}]
            )
            images = response.get('imageDetails', [])
            if images:
                image = images[0]
                size_mb = image.get('imageSizeInBytes', 0) / (1024 * 1024)
                pushed_at = image.get('imagePushedAt', 'Unknown')
                image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}:{image_tag}"

                print_status(f"ECR 镜像: {image_tag}", True,
                           f"镜像存在\n    URI: {image_uri}\n    大小: {size_mb:.2f} MB\n    推送时间: {pushed_at}")
                return True
            else:
                print_status(f"ECR 镜像: {image_tag}", False, "镜像不存在")
                print(f"    请先构建并推送镜像到 ECR")
                return True  # 返回 True 因为这是可选检查
        except ClientError as e:
            if e.response['Error']['Code'] == 'ImageNotFoundException':
                print_status(f"ECR 镜像: {image_tag}", False, "镜像不存在")
                print(f"    请先构建并推送镜像到 ECR")
                return True  # 返回 True 因为这是可选检查
            else:
                raise

    except Exception as e:
        print_status("ECR 镜像检查", False, f"检查失败: {str(e)}")
        print("    提示: 如不使用 Container Deployment 可忽略")
        return True  # 返回 True 因为这是可选检查

def check_workspace_environment():
    """检查工作空间环境（真实命令执行功能的前置条件）"""
    print("\n========== 检查工作空间环境 (真实命令执行) ==========")

    workspace_base = "/tmp/agentcore_workspaces"
    all_passed = True

    # 1. 检查工作目录是否可创建/可写
    try:
        os.makedirs(workspace_base, exist_ok=True)
        test_file = os.path.join(workspace_base, ".write_test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print_status(f"工作目录: {workspace_base}", True, "目录可写")
    except PermissionError:
        print_status(f"工作目录: {workspace_base}", False, "无写入权限")
        all_passed = False
    except Exception as e:
        print_status(f"工作目录: {workspace_base}", False, str(e))
        all_passed = False

    # 2. 检查 uv 命令是否可用
    uv_path = shutil.which("uv")
    if uv_path:
        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=5)
            version = result.stdout.strip() if result.returncode == 0 else "未知版本"
            print_status("uv 命令", True, f"已安装 ({version})")
        except Exception:
            print_status("uv 命令", True, f"已安装 ({uv_path})")
    else:
        print_status("uv 命令", False, "未安装 (Part 2 默认命令需要)")
        print("    安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh")
        # 不设置 all_passed = False，因为用户可以修改命令

    # 3. 检查 zip 命令是否可用
    zip_path = shutil.which("zip")
    if zip_path:
        print_status("zip 命令", True, f"已安装 ({zip_path})")
    else:
        print_status("zip 命令", False, "未安装 (Part 5-1 打包需要)")
        print("    安装命令: sudo apt-get install zip (Ubuntu/Debian)")
        # 不设置 all_passed = False，因为用户可以修改命令

    # 4. 检查磁盘空间
    try:
        stat = os.statvfs(workspace_base)
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        if free_gb >= 1.0:
            print_status("磁盘空间", True, f"可用: {free_gb:.2f} GB")
        else:
            print_status("磁盘空间", False, f"可用: {free_gb:.2f} GB (建议 >= 1 GB)")
            all_passed = False
    except Exception as e:
        print_status("磁盘空间", False, f"检查失败: {str(e)}")

    # 5. 检查 Python 版本
    python_version = sys.version_info
    if python_version >= (3, 10):
        print_status("Python 版本", True, f"{python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print_status("Python 版本", False, f"{python_version.major}.{python_version.minor} (需要 >= 3.10)")
        all_passed = False

    return all_passed

def main():
    """主函数"""
    print("=" * 60)
    print("AgentCore Runtime 部署前置条件检查")
    print("=" * 60)

    results = {
        "环境变量 (Direct Code)": check_env_variables(),
        "AWS 凭证": check_aws_credentials(),
        "S3 Bucket": check_s3_bucket(),
        "IAM 角色": check_iam_role(),
        "Bedrock 模型": check_bedrock_model_access(),
        "部署包 (Direct Code)": check_deployment_package(),
        "工作空间环境": check_workspace_environment(),
        "环境变量 (Container - 可选)": check_container_env_variables(),
        "ECR 镜像 (Container - 可选)": check_ecr_image()
    }

    print("\n" + "=" * 60)
    print("检查结果汇总")
    print("=" * 60)

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    for check_name, passed in results.items():
        print_status(check_name, passed)

    print(f"\n通过: {passed_count}/{total_count}")

    if passed_count == total_count:
        print("\n\033[92m✓ 所有检查通过，可以开始部署 Runtime！\033[0m")
        return 0
    else:
        print("\n\033[91m✗ 部分检查未通过，请修复后再试\033[0m")
        print("\n修复建议：")
        if not results["环境变量"]:
            print("  - 复制 .env.example 到 .env 并填写所有必需配置:")
            print("    * AWS_REGION")
            print("    * AWS_ACCOUNT_ID")
            print("    * S3_BUCKET")
            print("    * EXECUTION_ROLE_ARN")
            print("    * DEPLOYMENT_PACKAGE_PATH")
        if not results["AWS 凭证"]:
            print("  - 配置 AWS 凭证:")
            print("    方式1: 使用 IAM Role (EC2 Instance Profile 或 ECS Task Role)")
            print("    方式2: 运行 aws configure")
            print("    方式3: 在 .env 中配置 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY")
        if not results["S3 Bucket"]:
            print("  - 确保 S3 Bucket 已创建:")
            print("    * 在 AWS 控制台创建 Bucket")
            print("    * 或使用命令: aws s3 mb s3://你的bucket名称 --region us-west-2")
            print("    * 更新 .env 中的 S3_BUCKET 配置")
        if not results["IAM 角色"]:
            print("  - 确保 IAM 角色已创建:")
            print("    * 在 AWS IAM 控制台创建角色")
            print("    * 授予 Bedrock 和 S3 访问权限")
            print("    * 更新 .env 中的 EXECUTION_ROLE_ARN 配置")
        if not results["部署包 (Direct Code)"]:
            print("  - 参考文档准备 deployment_package.zip")
        if not results["工作空间环境"]:
            print("  - 确保工作空间环境正常:")
            print("    * 检查 /tmp 目录写入权限")
            print("    * 安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
            print("    * 安装 zip: sudo apt-get install zip")
            print("    * 确保磁盘空间 >= 1GB")
        return 1

if __name__ == "__main__":
    sys.exit(main())
