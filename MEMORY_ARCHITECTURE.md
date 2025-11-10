# AgentCore Memory 架构原理与设计

## 概述

Amazon Bedrock AgentCore Memory 是一个专为 AI Agent 设计的记忆管理服务,提供两种核心能力:

1. **Short-term Memory (STM)**: 会话内的短期记忆
2. **Long-term Memory (LTM)**: 跨会话的长期记忆

## 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AgentCore Memory 架构                         │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   AI Agent       │
│  Application     │
└────────┬─────────┘
         │
         │ SDK Calls
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              AgentCore Memory Service                        │
│                                                              │
│  ┌─────────────────────┐      ┌──────────────────────────┐ │
│  │  Memory Control     │      │  Memory Data Plane       │ │
│  │  Plane (CP)         │      │  (DP)                    │ │
│  │                     │      │                          │ │
│  │ • create_memory     │      │ • create_event           │ │
│  │ • delete_memory     │      │ • get_event              │ │
│  │ • update_strategies │      │ • list_events            │ │
│  │ • get_memory        │      │ • retrieve_memory_records│ │
│  └─────────────────────┘      │ • list_memory_records    │ │
│                               └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │                              │
         │                              │
         ▼                              ▼
┌──────────────────┐        ┌──────────────────────┐
│  Memory Resource │        │   Event Store        │
│  Configuration   │        │   (Short-term)       │
│                  │        │                      │
│ • ID             │        │ • Raw conversation   │
│ • Strategies     │        │ • Actor/Session      │
│ • Namespaces     │        │ • Timestamps         │
│ • Expiry         │        │ • Metadata           │
└──────────────────┘        └──────────────────────┘
                                     │
                                     │ Async Processing
                                     ▼
                            ┌──────────────────────┐
                            │  Memory Records      │
                            │  (Long-term)         │
                            │                      │
                            │ • Semantic facts     │
                            │ • User preferences   │
                            │ • Summaries          │
                            │ • Embeddings         │
                            └──────────────────────┘
```

## 核心概念

### 1. Memory Resource (内存资源)

Memory Resource 是 AgentCore Memory 的基本单位,由以下组成:

```python
{
    "id": "mem-xxxxxx",           # Memory 唯一标识
    "name": "MyMemory",            # 名称
    "status": "ACTIVE",            # 状态: CREATING, ACTIVE, FAILED
    "strategies": [                # 提取策略 (可选)
        {
            "name": "semantic",
            "type": "SEMANTIC",
            "strategyId": "strat-xxx",
            "namespaces": ["/strategies/{memoryStrategyId}/actors/{actorId}"]
        }
    ],
    "eventExpiryDuration": 30,    # 事件保留天数
    "createdAt": "2025-11-06T..."
}
```

### 2. Event (事件)

Event 是存储在 Short-term Memory 中的基本单位:

```python
{
    "eventId": "evt-xxxxx",
    "memoryId": "mem-xxxxx",
    "actorId": "user-123",        # 参与者 (用户/Agent)
    "sessionId": "session-456",   # 会话 ID
    "eventTimestamp": 1699564800,
    "payload": [                  # 消息内容
        {
            "conversational": {
                "role": "USER",
                "content": {"text": "Hello"}
            }
        },
        {
            "conversational": {
                "role": "ASSISTANT",
                "content": {"text": "Hi there!"}
            }
        }
    ],
    "branch": {                   # 可选: 分支信息
        "name": "alternative",
        "rootEventId": "evt-root"
    },
    "metadata": {                 # 可选: 自定义元数据
        "location": {"stringValue": "NYC"}
    }
}
```

### 3. Memory Record (记忆记录)

Memory Record 是由 LTM 策略自动提取的长期记忆:

```python
{
    "memoryRecordId": "rec-xxxxx",
    "memoryId": "mem-xxxxx",
    "memoryStrategyId": "strat-xxx",
    "namespace": "/strategies/strat-xxx/actors/user-123",
    "content": {
        "text": "用户喜欢简洁的代码风格"
    },
    "relevanceScore": 0.85,       # 相关性分数
    "sourceEventIds": ["evt-1", "evt-2"],
    "createdAt": "2025-11-06T..."
}
```

### 4. Memory Strategies (记忆策略)

AgentCore Memory 支持三种内置策略:

#### A. Semantic Memory Strategy (语义记忆)

自动提取对话中的重要事实和信息

```python
{
    "semanticMemoryStrategy": {
        "name": "facts",
        "description": "提取重要事实",
        "namespaces": ["/strategies/{memoryStrategyId}/actors/{actorId}"]
    }
}
```

**工作原理:**
1. 监听新的 Event 创建
2. 使用 LLM 提取语义信息
3. 生成 embedding 向量
4. 存储为 Memory Record

#### B. User Preference Memory Strategy (用户偏好)

自动提取用户的喜好、偏好和习惯

```python
{
    "userPreferenceMemoryStrategy": {
        "name": "preferences",
        "description": "提取用户偏好",
        "namespaces": ["/user/{actorId}/preferences"]
    }
}
```

**工作原理:**
1. 识别表达偏好的语句
2. 提取偏好类型和内容
3. 去重和合并
4. 存储为结构化记录

#### C. Summarization Memory Strategy (摘要记忆)

对长对话进行智能摘要

```python
{
    "summarizationMemoryStrategy": {
        "name": "summaries",
        "description": "对话摘要",
        "namespaces": ["/summaries/{actorId}/{sessionId}"]
    }
}
```

## Short-term Memory (STM) 工作流程

### 流程图

```
User Input
    │
    ▼
┌─────────────────┐
│  add_turns()    │
│                 │
│ • Create Event  │
│ • Store payload │
└────────┬────────┘
         │
         │ Immediate Storage (<1s)
         │
         ▼
┌─────────────────┐
│  Event Store    │
│                 │
│ • Raw messages  │
│ • Full context  │
│ • Session-bound │
└────────┬────────┘
         │
         │ Retrieval
         │
         ▼
┌─────────────────┐
│ get_last_k_turns│
│                 │
│ • By session    │
│ • Chronological │
└─────────────────┘
```

### 代码示例

```python
# 1. 创建 STM Manager
stm_manager = MemorySessionManager(
    memory_id="stm-memory-id",
    region_name="us-west-2"
)

# 2. 存储对话
stm_manager.add_turns(
    actor_id="user-123",
    session_id="session-456",
    messages=[
        ConversationalMessage("Hello", MessageRole.USER),
        ConversationalMessage("Hi!", MessageRole.ASSISTANT)
    ]
)

# 3. 检索最近对话
turns = stm_manager.get_last_k_turns(
    actor_id="user-123",
    session_id="session-456",
    k=5  # 最近 5 轮对话
)
```

### STM 特点

| 特性 | 说明 |
|-----|------|
| 存储速度 | 即时 (<1秒) |
| 数据保真度 | 100% 保留原始内容 |
| 检索方式 | 按时间顺序 |
| 记忆范围 | 当前会话内 |
| 跨会话 | ❌ 不支持 |
| 语义搜索 | ❌ 不支持 |

## Long-term Memory (LTM) 工作流程

### 流程图

```
User Input
    │
    ▼
┌─────────────────┐
│  add_turns()    │
│                 │
│ • Create Event  │
│ • Store payload │
└────────┬────────┘
         │
         │ Immediate Storage
         │
         ▼
┌─────────────────┐
│  Event Store    │
└────────┬────────┘
         │
         │ Async Processing (5-15s)
         │
         ▼
┌──────────────────────────┐
│  Strategy Execution      │
│                          │
│ 1. Semantic Extraction   │
│    • LLM analyzes        │
│    • Extract facts       │
│    • Generate embeddings │
│                          │
│ 2. Preference Detection  │
│    • Identify preferences│
│    • Categorize          │
│    • Deduplicate         │
│                          │
│ 3. Summarization         │
│    • Create summaries    │
│    • Merge contexts      │
└──────────┬───────────────┘
           │
           ▼
┌─────────────────────────┐
│  Memory Records Store   │
│                         │
│ • Semantic facts        │
│ • User preferences      │
│ • Summaries             │
│ • Vector embeddings     │
└─────────┬───────────────┘
          │
          │ Semantic Retrieval
          │
          ▼
┌──────────────────────────┐
│ search_long_term_memories│
│                          │
│ • By semantic similarity │
│ • Cross-session          │
│ • Ranked by relevance    │
└──────────────────────────┘
```

### 代码示例

```python
# 1. 创建带策略的 LTM Memory
memory = memory_client.create_memory_and_wait(
    name="LTM_Demo",
    strategies=[
        {
            "semanticMemoryStrategy": {
                "name": "facts",
                "namespaces": ["/strategies/{memoryStrategyId}/actors/{actorId}"]
            }
        },
        {
            "userPreferenceMemoryStrategy": {
                "name": "prefs",
                "namespaces": ["/user/{actorId}/preferences"]
            }
        }
    ],
    event_expiry_days=30
)

# 2. 创建 LTM Manager
ltm_manager = MemorySessionManager(
    memory_id=memory['id'],
    region_name="us-west-2"
)

# 3. 存储对话
ltm_manager.add_turns(
    actor_id="user-123",
    session_id="session-1",
    messages=[
        ConversationalMessage("我喜欢 Python", MessageRole.USER)
    ]
)

# 4. 等待异步处理
time.sleep(15)

# 5. 在新会话中检索
memories = ltm_manager.search_long_term_memories(
    query="编程语言偏好",
    namespace_prefix="/",
    top_k=3
)
# 结果: 找到 "用户喜欢 Python"
```

### LTM 特点

| 特性 | 说明 |
|-----|------|
| 存储速度 | 异步 (5-15秒) |
| 数据保真度 | 提取摘要 (非原始) |
| 检索方式 | 语义相似度 |
| 记忆范围 | 跨会话 |
| 跨会话 | ✅ 支持 |
| 语义搜索 | ✅ 支持 |

## 最佳实践: STM + LTM 结合使用

### 架构模式

```
┌────────────────────────────────────────────────────────┐
│                  AI Agent Application                   │
└──────────────┬───────────────────────┬─────────────────┘
               │                       │
               │                       │
   STM Manager │                       │ LTM Manager
               │                       │
               ▼                       ▼
┌──────────────────────┐  ┌──────────────────────────┐
│  Short-term Memory   │  │  Long-term Memory        │
│                      │  │                          │
│  Purpose:            │  │  Purpose:                │
│  • Dialog continuity │  │  • User profiling        │
│  • Context tracking  │  │  • Preference memory     │
│  • Recent history    │  │  • Fact extraction       │
│                      │  │                          │
│  Scope:              │  │  Scope:                  │
│  • Current session   │  │  • Cross-session         │
│  • Temporary         │  │  • Persistent            │
└──────────────────────┘  └──────────────────────────┘
```

### 使用场景

#### 1. 客服聊天机器人

```python
def handle_customer_query(user_input: str, session_id: str, user_id: str):
    # 1. 从 STM 获取当前会话历史
    recent_context = stm_manager.get_last_k_turns(
        actor_id=user_id,
        session_id=session_id,
        k=5
    )

    # 2. 从 LTM 获取用户画像和偏好
    user_profile = ltm_manager.search_long_term_memories(
        query=user_input,
        namespace_prefix=f"/user/{user_id}",
        top_k=3
    )

    # 3. 结合两者生成回复
    response = generate_response(
        user_input=user_input,
        recent_context=recent_context,
        user_profile=user_profile
    )

    # 4. 存储到两个 Memory
    stm_manager.add_turns(...)
    ltm_manager.add_turns(...)

    return response
```

#### 2. 个性化学习助手

```python
def tutoring_session(question: str, student_id: str):
    # STM: 跟踪当前学习进度
    current_topic = stm_manager.get_last_k_turns(...)

    # LTM: 了解学生的学习风格和难点
    learning_profile = ltm_manager.search_long_term_memories(
        query="学习风格 困难点",
        namespace_prefix=f"/student/{student_id}",
        top_k=5
    )

    # 根据学生特点调整教学方式
    response = customize_teaching(question, learning_profile)

    return response
```

## 命名空间 (Namespace) 设计

### 命名空间的作用

命名空间用于组织和隔离 Memory Records:

```
/                                    # 根命名空间
├── strategies/
│   ├── {strategyId}/
│   │   └── actors/
│   │       └── {actorId}/          # 按策略+用户组织
│   │           ├── record-1
│   │           └── record-2
│
├── user/
│   └── {actorId}/
│       ├── preferences/             # 用户偏好
│       ├── profile/                 # 用户画像
│       └── history/                 # 历史记录
│
└── session/
    └── {sessionId}/
        └── summaries/               # 会话摘要
```

### 模板变量

命名空间支持以下模板变量:

- `{actorId}`: 替换为实际的用户/Agent ID
- `{sessionId}`: 替换为实际的会话 ID
- `{memoryStrategyId}`: 替换为策略 ID

示例:

```python
# 配置时
namespaces = ["/strategies/{memoryStrategyId}/actors/{actorId}"]

# 实际存储时自动替换为
# /strategies/strat-123/actors/user-456
```

## 性能与成本考虑

### STM 成本

| 操作 | API 调用 | 延迟 | 成本 |
|------|---------|------|------|
| 存储 Event | create_event | <100ms | 低 |
| 检索 Events | list_events | <200ms | 低 |
| 获取单个 Event | get_event | <100ms | 低 |

### LTM 成本

| 操作 | API 调用 | 延迟 | 成本 |
|------|---------|------|------|
| 存储 Event | create_event | <100ms | 低 |
| 策略处理 | 异步后台 | 5-15s | 中 (LLM) |
| 语义检索 | retrieve_memory_records | <500ms | 中 (embedding) |

### 优化建议

1. **STM 优化**
   - 限制保留的 Event 数量 (eventExpiryDays)
   - 使用 `k` 参数限制检索数量
   - 按需加载 payload (includePayloads=False)

2. **LTM 优化**
   - 选择合适的策略 (不是所有对话都需要提取)
   - 设置合理的 namespace 隔离
   - 使用 relevance_score 过滤低相关性结果
   - 批量处理而非实时处理

3. **结合使用优化**
   - STM 用于高频、短期场景
   - LTM 用于低频、长期场景
   - 根据业务需求选择性存储

## 安全与隐私

### 1. 数据隔离

- 每个 Memory Resource 独立隔离
- Actor 和 Session 级别隔离
- Namespace 实现多租户隔离

### 2. 访问控制

- IAM 角色和策略控制
- 细粒度权限管理
- 审计日志支持

### 3. 数据保留

- 可配置的 Event 过期时间
- 支持手动删除
- GDPR 合规性支持

```python
# 删除特定用户的所有记忆
manager.delete_all_long_term_memories_in_namespace(
    namespace=f"/user/{user_id}"
)
```

## 总结

AgentCore Memory 提供了一个完整的记忆管理解决方案:

- **STM**: 快速、准确、会话内
- **LTM**: 智能、持久、跨会话
- **结合使用**: 兼顾短期连贯性和长期个性化

选择合适的策略和架构模式,可以构建出强大的记忆增强型 AI Agent 应用。
