# 🌊 流式响应功能说明

## ✨ 新功能

现在创建STM/LTM Memory时，**所有日志和代码会实时流式地显示**，不再需要等待全部完成后一次性显示！

### 技术实现

- **后端**: Server-Sent Events (SSE)
- **前端**: EventSource API
- **效果**: 像终端一样实时输出日志

---

## 🎯 用户体验

### 创建Memory时的流程

#### 1. 点击"创建 STM Memory"按钮

**你会看到**:
```
🚀 开始创建 Short-Term Memory (STM)
📡 初始化 MemoryClient...
✅ MemoryClient 初始化成功 (region: us-west-2)
📝 生成 Memory 名称: AgentCore_STM_Demo_abc123
⏳ 调用 AWS Bedrock AgentCore API 创建 Memory...
   - 名称: AgentCore_STM_Demo_abc123
   - 策略: 无 (STM 不需要提取策略)
   - 事件保留期: 7 天

⏳ 正在创建，请稍候...
```

*此时系统正在调用AWS API创建Memory资源...*

```
✅ STM 创建成功!
   - Memory ID: mem-xxxxx-xxxxx-xxxxx
   - 状态: ACTIVE
   - 创建时间: 2025-11-07T...

💡 提示: STM 适用于会话内的短期记忆，即时存储，无需等待
```

#### 2. 点击"创建 LTM Memory"按钮

**你会看到**:
```
🚀 开始创建 Long-Term Memory (LTM)
📡 初始化 MemoryClient...
✅ MemoryClient 初始化成功 (region: us-west-2)
📝 生成 Memory 名称: AgentCore_LTM_Demo_def456
⏳ 调用 AWS Bedrock AgentCore API 创建 Memory...
   - 名称: AgentCore_LTM_Demo_def456
   - 策略: 2 个 (语义记忆 + 用户偏好)
   - 事件保留期: 30 天

⚙️ 配置策略 1: Semantic Memory Strategy
   - 自动提取重要事实和信息
   - 使用 LLM 进行语义分析

⚙️ 配置策略 2: User Preference Memory Strategy
   - 自动提取用户偏好
   - 支持跨会话记忆

⏳ 正在创建并配置策略，请稍候...
```

*此时系统正在调用AWS API创建Memory资源并配置策略...*

```
✅ LTM 创建成功!
   - Memory ID: mem-yyyyy-yyyyy-yyyyy
   - 状态: ACTIVE
   - 创建时间: 2025-11-07T...
   - 策略: semantic_facts (SEMANTIC_MEMORY_STRATEGY)
   - 策略: user_preferences (USER_PREFERENCE_MEMORY_STRATEGY)

💡 提示: LTM 会异步提取记忆，通常需要 10-15 秒完成
```

### 同时显示的内容

在日志输出的同时，代码区域也会显示相应的Python代码示例：

```python
from bedrock_agentcore.memory import MemoryClient

# 初始化 Memory Client
client = MemoryClient(region_name="us-west-2")

# 创建 STM (不配置策略)
stm = client.create_memory_and_wait(
    name="AgentCore_STM_Demo_abc123",
    strategies=[],  # 空列表 = 不配置提取策略
    description="Short-term memory demo - 仅存储原始对话",
    event_expiry_days=7  # 保存7天
)

print(f"STM 创建成功: {stm['id']}")
```

---

## 🛠️ 技术细节

### 后端实现 (agentcore_memory_api.py)

#### SSE事件格式
```python
def _send_event(self, event_type: str, data: Any) -> str:
    """格式化SSE事件"""
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, ensure_ascii=False)
    else:
        data_str = str(data)
    return f"event: {event_type}\ndata: {data_str}\n\n"
```

#### 事件类型

| 事件类型 | 说明 | 数据格式 |
|---------|------|---------|
| `log` | 日志输出 | 字符串 |
| `code` | 代码片段 | 字符串（Python代码） |
| `result` | 最终结果 | JSON对象 |

### 前端实现 (agentcore-memory.html)

#### EventSource监听
```javascript
const eventSource = new EventSource('/api/memory/create-stm-stream');

// 监听日志事件
eventSource.addEventListener('log', (event) => {
    const logContent = document.getElementById('logContent');
    logContent.textContent += event.data + '\n';
    // 自动滚动到底部
    logDisplay.scrollTop = logDisplay.scrollHeight;
});

// 监听代码事件
eventSource.addEventListener('code', (event) => {
    document.getElementById('codeContent').textContent = event.data;
    document.getElementById('codeDisplayArea').style.display = 'block';
});

// 监听结果事件
eventSource.addEventListener('result', (event) => {
    const result = JSON.parse(event.data);
    if (result.success) {
        // 自动填充Memory ID
        document.getElementById('stmMemoryId').value = result.memory_id;
    }
    eventSource.close();
});
```

---

## 🎨 UI特性

### 实时滚动
- ✅ 日志自动滚动到最新内容
- ✅ 类似终端的输出体验

### 自动填充
- ✅ Memory ID创建成功后自动填充到输入框
- ✅ 无需手动复制粘贴

### 加载状态
- ✅ 显示加载动画
- ✅ 禁用按钮防止重复点击
- ✅ 完成后自动恢复

---

## 🔧 API端点

### STM流式创建
```
GET /api/memory/create-stm-stream
```

**响应**: SSE流
- `event: log` - 日志行
- `event: code` - Python代码
- `event: result` - 最终结果JSON

### LTM流式创建
```
GET /api/memory/create-ltm-stream
```

**响应**: SSE流
- `event: log` - 日志行
- `event: code` - Python代码
- `event: result` - 最终结果JSON

---

## 📊 对比：旧版 vs 新版

| 特性 | 旧版 | 新版（流式） |
|------|------|-------------|
| 日志输出 | ❌ 全部完成后一次性显示 | ✅ 实时逐行显示 |
| 用户感知 | ❌ 等待无反馈 | ✅ 实时看到进度 |
| 代码显示 | ✅ 支持 | ✅ 支持 |
| Memory ID | ✅ 自动填充 | ✅ 自动填充 |
| 创建时间 | 10-30秒 | 10-30秒（体验更好） |

---

## 💡 为什么使用SSE而不是WebSocket？

### SSE的优势
- ✅ **单向通信**：服务器→客户端，符合日志输出场景
- ✅ **自动重连**：连接断开会自动重连
- ✅ **HTTP协议**：兼容性好，无需特殊配置
- ✅ **简单实现**：前端使用EventSource API，后端yield即可

### WebSocket vs SSE

| 特性 | WebSocket | SSE |
|------|----------|-----|
| 双向通信 | ✅ | ❌ |
| 协议 | WS/WSS | HTTP/HTTPS |
| 自动重连 | ❌ | ✅ |
| 事件类型 | ❌ | ✅ |
| 适用场景 | 聊天、游戏 | **日志、通知** |

---

## 🐛 故障排查

### 问题1: 日志不实时更新

**原因**: 浏览器缓存或代理缓存

**解决方案**:
- 刷新页面（Ctrl+F5）
- 检查HTTP响应头：
  ```
  Cache-Control: no-cache
  X-Accel-Buffering: no
  ```

### 问题2: 连接断开

**症状**: "连接错误，请重试"

**原因**:
- 网络问题
- 服务器重启
- 超时

**解决方案**:
- 检查FastAPI日志: `tail -f app.log`
- 重新点击创建按钮
- 确认服务正在运行: `lsof -i :8090`

### 问题3: Memory创建失败但无错误提示

**原因**: SSE事件未正确处理

**解决方案**:
- 打开浏览器控制台查看错误
- 检查EventSource状态
- 查看Network标签的EventStream请求

---

## 🎉 使用建议

1. **观察日志**: 创建Memory时注意观察日志输出，了解AWS API调用过程
2. **耐心等待**: 创建LTM需要配置策略，通常需要15-30秒，请耐心等待
3. **保存Memory ID**: 创建成功后，Memory ID会自动填充，也可以手动记录
4. **监控状态**: 可以通过日志判断创建进度，无需频繁刷新

---

**最后更新**: 2025-11-07
**版本**: 3.0.0 (支持流式响应)
