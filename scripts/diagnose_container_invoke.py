#!/usr/bin/env python3
"""
Container Runtime 调用诊断工具

用法:
    python scripts/diagnose_container_invoke.py <runtime_id> <runtime_arn>

示例:
    python scripts/diagnose_container_invoke.py \\
        "abc123def456" \\
        "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/abc123def456"
"""

import boto3
import json
import sys
import os


def diagnose_runtime(runtime_id, runtime_arn, region='us-west-2'):
    """诊断 Container Runtime 调用问题"""

    print("=" * 60)
    print("Container Runtime 调用诊断工具")
    print("=" * 60)

    # 1. 检查 Runtime 状态
    print("\n1. 检查 Runtime 状态...")
    control_client = boto3.client('bedrock-agentcore-control', region_name=region)
    try:
        response = control_client.get_agent_runtime(
            agentRuntimeId=runtime_id,
            agentRuntimeVersion='1'
        )
        status = response['status']
        print(f"   ✓ Runtime ID: {runtime_id}")
        print(f"   ✓ Status: {status}")

        if status != 'READY':
            print(f"   ✗ 错误: Runtime 状态不是 READY，无法调用")
            print(f"   提示: 等待 Runtime 部署完成，通常需要 2-5 分钟")
            return False

        print(f"   ✓ Runtime ARN: {response.get('agentRuntimeArn', 'N/A')}")
        print(f"   ✓ 创建时间: {response.get('createdAt', 'N/A')}")

    except Exception as e:
        print(f"   ✗ 错误: {str(e)}")
        print(f"   提示: 检查 Runtime ID 是否正确")
        return False

    # 2. 检查 Runtime ARN 格式
    print("\n2. 检查 Runtime ARN 格式...")
    if not runtime_arn.startswith('arn:aws:bedrock-agentcore:'):
        print(f"   ✗ 错误: Runtime ARN 格式不正确")
        print(f"   当前 ARN: {runtime_arn}")
        print(f"   正确格式: arn:aws:bedrock-agentcore:<region>:<account>:agent-runtime/<id>")
        return False
    print(f"   ✓ ARN 格式正确")

    # 3. 检查 Session ID 长度
    print("\n3. 检查 Session ID 要求...")
    test_session_id = 'diagnostic-test-session-12345678901234567890'
    if len(test_session_id) < 33:
        print(f"   ✗ 错误: Session ID 长度不足 (当前: {len(test_session_id)}, 最小: 33)")
        return False
    print(f"   ✓ 测试 Session ID 长度符合要求: {len(test_session_id)} 字符")

    # 4. 测试 Container payload 格式
    print("\n4. 测试 Container Payload 格式...")
    test_payload = json.dumps({
        "input": {"prompt": "test"}
    })
    print(f"   ✓ 使用 Container payload 格式: {test_payload}")

    # 5. 测试调用
    print("\n5. 测试 Runtime 调用...")
    agentcore_client = boto3.client('bedrock-agentcore', region_name=region)

    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=test_session_id,
            payload=test_payload,
            qualifier="DEFAULT"
        )

        response_body = response['response'].read()
        response_data = json.loads(response_body)

        print(f"   ✓ 调用成功!")
        print(f"\n   响应内容:")
        print(f"   {json.dumps(response_data, indent=6, ensure_ascii=False)}")

        # 检查响应格式
        if 'output' in response_data:
            print(f"\n   ✓ 响应格式正确: 包含 'output' 字段")
        else:
            print(f"\n   ⚠ 警告: 响应格式可能不标准，缺少 'output' 字段")

        return True

    except Exception as e:
        error_message = str(e)
        print(f"   ✗ 调用失败: {error_message}")

        print(f"\n   可能的原因:")

        if "not found" in error_message.lower():
            print(f"   - Runtime ARN 不正确或 Runtime 已被删除")
            print(f"   - 建议: 在 Part 8 中重新检查 Runtime 状态")

        elif "not ready" in error_message.lower():
            print(f"   - Runtime 还未就绪")
            print(f"   - 建议: 等待 Runtime 状态变为 READY")

        elif "validation" in error_message.lower():
            print(f"   - Payload 格式错误")
            print(f"   - Container 应使用: {{'input': {{'prompt': '...'}}}}")

        elif "404" in error_message or "endpoint" in error_message.lower():
            print(f"   - Container agent.py 的 /invocations 端点未正确实现")
            print(f"   - 建议: 检查部署的 agent.py 代码")

        elif "500" in error_message:
            print(f"   - Agent 代码内部错误")
            print(f"   - 建议: 查看 CloudWatch 日志")
            print(f"   - 日志组: /aws/bedrock/agentcore/runtime/")

        elif "timeout" in error_message.lower():
            print(f"   - 网络超时或 Runtime 响应超时")
            print(f"   - 建议: 检查 Runtime 网络配置")

        elif "access" in error_message.lower() or "denied" in error_message.lower():
            print(f"   - IAM 权限不足")
            print(f"   - 建议: 确保有 bedrock-agentcore:InvokeAgentRuntime 权限")

        else:
            print(f"   - 其他错误，请查看完整错误消息")

        print(f"\n   调试建议:")
        print(f"   1. 检查 CloudWatch 日志: /aws/bedrock/agentcore/runtime/")
        print(f"   2. 验证 ECR 镜像架构是 linux/arm64")
        print(f"   3. 确认 agent.py 实现了正确的端点")

        return False


def main():
    if len(sys.argv) < 3:
        print("用法: python diagnose_container_invoke.py <runtime_id> <runtime_arn>")
        print("\n示例:")
        print('  python diagnose_container_invoke.py \\')
        print('    "abc123def456" \\')
        print('    "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/abc123def456"')
        sys.exit(1)

    runtime_id = sys.argv[1]
    runtime_arn = sys.argv[2]

    # 可选: 从环境变量读取 region
    region = os.getenv('AWS_REGION', 'us-west-2')

    success = diagnose_runtime(runtime_id, runtime_arn, region)

    print("\n" + "=" * 60)
    if success:
        print("✓ 诊断完成: 一切正常，Runtime 可以正常调用")
        print("\n下一步:")
        print("  - 在浏览器中使用 Part 9 调用 Agent")
        print("  - 尝试不同的 prompt 测试功能")
    else:
        print("✗ 诊断完成: 发现问题，请查看上面的错误信息和建议")
        print("\n如需进一步帮助:")
        print("  1. 查看 TROUBLESHOOTING_CONTAINER_INVOKE.md")
        print("  2. 收集 CloudWatch 日志")
        print("  3. 提交 GitHub Issue")
    print("=" * 60)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
