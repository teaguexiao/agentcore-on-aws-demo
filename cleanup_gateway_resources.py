#!/usr/bin/env python3
"""
Gateway Demo 资源清理脚本

清理所有由 Gateway Demo 创建的 AWS 资源，包括：
- AgentCore Gateways (名称包含 gateway-lambda, gateway-openapi, gateway-search)
- Lambda 函数 (名称包含 gateway-demo-lambda, search-demo-lambda)
- Cognito 用户池 (名称包含 gateway-pool)
- IAM 角色 (名称包含 agentcore-gateway-role)

使用方法：
    python cleanup_gateway_resources.py --dry-run    # 预览要删除的资源
    python cleanup_gateway_resources.py              # 实际删除资源
"""

import boto3
import argparse
import time
from datetime import datetime


def get_demo_gateways(client):
    """获取所有 Demo 创建的 Gateway"""
    gateways = []
    try:
        response = client.list_gateways(maxResults=100)
        for item in response.get('items', []):
            name = item.get('name', '')
            # 匹配 Demo 创建的 Gateway 命名模式
            if any(pattern in name for pattern in ['gateway-lambda', 'gateway-openapi', 'gateway-search']):
                gateways.append({
                    'id': item.get('gatewayId'),
                    'name': name,
                    'status': item.get('status'),
                    'created': str(item.get('createdAt', ''))
                })
    except Exception as e:
        print(f"Error listing gateways: {e}")
    return gateways


def get_demo_lambdas(client):
    """获取所有 Demo 创建的 Lambda 函数"""
    lambdas = []
    try:
        paginator = client.get_paginator('list_functions')
        for page in paginator.paginate():
            for func in page.get('Functions', []):
                name = func.get('FunctionName', '')
                if any(pattern in name for pattern in ['gateway-demo-lambda', 'search-demo-lambda']):
                    lambdas.append({
                        'name': name,
                        'arn': func.get('FunctionArn'),
                        'modified': str(func.get('LastModified', ''))
                    })
    except Exception as e:
        print(f"Error listing lambdas: {e}")
    return lambdas


def get_demo_cognito_pools(client):
    """获取所有 Demo 创建的 Cognito 用户池"""
    pools = []
    try:
        response = client.list_user_pools(MaxResults=60)
        for pool in response.get('UserPools', []):
            name = pool.get('Name', '')
            if 'gateway-pool' in name or 'gateway-openapi-pool' in name or 'gateway-search-pool' in name:
                pools.append({
                    'id': pool.get('Id'),
                    'name': name,
                    'created': str(pool.get('CreationDate', ''))
                })
    except Exception as e:
        print(f"Error listing cognito pools: {e}")
    return pools


def get_demo_iam_roles(client):
    """获取所有 Demo 创建的 IAM 角色"""
    roles = []
    try:
        paginator = client.get_paginator('list_roles')
        for page in paginator.paginate():
            for role in page.get('Roles', []):
                name = role.get('RoleName', '')
                if any(pattern in name for pattern in ['agentcore-gateway-role', 'gateway-demo-lambda', 'search-demo-lambda']):
                    roles.append({
                        'name': name,
                        'arn': role.get('Arn'),
                        'created': str(role.get('CreateDate', ''))
                    })
    except Exception as e:
        print(f"Error listing IAM roles: {e}")
    return roles


def delete_gateway(client, gateway_id, gateway_name):
    """删除 Gateway 及其所有 targets"""
    try:
        # 先删除所有 targets
        try:
            targets = client.list_gateway_targets(gatewayIdentifier=gateway_id, maxResults=100)
            for target in targets.get('items', []):
                target_id = target.get('targetId')
                print(f"    删除 Target: {target_id}")
                client.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
                time.sleep(2)
        except Exception as e:
            print(f"    警告: 删除 targets 时出错: {e}")

        # 删除 Gateway
        client.delete_gateway(gatewayIdentifier=gateway_id)
        print(f"  ✓ Gateway 已删除: {gateway_name}")
        return True
    except Exception as e:
        print(f"  ✗ Gateway 删除失败: {gateway_name} - {e}")
        return False


def delete_lambda(client, function_name):
    """删除 Lambda 函数"""
    try:
        client.delete_function(FunctionName=function_name)
        print(f"  ✓ Lambda 已删除: {function_name}")
        return True
    except Exception as e:
        print(f"  ✗ Lambda 删除失败: {function_name} - {e}")
        return False


def delete_cognito_pool(client, pool_id, pool_name):
    """删除 Cognito 用户池"""
    try:
        # 先尝试删除域名
        try:
            domain_prefix = pool_id.replace("_", "").lower()
            client.delete_user_pool_domain(Domain=domain_prefix, UserPoolId=pool_id)
        except Exception:
            pass

        client.delete_user_pool(UserPoolId=pool_id)
        print(f"  ✓ Cognito Pool 已删除: {pool_name}")
        return True
    except Exception as e:
        print(f"  ✗ Cognito Pool 删除失败: {pool_name} - {e}")
        return False


def delete_iam_role(client, role_name):
    """删除 IAM 角色及其策略"""
    try:
        # 删除内联策略
        try:
            policies = client.list_role_policies(RoleName=role_name)
            for policy_name in policies.get('PolicyNames', []):
                client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        except Exception:
            pass

        # 分离托管策略
        try:
            attached = client.list_attached_role_policies(RoleName=role_name)
            for policy in attached.get('AttachedPolicies', []):
                client.detach_role_policy(RoleName=role_name, PolicyArn=policy['PolicyArn'])
        except Exception:
            pass

        # 删除角色
        client.delete_role(RoleName=role_name)
        print(f"  ✓ IAM Role 已删除: {role_name}")
        return True
    except Exception as e:
        print(f"  ✗ IAM Role 删除失败: {role_name} - {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='清理 Gateway Demo 创建的 AWS 资源')
    parser.add_argument('--dry-run', action='store_true', help='仅预览要删除的资源，不实际删除')
    parser.add_argument('--region', default='us-west-2', help='AWS 区域 (默认: us-west-2)')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Gateway Demo 资源清理工具")
    print(f"区域: {args.region}")
    print(f"模式: {'预览 (dry-run)' if args.dry_run else '实际删除'}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 初始化 AWS 客户端
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=args.region)
    lambda_client = boto3.client('lambda', region_name=args.region)
    cognito_client = boto3.client('cognito-idp', region_name=args.region)
    iam_client = boto3.client('iam', region_name=args.region)

    # 收集资源
    print("📋 扫描 Demo 创建的资源...\n")

    gateways = get_demo_gateways(gateway_client)
    lambdas = get_demo_lambdas(lambda_client)
    pools = get_demo_cognito_pools(cognito_client)
    roles = get_demo_iam_roles(iam_client)

    # 显示资源摘要
    print(f"发现的资源:")
    print(f"  • Gateways: {len(gateways)}")
    print(f"  • Lambda 函数: {len(lambdas)}")
    print(f"  • Cognito 用户池: {len(pools)}")
    print(f"  • IAM 角色: {len(roles)}")
    print()

    total_resources = len(gateways) + len(lambdas) + len(pools) + len(roles)
    if total_resources == 0:
        print("✅ 没有发现需要清理的 Demo 资源")
        return

    # 详细列表
    if gateways:
        print("📦 Gateways:")
        for gw in gateways:
            print(f"    - {gw['name']} ({gw['id']}) [{gw['status']}]")
        print()

    if lambdas:
        print("⚡ Lambda 函数:")
        for func in lambdas:
            print(f"    - {func['name']}")
        print()

    if pools:
        print("🔐 Cognito 用户池:")
        for pool in pools:
            print(f"    - {pool['name']} ({pool['id']})")
        print()

    if roles:
        print("👤 IAM 角色:")
        for role in roles:
            print(f"    - {role['name']}")
        print()

    if args.dry_run:
        print("="*60)
        print("⚠️  这是预览模式，未实际删除任何资源")
        print("   运行 'python cleanup_gateway_resources.py' 来实际删除")
        print("="*60)
        return

    # 确认删除
    print("="*60)
    confirm = input(f"⚠️  即将删除 {total_resources} 个资源，确认吗? (yes/no): ")
    if confirm.lower() != 'yes':
        print("已取消")
        return

    print("\n🗑️  开始删除资源...\n")

    deleted = 0
    failed = 0

    # 删除 Gateways (先删除，因为它依赖其他资源)
    if gateways:
        print("删除 Gateways...")
        for gw in gateways:
            if delete_gateway(gateway_client, gw['id'], gw['name']):
                deleted += 1
            else:
                failed += 1
            time.sleep(1)
        print()

    # 删除 Lambdas
    if lambdas:
        print("删除 Lambda 函数...")
        for func in lambdas:
            if delete_lambda(lambda_client, func['name']):
                deleted += 1
            else:
                failed += 1
        print()

    # 删除 Cognito Pools
    if pools:
        print("删除 Cognito 用户池...")
        for pool in pools:
            if delete_cognito_pool(cognito_client, pool['id'], pool['name']):
                deleted += 1
            else:
                failed += 1
        print()

    # 删除 IAM Roles
    if roles:
        print("删除 IAM 角色...")
        for role in roles:
            if delete_iam_role(iam_client, role['name']):
                deleted += 1
            else:
                failed += 1
        print()

    # 结果摘要
    print("="*60)
    print(f"清理完成!")
    print(f"  ✓ 成功删除: {deleted}")
    print(f"  ✗ 删除失败: {failed}")
    print("="*60)


if __name__ == "__main__":
    main()
