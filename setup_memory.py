"""
AgentCore Memory Setup Script - 初始化 Memory 资源

这个脚本用于创建两个 Memory 资源:
1. STM (Short-Term Memory): 不配置策略，只存储原始对话
2. LTM (Long-Term Memory): 配置语义策略和用户偏好策略

运行方法:
    python setup_memory.py

输出:
    - 显示创建的 Memory ID
    - 生成环境变量设置命令
"""

import uuid
import sys
from bedrock_agentcore.memory import MemoryClient
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def create_stm_memory(client: MemoryClient) -> dict:
    """创建 Short-Term Memory (不配置策略)"""
    console.print("\n[cyan]→ 创建 Short-Term Memory (STM)...[/cyan]")

    name = f"AgentCore_STM_Demo_{uuid.uuid4().hex[:8]}"

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating STM...", total=None)

            # 创建不带策略的 Memory
            stm = client.create_memory_and_wait(
                name=name,
                strategies=[],  # 空列表 = 不配置提取策略
                description="Short-term memory demo - 仅存储原始对话",
                event_expiry_days=7  # 保存7天
            )

            progress.update(task, completed=True)

        console.print(f"[green]✓ STM 创建成功: {stm['id']}[/green]")
        console.print("[dim]特点: 即时存储、无需等待、仅会话内有效[/dim]\n")

        return stm

    except Exception as e:
        console.print(f"[red]✗ STM 创建失败: {e}[/red]")
        sys.exit(1)


def create_ltm_memory(client: MemoryClient) -> dict:
    """创建 Long-Term Memory (配置语义和偏好策略)"""
    console.print("[magenta]→ 创建 Long-Term Memory (LTM)...[/magenta]")

    name = f"AgentCore_LTM_Demo_{uuid.uuid4().hex[:8]}"

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating LTM with strategies...", total=None)

            # 创建带策略的 Memory
            ltm = client.create_memory_and_wait(
                name=name,
                strategies=[
                    # 语义记忆策略: 提取重要的事实和信息
                    {
                        "semanticMemoryStrategy": {
                            "name": "semantic_facts",
                            "description": "提取用户提到的重要事实和信息",
                            "namespaces": ["/strategies/{memoryStrategyId}/actors/{actorId}"]
                        }
                    },
                    # 用户偏好策略: 提取用户的喜好和偏好
                    {
                        "userPreferenceMemoryStrategy": {
                            "name": "user_preferences",
                            "description": "提取用户的偏好、喜好和习惯",
                            "namespaces": ["/strategies/{memoryStrategyId}/actors/{actorId}"]
                        }
                    }
                ],
                description="Long-term memory demo - 智能提取和跨会话记忆",
                event_expiry_days=30  # 保存30天
            )

            progress.update(task, completed=True)

        console.print(f"[green]✓ LTM 创建成功: {ltm['id']}[/green]")
        console.print("[dim]特点: 语义提取、跨会话、智能检索[/dim]\n")

        # 显示配置的策略
        strategies = ltm.get('strategies', [])
        if strategies:
            console.print("[yellow]配置的策略:[/yellow]")
            for strategy in strategies:
                strategy_name = strategy.get('name', 'N/A')
                strategy_type = strategy.get('type', 'N/A')
                strategy_id = strategy.get('strategyId', 'N/A')
                console.print(f"  • {strategy_name} ({strategy_type})")
                console.print(f"    ID: {strategy_id}")

        return ltm

    except Exception as e:
        console.print(f"[red]✗ LTM 创建失败: {e}[/red]")
        sys.exit(1)


def generate_export_commands(stm: dict, ltm: dict):
    """生成环境变量设置命令"""
    console.print("\n")
    console.print(Panel.fit(
        "[bold green]✓ Memory 资源创建成功![/bold green]\n\n"
        "请复制以下命令设置环境变量:\n\n"
        f"[yellow]export STM_MEMORY_ID={stm['id']}[/yellow]\n"
        f"[yellow]export LTM_MEMORY_ID={ltm['id']}[/yellow]\n\n"
        "然后运行演示程序:\n"
        "[cyan]python agentcore_memory_demo.py[/cyan]",
        border_style="green",
        title="🎉 设置完成"
    ))


def show_memory_info():
    """显示 Memory 信息说明"""
    console.print(Panel.fit(
        "[bold white]AgentCore Memory Setup[/bold white]\n\n"
        "将创建两个 Memory 资源:\n\n"
        "[cyan]1. STM (Short-Term Memory)[/cyan]\n"
        "   • 不配置策略\n"
        "   • 只存储原始对话轮次\n"
        "   • 即时存储，无需等待\n\n"
        "[magenta]2. LTM (Long-Term Memory)[/magenta]\n"
        "   • 配置语义和偏好策略\n"
        "   • 自动提取重要信息\n"
        "   • 支持跨会话检索",
        border_style="white",
        title="📝 说明"
    ))


def cleanup_old_memories(client: MemoryClient):
    """清理旧的演示 Memory (可选)"""
    console.print("\n[yellow]→ 检查是否有旧的演示 Memory...[/yellow]")

    try:
        memories = client.list_memories(max_results=100)

        demo_memories = [
            m for m in memories
            if 'AgentCore_STM_Demo_' in m.get('name', '') or
               'AgentCore_LTM_Demo_' in m.get('name', '')
        ]

        if demo_memories:
            console.print(f"[yellow]找到 {len(demo_memories)} 个旧的演示 Memory[/yellow]")

            # 询问是否删除
            response = input("是否删除旧的演示 Memory? (y/N): ")

            if response.lower() == 'y':
                console.print("[cyan]→ 删除旧的 Memory...[/cyan]")

                for memory in demo_memories:
                    memory_id = memory.get('id', memory.get('memoryId'))
                    memory_name = memory.get('name', 'Unknown')

                    try:
                        console.print(f"  - 删除: {memory_name}")
                        client.delete_memory(memory_id)
                    except Exception as e:
                        console.print(f"    [red]删除失败: {e}[/red]")

                console.print("[green]✓ 清理完成[/green]\n")
            else:
                console.print("[dim]跳过清理[/dim]\n")
        else:
            console.print("[green]没有找到旧的演示 Memory[/green]\n")

    except Exception as e:
        console.print(f"[yellow]警告: 无法检查旧 Memory: {e}[/yellow]\n")


def main():
    """主函数"""
    # 显示说明
    show_memory_info()

    try:
        # 初始化 Memory Client
        console.print("\n[cyan]→ 初始化 MemoryClient (us-west-2)...[/cyan]")
        client = MemoryClient(region_name='us-west-2')
        console.print("[green]✓ MemoryClient 初始化成功[/green]")

        # 可选: 清理旧的 Memory
        cleanup_old_memories(client)

        # 创建 STM
        stm = create_stm_memory(client)

        # 创建 LTM
        ltm = create_ltm_memory(client)

        # 生成环境变量命令
        generate_export_commands(stm, ltm)

        console.print("\n[green]✓ Setup 完成![/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Setup 被用户中断[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Setup 失败: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
