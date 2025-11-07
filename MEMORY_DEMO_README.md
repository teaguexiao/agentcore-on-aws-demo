# AgentCore Memory 演示程序使用说明

## 🎯 演示目标

本演示程序展示 Amazon Bedrock AgentCore Memory 的两大核心能力:

1. **Short-term Memory (STM)** - 会话内的短期记忆
2. **Long-term Memory (LTM)** - 跨会话的长期记忆
3. **STM + LTM 结合** - 最佳实践模式

## 📋 前置条件

### 1. AWS 账户配置

```bash
# 配置 AWS 凭证
aws configure

# 或设置环境变量
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-west-2
```

### 2. IAM 权限

确保您的 AWS 账户具有以下权限:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateMemory",
        "bedrock-agentcore:GetMemory",
        "bedrock-agentcore:DeleteMemory",
        "bedrock-agentcore:UpdateMemory",
        "bedrock-agentcore:ListMemories",
        "bedrock-agentcore:CreateEvent",
        "bedrock-agentcore:GetEvent",
        "bedrock-agentcore:ListEvents",
        "bedrock-agentcore:DeleteEvent",
        "bedrock-agentcore:RetrieveMemoryRecords",
        "bedrock-agentcore:ListMemoryRecords",
        "bedrock-agentcore:GetMemoryRecord",
        "bedrock-agentcore:DeleteMemoryRecord",
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Python 环境

- Python 3.10 或更高版本
- 已安装所需依赖 (见下方)

## 🚀 快速开始

### 步骤 1: 安装依赖

```bash
# 确保已安装以下包
pip install bedrock-agentcore>=0.1.0
pip install boto3>=1.34.0
pip install rich>=13.0.0
```

或者使用项目的 requirements.txt:

```bash
pip install -r requirements.txt
```

### 步骤 2: 初始化 Memory 资源

运行 setup 脚本创建 STM 和 LTM Memory:

```bash
python setup_memory.py
```

**输出示例:**

```
📝 说明
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ AgentCore Memory Setup                              ┃
┃                                                      ┃
┃ 将创建两个 Memory 资源:                               ┃
┃                                                      ┃
┃ 1. STM (Short-Term Memory)                          ┃
┃    • 不配置策略                                       ┃
┃    • 只存储原始对话轮次                               ┃
┃    • 即时存储，无需等待                               ┃
┃                                                      ┃
┃ 2. LTM (Long-Term Memory)                           ┃
┃    • 配置语义和偏好策略                               ┃
┃    • 自动提取重要信息                                 ┃
┃    • 支持跨会话检索                                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

→ 初始化 MemoryClient (us-west-2)...
✓ MemoryClient 初始化成功

→ 创建 Short-Term Memory (STM)...
✓ STM 创建成功: mem-abc123...
特点: 即时存储、无需等待、仅会话内有效

→ 创建 Long-Term Memory (LTM)...
✓ LTM 创建成功: mem-def456...
特点: 语义提取、跨会话、智能检索

🎉 设置完成
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✓ Memory 资源创建成功!                                ┃
┃                                                      ┃
┃ 请复制以下命令设置环境变量:                           ┃
┃                                                      ┃
┃ export STM_MEMORY_ID=mem-abc123...                  ┃
┃ export LTM_MEMORY_ID=mem-def456...                  ┃
┃                                                      ┃
┃ 然后运行演示程序:                                     ┃
┃ python agentcore_memory_demo.py                     ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### 步骤 3: 设置环境变量

复制 setup_memory.py 输出的命令:

```bash
export STM_MEMORY_ID=mem-abc123...
export LTM_MEMORY_ID=mem-def456...
```

### 步骤 4: 运行演示

```bash
python agentcore_memory_demo.py
```

## 📊 演示内容

### Demo 1: Short-term Memory

**场景:** 会话内的连续对话

**演示流程:**
1. 用户介绍自己的信息 (姓名、职业、爱好)
2. AI 助手即时记忆
3. 用户询问之前提到的信息
4. AI 助手从 STM 检索并回答

**关键特性:**
- ✅ 即时存储 (<1秒)
- ✅ 完整保留对话细节
- ✅ 适合会话内连贯对话
- ❌ 不支持跨会话

### Demo 2: Long-term Memory

**场景:** 跨会话的用户偏好记忆

**演示流程:**
1. Session 1: 用户表达编程偏好 (如: 喜欢 TypeScript)
2. 等待 LTM 异步处理 (10-15秒)
3. Session 2: 新会话中询问编程建议
4. AI 助手从 LTM 检索用户偏好并提供个性化建议

**关键特性:**
- ✅ 跨会话记忆
- ✅ 自动提取用户偏好
- ✅ 语义相关性检索
- ⏱️ 需要等待异步处理 (5-15秒)

### Demo 3: STM + LTM 结合

**场景:** 最佳实践 - 同时利用两者优势

**演示流程:**
1. 结合 STM 的会话历史
2. 结合 LTM 的长期记忆
3. 提供更全面的上下文给 AI
4. 生成更个性化、更连贯的回复

**关键特性:**
- ✅ 短期记忆 + 长期记忆
- ✅ 会话连贯性 + 个性化
- ✅ 适合生产环境

## 🔧 高级配置

### 自定义 Memory 策略

编辑 `setup_memory.py` 中的策略配置:

```python
strategies=[
    # 语义记忆
    {
        "semanticMemoryStrategy": {
            "name": "custom_facts",
            "description": "提取特定领域的事实",
            "namespaces": ["/domain/{actorId}"]
        }
    },
    # 用户偏好
    {
        "userPreferenceMemoryStrategy": {
            "name": "user_prefs",
            "description": "用户个人偏好",
            "namespaces": ["/user/{actorId}/prefs"]
        }
    },
    # 摘要记忆
    {
        "summarizationMemoryStrategy": {
            "name": "summaries",
            "description": "对话摘要",
            "namespaces": ["/summaries/{sessionId}"]
        }
    }
]
```

### 自定义检索配置

在 `agentcore_memory_demo.py` 中修改:

```python
retrieval_config = {
    # 命名空间 -> 检索配置
    "/user/{actorId}/preferences": RetrievalConfig(
        top_k=5,                    # 返回前5个结果
        relevance_score=0.7,        # 最低相关性分数
        retrieval_query="用户偏好"   # 自定义查询
    ),
    "/strategies/{memoryStrategyId}/actors/{actorId}": RetrievalConfig(
        top_k=3,
        relevance_score=0.5
    )
}
```

### 自定义 LLM 模型

修改 `call_llm()` 方法中的模型 ID:

```python
response = self.bedrock_runtime.converse(
    modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",  # 修改这里
    messages=[...],
    inferenceConfig={
        "maxTokens": 2000,
        "temperature": 0.7,
    }
)
```

支持的模型:
- `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (Claude 3.7 Sonnet)
- `us.anthropic.claude-3-5-sonnet-20241022-v2:0` (Claude 3.5 Sonnet v2)
- `us.anthropic.claude-3-5-sonnet-20240620-v1:0` (Claude 3.5 Sonnet v1)

## 📖 代码结构

```
agentcore-on-aws-demo/
├── agentcore_memory_demo.py      # 主演示程序
│   ├── AgentCoreMemoryDemo       # 演示类
│   ├── demo_short_term_memory()  # STM 演示
│   ├── demo_long_term_memory()   # LTM 演示
│   └── demo_combined_memory()    # 结合演示
│
├── setup_memory.py                # Memory 初始化脚本
│   ├── create_stm_memory()       # 创建 STM
│   └── create_ltm_memory()       # 创建 LTM
│
├── MEMORY_ARCHITECTURE.md         # 架构原理文档
│
└── MEMORY_DEMO_README.md          # 本文档
```

## 🐛 故障排查

### 问题 1: 无法创建 Memory

**错误:**
```
ClientError: An error occurred (AccessDeniedException) when calling the CreateMemory operation
```

**解决方案:**
1. 检查 AWS 凭证是否正确配置
2. 确认 IAM 角色具有必要权限
3. 检查区域是否支持 AgentCore Memory (us-west-2)

### 问题 2: LTM 检索不到记忆

**可能原因:**
1. 等待时间不足 (需要 10-15 秒)
2. 命名空间配置错误
3. 相关性分数阈值过高

**解决方案:**
```python
# 1. 增加等待时间
time.sleep(20)

# 2. 检查命名空间
memories = ltm_manager.list_long_term_memory_records(
    namespace_prefix="/",  # 使用根命名空间查看所有记录
    max_results=100
)

# 3. 降低相关性阈值
retrieval_config = {
    "/": RetrievalConfig(
        top_k=10,
        relevance_score=0.3  # 降低阈值
    )
}
```

### 问题 3: LLM 调用失败

**错误:**
```
ClientError: An error occurred (ThrottlingException)
```

**解决方案:**
1. 添加重试逻辑
2. 增加调用间隔
3. 请求提高 API 配额

### 问题 4: 内存清理

**删除演示 Memory:**

```python
from bedrock_agentcore.memory import MemoryClient

client = MemoryClient(region_name='us-west-2')

# 列出所有 Memory
memories = client.list_memories()

# 删除演示 Memory
for memory in memories:
    if 'Demo' in memory.get('name', ''):
        client.delete_memory(memory['id'])
        print(f"Deleted: {memory['name']}")
```

## 📚 延伸阅读

### 官方文档

- [AgentCore Memory 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-memory.html)
- [Bedrock AgentCore SDK](https://github.com/awslabs/bedrock-agentcore-sdk)
- [MEMORY_ARCHITECTURE.md](./MEMORY_ARCHITECTURE.md) - 本项目的架构说明

### 相关示例

- [Semantic Search Example](https://aws.github.io/bedrock-agentcore-starter-toolkit/examples/semantic_search.md)
- [Memory Gateway Agent](https://aws.github.io/bedrock-agentcore-starter-toolkit/examples/memory_gateway_agent.md)

### 博客和教程

- [Building Memory-Enhanced AI Agents with AgentCore](https://aws.amazon.com/blogs/machine-learning/)
- [Best Practices for Agent Memory Management](https://docs.aws.amazon.com/bedrock/)

## 💡 最佳实践

### 1. 选择合适的 Memory 类型

| 场景 | 推荐方案 |
|-----|---------|
| 单次对话 | 仅 STM |
| 客服系统 | STM + LTM (用户画像) |
| 学习助手 | STM + LTM (学习进度) |
| 代码助手 | STM + LTM (偏好风格) |

### 2. 优化性能

```python
# ✅ 好的做法
- 限制 get_last_k_turns 的 k 值 (<=10)
- 使用命名空间隔离不同类型的记忆
- 设置合理的 event_expiry_days

# ❌ 避免
- 不要存储过大的 payload (>10KB)
- 不要频繁创建/删除 Memory Resource
- 不要在每次对话都进行 LTM 检索
```

### 3. 成本控制

```python
# STM: 低成本
- 主要是 API 调用费用
- 按 Event 数量计费

# LTM: 中等成本
- 包含 LLM 处理费用
- 包含 embedding 生成费用
- 按提取的 Memory Record 数量计费

# 优化建议
- 使用 STM 处理大部分对话
- 只在关键场景使用 LTM
- 定期清理过期 Event
```

### 4. 安全与隐私

```python
# GDPR 合规
def delete_user_data(user_id: str):
    # 删除用户的所有 Memory Records
    manager.delete_all_long_term_memories_in_namespace(
        namespace=f"/user/{user_id}"
    )

    # 删除用户的 Events (需要枚举 session)
    sessions = manager.list_actor_sessions(user_id)
    for session in sessions:
        events = manager.list_events(user_id, session['sessionId'])
        for event in events:
            manager.delete_event(user_id, session['sessionId'], event['eventId'])
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request!

## 📄 许可证

本演示程序遵循 MIT 许可证。

---

**有问题?** 请查看 [MEMORY_ARCHITECTURE.md](./MEMORY_ARCHITECTURE.md) 了解更多架构细节。

**下一步:** 尝试将 Memory 集成到您的 AI Agent 应用中!
