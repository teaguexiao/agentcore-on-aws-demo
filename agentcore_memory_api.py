"""
AgentCore Memory API - Backend module for Memory demonstrations

Provides API functions for demonstrating STM and LTM capabilities
"""

import os
import time
import boto3
import uuid
from datetime import datetime
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.session import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole, RetrievalConfig
from typing import Dict, Any, Optional, List, Generator
import json


class AgentCoreMemoryAPI:
    """Memory API handler"""

    def __init__(self, region_name: str = "us-west-2"):
        self.region_name = region_name
        self.memory_client = None
        self.bedrock_runtime = None
        self.stm_manager = None
        self.ltm_manager = None
        self.stm_memory_id = os.getenv('STM_MEMORY_ID')
        self.ltm_memory_id = os.getenv('LTM_MEMORY_ID')

    def initialize(self, stm_memory_id: str = None, ltm_memory_id: str = None) -> Dict[str, Any]:
        """Initialize Memory Managers"""
        try:
            # Use provided IDs or fallback to environment variables
            if stm_memory_id:
                self.stm_memory_id = stm_memory_id
            if ltm_memory_id:
                self.ltm_memory_id = ltm_memory_id

            if not self.stm_memory_id or not self.ltm_memory_id:
                return {
                    "success": False,
                    "message": "请先设置 STM_MEMORY_ID 和 LTM_MEMORY_ID 环境变量"
                }

            self.memory_client = MemoryClient(region_name=self.region_name)
            self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region_name)

            self.stm_manager = MemorySessionManager(
                memory_id=self.stm_memory_id,
                region_name=self.region_name
            )

            self.ltm_manager = MemorySessionManager(
                memory_id=self.ltm_memory_id,
                region_name=self.region_name
            )

            return {
                "success": True,
                "message": "初始化成功！可以开始演示了。",
                "stm_memory_id": self.stm_memory_id,
                "ltm_memory_id": self.ltm_memory_id
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"初始化失败: {str(e)}"
            }

    def initialize_stream(self, stm_memory_id: str = None, ltm_memory_id: str = None) -> Generator[str, None, None]:
        """Initialize Memory Managers (流式输出)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始初始化 Memory Managers")
            yield self._send_event("log", f"⏱️  开始时间: {datetime.now().strftime('%H:%M:%S')}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # Use provided IDs or fallback to environment variables
            if stm_memory_id:
                self.stm_memory_id = stm_memory_id
            if ltm_memory_id:
                self.ltm_memory_id = ltm_memory_id

            if not self.stm_memory_id or not self.ltm_memory_id:
                yield self._send_event("log", "❌ 请先设置 STM_MEMORY_ID 和 LTM_MEMORY_ID")
                yield self._send_event("result", {
                    "success": False,
                    "message": "请先设置 STM_MEMORY_ID 和 LTM_MEMORY_ID"
                })
                return

            yield self._send_event("log", f"📝 STM Memory ID: {self.stm_memory_id}")
            yield self._send_event("log", f"📝 LTM Memory ID: {self.ltm_memory_id}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # Initialize MemoryClient
            yield self._send_event("log", "🔧 初始化 MemoryClient...")
            time_module.sleep(0.1)
            self.memory_client = MemoryClient(region_name=self.region_name)
            yield self._send_event("log", f"✅ MemoryClient 初始化成功 (region: {self.region_name})")
            time_module.sleep(0.1)

            # Initialize Bedrock Runtime
            yield self._send_event("log", "🔧 初始化 Bedrock Runtime...")
            time_module.sleep(0.1)
            self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region_name)
            yield self._send_event("log", "✅ Bedrock Runtime 初始化成功")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # Initialize STM Manager
            yield self._send_event("log", "🔄 初始化 STM Manager...")
            time_module.sleep(0.1)
            self.stm_manager = MemorySessionManager(
                memory_id=self.stm_memory_id,
                region_name=self.region_name
            )
            yield self._send_event("log", f"✅ STM Manager 初始化成功")
            yield self._send_event("log", f"   - Memory ID: {self.stm_memory_id}")
            time_module.sleep(0.1)

            # Initialize LTM Manager
            yield self._send_event("log", "🔄 初始化 LTM Manager...")
            time_module.sleep(0.1)
            self.ltm_manager = MemorySessionManager(
                memory_id=self.ltm_memory_id,
                region_name=self.region_name
            )
            yield self._send_event("log", f"✅ LTM Manager 初始化成功")
            yield self._send_event("log", f"   - Memory ID: {self.ltm_memory_id}")
            time_module.sleep(0.1)

            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            yield self._send_event("log", "")
            yield self._send_event("log", "✨ Memory Managers 初始化完成，可以开始演示了！")

            yield self._send_event("result", {
                "success": True,
                "message": "初始化成功！可以开始演示了。",
                "stm_memory_id": self.stm_memory_id,
                "ltm_memory_id": self.ltm_memory_id,
                "elapsed_time": f"{total_elapsed:.2f}s"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"❌ 初始化失败: {str(e)}")
            yield self._send_event("log", f"⏱️  失败耗时: {elapsed:.2f}秒")
            yield self._send_event("result", {
                "success": False,
                "message": f"初始化失败: {str(e)}",
                "elapsed_time": f"{elapsed:.2f}s"
            })

    def call_llm(self, user_input: str, context: str = "") -> str:
        """调用 Bedrock Claude 模型"""
        try:
            system_prompt = "你是一个友好的 AI 助手，请用中文回答。"
            if context:
                system_prompt += f"\n\n相关记忆上下文:\n{context}"

            response = self.bedrock_runtime.converse(
                modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": user_input}]
                    }
                ],
                system=[{"text": system_prompt}],
                inferenceConfig={
                    "maxTokens": 2000,
                    "temperature": 0.7,
                }
            )

            return response['output']['message']['content'][0]['text']
        except Exception as e:
            return f"LLM 调用错误: {str(e)}"

    def call_llm_stream(self, user_input: str, context: str = "") -> Generator[str, None, None]:
        """调用 Bedrock Claude 模型 (流式响应) - 带重试机制"""
        import time as time_module

        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                system_prompt = "你是一个友好的 AI 助手，请用中文回答。"
                if context:
                    system_prompt += f"\n\n相关记忆上下文:\n{context}"

                response = self.bedrock_runtime.converse_stream(
                    modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                    messages=[
                        {
                            "role": "user",
                            "content": [{"text": user_input}]
                        }
                    ],
                    system=[{"text": system_prompt}],
                    inferenceConfig={
                        "maxTokens": 2000,
                        "temperature": 0.7,
                    }
                )

                # Stream the response
                for event in response['stream']:
                    if 'contentBlockDelta' in event:
                        delta = event['contentBlockDelta']['delta']
                        if 'text' in delta:
                            yield delta['text']

                # If we got here, the call was successful
                return

            except Exception as e:
                error_msg = str(e)

                # Check if it's a retryable error
                if attempt < max_retries - 1 and ('serviceUnavailableException' in error_msg or 'ThrottlingException' in error_msg):
                    yield f"\n⚠️  Bedrock 暂时不可用，{retry_delay}秒后重试 (尝试 {attempt + 1}/{max_retries})...\n"
                    time_module.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    # Final error or non-retryable error
                    yield f"\n❌ LLM 调用失败: {error_msg}\n"
                    return

    def demo_stm_step1(self, user_message: str, actor_id: str) -> Dict[str, Any]:
        """STM Demo - 步骤 1: 存储第一条消息"""
        try:
            if not self.stm_manager:
                return {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                }

            session_id = f"stm-{int(time.time())}"

            # 调用 LLM
            assistant_response = self.call_llm(user_message)

            # 存储到 STM
            self.stm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    ConversationalMessage(user_message, MessageRole.USER),
                    ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
                ]
            )

            return {
                "success": True,
                "session_id": session_id,
                "actor_id": actor_id,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "message": "已存储到 Short-term Memory"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"错误: {str(e)}"
            }

    def demo_stm_step2(self, user_message: str, session_id: str, actor_id: str) -> Dict[str, Any]:
        """STM Demo - 步骤 2: 基于历史对话回答"""
        try:
            if not self.stm_manager:
                return {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                }

            if not session_id or not actor_id:
                return {
                    "success": False,
                    "message": "请先执行步骤 1"
                }

            # 获取历史对话
            recent_turns = self.stm_manager.get_last_k_turns(
                actor_id=actor_id,
                session_id=session_id,
                k=5
            )

            # 构建上下文
            context_lines = []
            for turn in recent_turns:
                for msg in turn:
                    role = "用户" if msg.get('role') == MessageRole.USER.value else "助手"
                    text = msg.get('content', {}).get('text', '')
                    context_lines.append(f"{role}: {text}")

            context = "\n".join(context_lines)

            # 调用 LLM
            assistant_response = self.call_llm(user_message, context)

            # 存储新的对话
            self.stm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    ConversationalMessage(user_message, MessageRole.USER),
                    ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
                ]
            )

            return {
                "success": True,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "context": context,
                "message": "从 STM 检索历史并回答"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"错误: {str(e)}"
            }

    def demo_ltm_step1(self, user_preference: str, actor_id: str) -> Dict[str, Any]:
        """LTM Demo - 步骤 1: 表达偏好"""
        try:
            if not self.ltm_manager:
                return {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                }

            session_id = f"ltm-1-{int(time.time())}"

            # 调用 LLM
            assistant_response = self.call_llm(user_preference)

            # 存储到 LTM
            self.ltm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    ConversationalMessage(user_preference, MessageRole.USER),
                    ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
                ]
            )

            return {
                "success": True,
                "session_id": session_id,
                "actor_id": actor_id,
                "user_preference": user_preference,
                "assistant_response": assistant_response,
                "message": "已存储到 Long-term Memory，LTM 正在异步提取偏好信息（约需 10-15 秒）"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"错误: {str(e)}"
            }

    def demo_ltm_step2(self, user_question: str, actor_id: str) -> Dict[str, Any]:
        """LTM Demo - 步骤 2: 新会话中检索记忆"""
        try:
            if not self.ltm_manager:
                return {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                }

            if not actor_id:
                return {
                    "success": False,
                    "message": "请先执行步骤 1"
                }

            session_id = f"ltm-2-{int(time.time())}"

            # 从 LTM 检索相关记忆
            memories = self.ltm_manager.search_long_term_memories(
                query=user_question,
                namespace_prefix="/",
                top_k=5
            )

            # 构建上下文
            context_lines = []
            memory_list = []
            if memories:
                for i, memory in enumerate(memories, 1):
                    content = memory.get('content', {})
                    if isinstance(content, dict):
                        text = content.get('text', '')
                    else:
                        text = str(content)
                    relevance = memory.get('relevanceScore', 0.0)

                    context_lines.append(f"{i}. {text}")
                    memory_list.append({
                        "text": text,
                        "relevance": relevance
                    })

            context = "\n".join(context_lines) if context_lines else ""

            # 调用 LLM
            assistant_response = self.call_llm(user_question, context)

            # 存储新的对话
            self.ltm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    ConversationalMessage(user_question, MessageRole.USER),
                    ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
                ]
            )

            return {
                "success": True,
                "session_id": session_id,
                "user_question": user_question,
                "assistant_response": assistant_response,
                "memories": memory_list,
                "memory_count": len(memories),
                "message": f"从 LTM 检索到 {len(memories)} 条相关记忆"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"错误: {str(e)}"
            }

    def demo_combined(self, user_question: str, actor_id: str) -> Dict[str, Any]:
        """Combined Demo: STM + LTM"""
        try:
            if not self.stm_manager or not self.ltm_manager:
                return {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                }

            session_id = f"combined-{int(time.time())}"

            # 1. 从 LTM 获取长期记忆
            ltm_memories = self.ltm_manager.search_long_term_memories(
                query=user_question,
                namespace_prefix="/",
                top_k=3
            )

            # 2. 从 STM 获取会话历史 (如果有的话)
            stm_turns = []
            try:
                stm_turns = self.stm_manager.get_last_k_turns(
                    actor_id=actor_id,
                    session_id=session_id,
                    k=3
                )
            except:
                pass

            # 3. 构建综合上下文
            context_parts = []
            ltm_list = []
            stm_list = []

            if ltm_memories:
                ltm_lines = []
                for memory in ltm_memories:
                    content = memory.get('content', {})
                    if isinstance(content, dict):
                        text = content.get('text', '')
                    else:
                        text = str(content)
                    ltm_lines.append(f"- {text}")
                    ltm_list.append(text)

                if ltm_lines:
                    context_parts.append("长期记忆 (跨会话):\n" + "\n".join(ltm_lines))

            if stm_turns:
                stm_lines = []
                for turn in stm_turns:
                    for msg in turn:
                        role = "用户" if msg.get('role') == MessageRole.USER.value else "助手"
                        text = msg.get('content', {}).get('text', '')
                        stm_lines.append(f"{role}: {text}")
                        stm_list.append({"role": role, "text": text})

                if stm_lines:
                    context_parts.append("会话历史 (当前会话):\n" + "\n".join(stm_lines))

            context = "\n\n".join(context_parts)

            # 4. 调用 LLM
            assistant_response = self.call_llm(user_question, context)

            # 5. 同时存储到 STM 和 LTM
            messages = [
                ConversationalMessage(user_question, MessageRole.USER),
                ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
            ]

            self.stm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=messages
            )

            self.ltm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=messages
            )

            return {
                "success": True,
                "session_id": session_id,
                "user_question": user_question,
                "assistant_response": assistant_response,
                "ltm_memories": ltm_list,
                "stm_history": stm_list,
                "message": "综合使用 STM + LTM"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"错误: {str(e)}"
            }

    def demo_stm_step1_stream(self, user_message: str, actor_id: str) -> Generator[str, None, None]:
        """STM Demo - 步骤 1: 存储第一条消息 (流式输出)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始 STM Demo - 步骤 1: 存储第一条对话")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            if not self.stm_manager:
                yield self._send_event("log", "❌ 请先初始化 Memory Manager")
                yield self._send_event("result", {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                })
                return

            session_id = f"stm-{int(time.time())}"

            # 不再发送代码片段，页面已经有静态代码示例了
            # 直接开始执行步骤

            yield self._send_event("log", f"📝 用户消息: {user_message}")
            yield self._send_event("log", f"👤 Actor ID: {actor_id}")
            yield self._send_event("log", f"🔗 Session ID: {session_id}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 调用 LLM (流式响应)
            yield self._send_event("log", "🤖 调用 LLM 生成回复...")
            time_module.sleep(0.1)

            api_start = time_module.time()
            assistant_response = ""
            for chunk in self.call_llm_stream(user_message):
                assistant_response += chunk
                # Stream partial response to user
                yield self._send_event("log", f"💬 {chunk}")
            api_elapsed = time_module.time() - api_start

            yield self._send_event("log", "")
            yield self._send_event("log", f"✅ LLM 回复完成")
            yield self._send_event("log", f"   ⏱️  LLM 耗时: {api_elapsed:.2f}秒")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 存储到 STM
            yield self._send_event("log", "💾 存储对话到 STM...")
            time_module.sleep(0.1)

            self.stm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    ConversationalMessage(user_message, MessageRole.USER),
                    ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
                ]
            )

            yield self._send_event("log", "✅ 已存储到 Short-term Memory")
            yield self._send_event("log", f"📊 Session ID: {session_id}")
            time_module.sleep(0.05)

            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            yield self._send_event("log", "")
            yield self._send_event("log", "✨ 提示: 请继续执行步骤 2，询问相关问题测试 STM 的记忆能力")

            yield self._send_event("result", {
                "success": True,
                "session_id": session_id,
                "actor_id": actor_id,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": "已存储到 Short-term Memory"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"❌ 错误: {str(e)}")
            yield self._send_event("log", f"⏱️  失败耗时: {elapsed:.2f}秒")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"错误: {str(e)}"
            })

    def demo_stm_step2_stream(self, user_message: str, session_id: str, actor_id: str) -> Generator[str, None, None]:
        """STM Demo - 步骤 2: 基于历史对话回答 (流式输出)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始 STM Demo - 步骤 2: 基于历史对话回答")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            if not self.stm_manager:
                yield self._send_event("log", "❌ 请先初始化 Memory Manager")
                yield self._send_event("result", {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                })
                return

            if not session_id or not actor_id:
                yield self._send_event("log", "❌ 请先执行步骤 1")
                yield self._send_event("result", {
                    "success": False,
                    "message": "请先执行步骤 1"
                })
                return

            # 不再发送代码片段，页面已经有静态代码示例了
            # 直接开始执行步骤

            yield self._send_event("log", f"📝 用户问题: {user_message}")
            yield self._send_event("log", f"🔗 Session ID: {session_id}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 获取历史对话
            yield self._send_event("log", "🔍 从 STM 检索历史对话...")
            time_module.sleep(0.1)

            recent_turns = self.stm_manager.get_last_k_turns(
                actor_id=actor_id,
                session_id=session_id,
                k=5
            )

            # 构建上下文
            context_lines = []
            for turn in recent_turns:
                for msg in turn:
                    role = "用户" if msg.get('role') == MessageRole.USER.value else "助手"
                    text = msg.get('content', {}).get('text', '')
                    context_lines.append(f"{role}: {text}")

            context = "\n".join(context_lines)

            yield self._send_event("log", f"✅ 检索到 {len(recent_turns)} 轮历史对话")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 显示历史上下文
            yield self._send_event("log", "📜 历史对话上下文:")
            for line in context_lines[:6]:  # 只显示前6条
                yield self._send_event("log", f"   {line[:80]}...")
                time_module.sleep(0.05)
            if len(context_lines) > 6:
                yield self._send_event("log", f"   ... (还有 {len(context_lines)-6} 条)")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 调用 LLM (流式响应)
            yield self._send_event("log", "🤖 调用 LLM 生成回复 (基于历史上下文)...")
            time_module.sleep(0.1)

            api_start = time_module.time()
            assistant_response = ""
            for chunk in self.call_llm_stream(user_message, context):
                assistant_response += chunk
                yield self._send_event("log", f"💬 {chunk}")
            api_elapsed = time_module.time() - api_start

            yield self._send_event("log", "")
            yield self._send_event("log", f"✅ LLM 回复完成")
            yield self._send_event("log", f"   ⏱️  LLM 耗时: {api_elapsed:.2f}秒")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 存储新的对话
            yield self._send_event("log", "💾 存储新对话到 STM...")
            time_module.sleep(0.1)

            self.stm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    ConversationalMessage(user_message, MessageRole.USER),
                    ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
                ]
            )

            yield self._send_event("log", "✅ 已存储，对话历史已更新")
            time_module.sleep(0.05)

            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            yield self._send_event("log", "")
            yield self._send_event("log", "✨ 提示: 助手能够记住之前的对话内容，体现了 STM 的会话内记忆能力")

            yield self._send_event("result", {
                "success": True,
                "user_message": user_message,
                "assistant_response": assistant_response,
                "context": context,
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": "从 STM 检索历史并回答"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"❌ 错误: {str(e)}")
            yield self._send_event("log", f"⏱️  失败耗时: {elapsed:.2f}秒")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"错误: {str(e)}"
            })

    def demo_ltm_step1_stream(self, user_preference: str, actor_id: str) -> Generator[str, None, None]:
        """LTM Demo - 步骤 1: 表达偏好 (流式输出)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始 LTM Demo - 步骤 1: 表达偏好")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            if not self.ltm_manager:
                yield self._send_event("log", "❌ 请先初始化 Memory Manager")
                yield self._send_event("result", {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                })
                return

            session_id = f"ltm-1-{int(time.time())}"

            # 不再发送代码片段，页面已经有静态代码示例了
            # 直接开始执行步骤

            yield self._send_event("log", f"📝 用户偏好: {user_preference}")
            yield self._send_event("log", f"👤 Actor ID: {actor_id}")
            yield self._send_event("log", f"🔗 Session ID: {session_id}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 调用 LLM (流式响应)
            yield self._send_event("log", "🤖 调用 LLM 生成回复...")
            time_module.sleep(0.1)

            api_start = time_module.time()
            assistant_response = ""
            for chunk in self.call_llm_stream(user_preference):
                assistant_response += chunk
                yield self._send_event("log", f"💬 {chunk}")
            api_elapsed = time_module.time() - api_start

            yield self._send_event("log", "")
            yield self._send_event("log", f"✅ LLM 回复完成")
            yield self._send_event("log", f"   ⏱️  LLM 耗时: {api_elapsed:.2f}秒")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 存储到 LTM
            yield self._send_event("log", "💾 存储偏好到 LTM...")
            time_module.sleep(0.1)

            self.ltm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    ConversationalMessage(user_preference, MessageRole.USER),
                    ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
                ]
            )

            yield self._send_event("log", "✅ 已存储到 Long-term Memory")
            yield self._send_event("log", f"📊 Session ID: {session_id}")
            time_module.sleep(0.05)

            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", "⏳ LTM 正在异步提取偏好信息，通常需要 10-15 秒...")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            yield self._send_event("log", "")
            yield self._send_event("log", "✨ 提示: 请等待约 15 秒后再执行步骤 2，以便 LTM 完成异步处理")

            yield self._send_event("result", {
                "success": True,
                "session_id": session_id,
                "actor_id": actor_id,
                "user_preference": user_preference,
                "assistant_response": assistant_response,
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": "已存储到 Long-term Memory，LTM 正在异步提取偏好信息（约需 10-15 秒）"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"❌ 错误: {str(e)}")
            yield self._send_event("log", f"⏱️  失败耗时: {elapsed:.2f}秒")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"错误: {str(e)}"
            })

    def demo_ltm_step2_stream(self, user_question: str, actor_id: str) -> Generator[str, None, None]:
        """LTM Demo - 步骤 2: 新会话中检索记忆 (流式输出)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始 LTM Demo - 步骤 2: 新会话中检索记忆")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            if not self.ltm_manager:
                yield self._send_event("log", "❌ 请先初始化 Memory Manager")
                yield self._send_event("result", {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                })
                return

            if not actor_id:
                yield self._send_event("log", "❌ 请先执行步骤 1")
                yield self._send_event("result", {
                    "success": False,
                    "message": "请先执行步骤 1"
                })
                return

            session_id = f"ltm-2-{int(time.time())}"

            # 不再发送代码片段，页面已经有静态代码示例了
            # 直接开始执行步骤

            yield self._send_event("log", f"📝 用户问题: {user_question}")
            yield self._send_event("log", f"🔗 新 Session ID: {session_id}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 从 LTM 检索相关记忆
            yield self._send_event("log", "🔍 从 LTM 检索相关记忆...")
            time_module.sleep(0.1)

            memories = self.ltm_manager.search_long_term_memories(
                query=user_question,
                namespace_prefix="/",
                top_k=5
            )

            # 构建上下文
            context_lines = []
            memory_list = []
            if memories:
                for i, memory in enumerate(memories, 1):
                    content = memory.get('content', {})
                    if isinstance(content, dict):
                        text = content.get('text', '')
                    else:
                        text = str(content)
                    relevance = memory.get('relevanceScore', 0.0)

                    context_lines.append(f"{i}. {text}")
                    memory_list.append({
                        "text": text,
                        "relevance": relevance
                    })

            context = "\n".join(context_lines) if context_lines else ""

            yield self._send_event("log", f"✅ 检索到 {len(memories)} 条相关记忆")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 显示记忆内容
            if memories:
                yield self._send_event("log", "📜 检索到的长期记忆:")
                for i, mem in enumerate(memory_list[:3], 1):
                    yield self._send_event("log", f"  {i}. {mem['text'][:60]}... (相关性: {mem['relevance']:.2f})")
                    time_module.sleep(0.05)
                if len(memory_list) > 3:
                    yield self._send_event("log", f"  ... (还有 {len(memory_list)-3} 条)")
                yield self._send_event("log", "")
                time_module.sleep(0.1)

            # 调用 LLM (流式响应)
            yield self._send_event("log", "🤖 调用 LLM 生成回复 (基于长期记忆)...")
            time_module.sleep(0.1)

            api_start = time_module.time()
            assistant_response = ""
            for chunk in self.call_llm_stream(user_question, context):
                assistant_response += chunk
                yield self._send_event("log", f"💬 {chunk}")
            api_elapsed = time_module.time() - api_start

            yield self._send_event("log", "")
            yield self._send_event("log", f"✅ LLM 回复完成")
            yield self._send_event("log", f"   ⏱️  LLM 耗时: {api_elapsed:.2f}秒")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 存储新的对话
            yield self._send_event("log", "💾 存储新对话到 LTM...")
            time_module.sleep(0.1)

            self.ltm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    ConversationalMessage(user_question, MessageRole.USER),
                    ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
                ]
            )

            yield self._send_event("log", "✅ 已存储，跨会话记忆功能展示完成")
            time_module.sleep(0.05)

            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            yield self._send_event("log", "")
            yield self._send_event("log", "✨ 提示: 即使在新会话中，助手仍能记住之前表达的偏好，这就是 LTM 的跨会话记忆能力")

            yield self._send_event("result", {
                "success": True,
                "session_id": session_id,
                "user_question": user_question,
                "assistant_response": assistant_response,
                "memories": memory_list,
                "memory_count": len(memories),
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": f"从 LTM 检索到 {len(memories)} 条相关记忆"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"❌ 错误: {str(e)}")
            yield self._send_event("log", f"⏱️  失败耗时: {elapsed:.2f}秒")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"错误: {str(e)}"
            })

    def demo_combined_stream(self, user_question: str, actor_id: str) -> Generator[str, None, None]:
        """Combined Demo: STM + LTM (流式输出)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始 Combined Demo: STM + LTM 综合演示")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            if not self.stm_manager or not self.ltm_manager:
                yield self._send_event("log", "❌ 请先初始化 Memory Manager")
                yield self._send_event("result", {
                    "success": False,
                    "message": "请先初始化 Memory Manager"
                })
                return

            session_id = f"combined-{int(time.time())}"

            # 不再发送代码片段，页面已经有静态代码示例了
            # 直接开始执行步骤

            yield self._send_event("log", f"📝 用户问题: {user_question}")
            yield self._send_event("log", f"🔗 Session ID: {session_id}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 1. 从 LTM 获取长期记忆
            yield self._send_event("log", "🔍 从 LTM 检索长期记忆...")
            time_module.sleep(0.1)

            ltm_memories = self.ltm_manager.search_long_term_memories(
                query=user_question,
                namespace_prefix="/",
                top_k=3
            )

            yield self._send_event("log", f"✅ 检索到 {len(ltm_memories)} 条长期记忆")
            time_module.sleep(0.05)

            # 2. 从 STM 获取会话历史
            yield self._send_event("log", "🔍 从 STM 检索会话历史...")
            time_module.sleep(0.1)

            stm_turns = []
            try:
                stm_turns = self.stm_manager.get_last_k_turns(
                    actor_id=actor_id,
                    session_id=session_id,
                    k=3
                )
                yield self._send_event("log", f"✅ 检索到 {len(stm_turns)} 轮会话历史")
            except:
                yield self._send_event("log", "⚠️  当前会话暂无历史记录")

            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 3. 构建综合上下文
            yield self._send_event("log", "🔧 构建综合上下文...")
            time_module.sleep(0.1)

            context_parts = []
            ltm_list = []
            stm_list = []

            if ltm_memories:
                ltm_lines = []
                for memory in ltm_memories:
                    content = memory.get('content', {})
                    if isinstance(content, dict):
                        text = content.get('text', '')
                    else:
                        text = str(content)
                    ltm_lines.append(f"- {text}")
                    ltm_list.append(text)

                if ltm_lines:
                    context_parts.append("长期记忆 (跨会话):\n" + "\n".join(ltm_lines))

            if stm_turns:
                stm_lines = []
                for turn in stm_turns:
                    for msg in turn:
                        role = "用户" if msg.get('role') == MessageRole.USER.value else "助手"
                        text = msg.get('content', {}).get('text', '')
                        stm_lines.append(f"{role}: {text}")
                        stm_list.append({"role": role, "text": text})

                if stm_lines:
                    context_parts.append("会话历史 (当前会话):\n" + "\n".join(stm_lines))

            context = "\n\n".join(context_parts)

            yield self._send_event("log", "✅ 综合上下文构建完成")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 4. 调用 LLM (流式响应)
            yield self._send_event("log", "🤖 调用 LLM 生成回复 (基于综合记忆)...")
            time_module.sleep(0.1)

            api_start = time_module.time()
            assistant_response = ""
            for chunk in self.call_llm_stream(user_question, context):
                assistant_response += chunk
                yield self._send_event("log", f"💬 {chunk}")
            api_elapsed = time_module.time() - api_start

            yield self._send_event("log", "")
            yield self._send_event("log", f"✅ LLM 回复完成")
            yield self._send_event("log", f"   ⏱️  LLM 耗时: {api_elapsed:.2f}秒")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            # 5. 同时存储到 STM 和 LTM
            yield self._send_event("log", "💾 存储对话到 STM 和 LTM...")
            time_module.sleep(0.1)

            messages = [
                ConversationalMessage(user_question, MessageRole.USER),
                ConversationalMessage(assistant_response, MessageRole.ASSISTANT)
            ]

            self.stm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=messages
            )

            self.ltm_manager.add_turns(
                actor_id=actor_id,
                session_id=session_id,
                messages=messages
            )

            yield self._send_event("log", "✅ 已同时存储到 STM 和 LTM")
            time_module.sleep(0.05)

            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            yield self._send_event("log", "")
            yield self._send_event("log", "✨ 综合演示完成: 利用了短期记忆和长期记忆的优势")

            yield self._send_event("result", {
                "success": True,
                "session_id": session_id,
                "user_question": user_question,
                "assistant_response": assistant_response,
                "ltm_memories": ltm_list,
                "stm_history": stm_list,
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": "综合使用 STM + LTM"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"❌ 错误: {str(e)}")
            yield self._send_event("log", f"⏱️  失败耗时: {elapsed:.2f}秒")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"错误: {str(e)}"
            })

    def create_stm_memory_stream(self, name: str = None) -> Generator[str, None, None]:
        """创建 Short-Term Memory (流式输出)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始创建 Short-Term Memory (STM)")
            yield self._send_event("log", f"⏱️  开始时间: {datetime.now().strftime('%H:%M:%S')}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)  # 确保流式输出

            if not self.memory_client:
                yield self._send_event("log", "📡 初始化 MemoryClient...")
                time_module.sleep(0.1)
                self.memory_client = MemoryClient(region_name=self.region_name)
                elapsed = time_module.time() - start_time
                yield self._send_event("log", f"✅ MemoryClient 初始化成功 (region: {self.region_name}) [{elapsed:.2f}s]")
                time_module.sleep(0.1)

            if not name:
                name = f"AgentCore_STM_Demo_{uuid.uuid4().hex[:8]}"
                elapsed = time_module.time() - start_time
                yield self._send_event("log", f"📝 生成 Memory 名称: {name} [{elapsed:.2f}s]")
                time_module.sleep(0.1)

            # 构建代码片段
            code_snippet = f'''import time
from datetime import datetime
from bedrock_agentcore.memory import MemoryClient

print("🚀 开始创建 Short-Term Memory (STM)")
print(f"⏱️  开始时间: {{datetime.now().strftime('%H:%M:%S')}}")
print()

start_time = time.time()

# 初始化 Memory Client
print("📡 初始化 MemoryClient...")
client = MemoryClient(region_name="{self.region_name}")
elapsed = time.time() - start_time
print(f"✅ MemoryClient 初始化成功 (region: {self.region_name}) [{{elapsed:.2f}}s]")

# 生成 Memory 名称
print(f"📝 生成 Memory 名称: {name}")
print()

# 创建 STM (不配置策略)
print("⏳ 调用 AWS Bedrock AgentCore API 创建 Memory...")
print(f"   - 名称: {name}")
print("   - 策略: 无 (STM 不需要提取策略)")
print("   - 事件保留期: 7 天")
print()

elapsed = time.time() - start_time
print(f"⏳ 正在创建，请稍候... [{{elapsed:.2f}}s]")

api_start = time.time()
stm = client.create_memory_and_wait(
    name="{name}",
    strategies=[],  # 空列表 = 不配置提取策略
    description="Short-term memory demo - 仅存储原始对话",
    event_expiry_days=7  # 保存7天
)
api_elapsed = time.time() - api_start

print()
print("✅ STM 创建成功!")
print(f"   - Memory ID: {{stm['id']}}")
print(f"   - 状态: {{stm.get('status', 'ACTIVE')}}")
print(f"   - 创建时间: {{stm.get('createdAt', 'N/A')}}")
print(f"   - API 耗时: {{api_elapsed:.2f}}秒")

total_elapsed = time.time() - start_time
print()
print(f"⏱️  总耗时: {{total_elapsed:.2f}}秒")
print()
print("💡 提示: STM 适用于会话内的短期记忆，即时存储，无需等待")'''

            yield self._send_event("code", code_snippet)
            time_module.sleep(0.1)

            yield self._send_event("log", "")
            yield self._send_event("log", "⏳ 调用 AWS Bedrock AgentCore API 创建 Memory...")
            time_module.sleep(0.1)
            yield self._send_event("log", f"   - 名称: {name}")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - 策略: 无 (STM 不需要提取策略)")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - 事件保留期: 7 天")
            time_module.sleep(0.05)
            yield self._send_event("log", "")

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"⏳ 正在创建，请稍候... [{elapsed:.2f}s]")
            time_module.sleep(0.1)

            # 创建不带策略的 Memory
            api_start = time_module.time()
            stm = self.memory_client.create_memory_and_wait(
                name=name,
                strategies=[],
                description="Short-term memory demo - 仅存储原始对话",
                event_expiry_days=7
            )
            api_elapsed = time_module.time() - api_start

            yield self._send_event("log", "")
            time_module.sleep(0.1)
            yield self._send_event("log", f"✅ STM 创建成功!")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - Memory ID: {stm['id']}")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - 状态: {stm.get('status', 'ACTIVE')}")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - 创建时间: {stm.get('createdAt', 'N/A')}")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - API 耗时: {api_elapsed:.2f}秒")
            time_module.sleep(0.05)

            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            time_module.sleep(0.05)
            yield self._send_event("log", "")
            yield self._send_event("log", "💡 提示: STM 适用于会话内的短期记忆，即时存储，无需等待")

            yield self._send_event("result", {
                "success": True,
                "memory_id": stm['id'],
                "name": stm['name'],
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": f"STM 创建成功: {stm['id']}"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"")
            yield self._send_event("log", f"❌ STM 创建失败: {str(e)}")
            yield self._send_event("log", f"⏱️  失败耗时: {elapsed:.2f}秒")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"STM 创建失败: {str(e)}"
            })

    def create_ltm_memory_stream(self, name: str = None) -> Generator[str, None, None]:
        """创建 Long-Term Memory (流式输出)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始创建 Long-Term Memory (LTM)")
            yield self._send_event("log", f"⏱️  开始时间: {datetime.now().strftime('%H:%M:%S')}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            if not self.memory_client:
                yield self._send_event("log", "📡 初始化 MemoryClient...")
                time_module.sleep(0.1)
                self.memory_client = MemoryClient(region_name=self.region_name)
                elapsed = time_module.time() - start_time
                yield self._send_event("log", f"✅ MemoryClient 初始化成功 (region: {self.region_name}) [{elapsed:.2f}s]")
                time_module.sleep(0.1)

            if not name:
                name = f"AgentCore_LTM_Demo_{uuid.uuid4().hex[:8]}"
                elapsed = time_module.time() - start_time
                yield self._send_event("log", f"📝 生成 Memory 名称: {name} [{elapsed:.2f}s]")
                time_module.sleep(0.1)

            # 构建代码片段
            code_snippet = f'''import time
from datetime import datetime
from bedrock_agentcore.memory import MemoryClient

print("🚀 开始创建 Long-Term Memory (LTM)")
print(f"⏱️  开始时间: {{datetime.now().strftime('%H:%M:%S')}}")
print()

start_time = time.time()

# 初始化 Memory Client
print("📡 初始化 MemoryClient...")
client = MemoryClient(region_name="{self.region_name}")
elapsed = time.time() - start_time
print(f"✅ MemoryClient 初始化成功 (region: {self.region_name}) [{{elapsed:.2f}}s]")

# 生成 Memory 名称
print(f"📝 生成 Memory 名称: {name}")
print()

# 创建 LTM (配置语义和偏好策略)
print("⏳ 调用 AWS Bedrock AgentCore API 创建 Memory...")
print(f"   - 名称: {name}")
print("   - 策略: 2 个 (语义记忆 + 用户偏好)")
print("   - 事件保留期: 30 天")
print()
print("⚙️ 配置策略 1: Semantic Memory Strategy")
print("   - 自动提取重要事实和信息")
print("   - 使用 LLM 进行语义分析")
print()
print("⚙️ 配置策略 2: User Preference Memory Strategy")
print("   - 自动提取用户偏好")
print("   - 支持跨会话记忆")
print()

elapsed = time.time() - start_time
print(f"⏳ 正在创建并配置策略，请稍候... [{{elapsed:.2f}}s]")

api_start = time.time()
ltm = client.create_memory_and_wait(
    name="{name}",
    strategies=[
        # 语义记忆策略: 提取重要的事实和信息
        {{
            "semanticMemoryStrategy": {{
                "name": "semantic_facts",
                "description": "提取用户提到的重要事实和信息",
                "namespaces": ["/strategies/{{memoryStrategyId}}/actors/{{actorId}}"]
            }}
        }},
        # 用户偏好策略: 提取用户的喜好和偏好
        {{
            "userPreferenceMemoryStrategy": {{
                "name": "user_preferences",
                "description": "提取用户的偏好、喜好和习惯",
                "namespaces": ["/strategies/{{memoryStrategyId}}/actors/{{actorId}}"]
            }}
        }}
    ],
    description="Long-term memory demo - 智能提取和跨会话记忆",
    event_expiry_days=30  # 保存30天
)
api_elapsed = time.time() - api_start

print()
print("✅ LTM 创建成功!")
print(f"   - Memory ID: {{ltm['id']}}")
print(f"   - 状态: {{ltm.get('status', 'ACTIVE')}}")
print(f"   - 创建时间: {{ltm.get('createdAt', 'N/A')}}")
print(f"   - 策略: (查看详细信息)")
print(f"   - API 耗时: {{api_elapsed:.2f}}秒")

total_elapsed = time.time() - start_time
print()
print(f"⏱️  总耗时: {{total_elapsed:.2f}}秒")
print()
print("💡 提示: LTM 会异步提取记忆，通常需要 10-15 秒完成")'''

            yield self._send_event("code", code_snippet)
            time_module.sleep(0.1)

            yield self._send_event("log", "")
            yield self._send_event("log", "⏳ 调用 AWS Bedrock AgentCore API 创建 Memory...")
            time_module.sleep(0.1)
            yield self._send_event("log", f"   - 名称: {name}")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - 策略: 2 个 (语义记忆 + 用户偏好)")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - 事件保留期: 30 天")
            time_module.sleep(0.05)
            yield self._send_event("log", "")
            yield self._send_event("log", "⚙️ 配置策略 1: Semantic Memory Strategy")
            time_module.sleep(0.05)
            yield self._send_event("log", "   - 自动提取重要事实和信息")
            time_module.sleep(0.05)
            yield self._send_event("log", "   - 使用 LLM 进行语义分析")
            time_module.sleep(0.05)
            yield self._send_event("log", "")
            yield self._send_event("log", "⚙️ 配置策略 2: User Preference Memory Strategy")
            time_module.sleep(0.05)
            yield self._send_event("log", "   - 自动提取用户偏好")
            time_module.sleep(0.05)
            yield self._send_event("log", "   - 支持跨会话记忆")
            time_module.sleep(0.05)
            yield self._send_event("log", "")

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"⏳ 正在创建并配置策略，请稍候... [{elapsed:.2f}s]")
            time_module.sleep(0.1)

            # 创建带策略的 Memory
            api_start = time_module.time()
            ltm = self.memory_client.create_memory_and_wait(
                name=name,
                strategies=[
                    {
                        "semanticMemoryStrategy": {
                            "name": "semantic_facts",
                            "description": "提取用户提到的重要事实和信息",
                            "namespaces": ["/strategies/{memoryStrategyId}/actors/{actorId}"]
                        }
                    },
                    {
                        "userPreferenceMemoryStrategy": {
                            "name": "user_preferences",
                            "description": "提取用户的偏好、喜好和习惯",
                            "namespaces": ["/strategies/{memoryStrategyId}/actors/{actorId}"]
                        }
                    }
                ],
                description="Long-term memory demo - 智能提取和跨会话记忆",
                event_expiry_days=30
            )
            api_elapsed = time_module.time() - api_start

            yield self._send_event("log", "")
            time_module.sleep(0.1)
            yield self._send_event("log", f"✅ LTM 创建成功!")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - Memory ID: {ltm['id']}")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - 状态: {ltm.get('status', 'ACTIVE')}")
            time_module.sleep(0.05)
            yield self._send_event("log", f"   - 创建时间: {ltm.get('createdAt', 'N/A')}")
            time_module.sleep(0.05)

            # 提取策略信息
            strategies = []
            for strategy in ltm.get('strategies', []):
                strategy_info = {
                    "name": strategy.get('name', 'N/A'),
                    "type": strategy.get('type', 'N/A'),
                    "strategy_id": strategy.get('strategyId', 'N/A')
                }
                strategies.append(strategy_info)
                yield self._send_event("log", f"   - 策略: {strategy_info['name']} ({strategy_info['type']})")
                time_module.sleep(0.05)

            yield self._send_event("log", f"   - API 耗时: {api_elapsed:.2f}秒")
            time_module.sleep(0.05)

            total_elapsed = time_module.time() - start_time
            yield self._send_event("log", "")
            yield self._send_event("log", f"⏱️  总耗时: {total_elapsed:.2f}秒")
            time_module.sleep(0.05)
            yield self._send_event("log", "")
            yield self._send_event("log", "💡 提示: LTM 会异步提取记忆，通常需要 10-15 秒完成")

            yield self._send_event("result", {
                "success": True,
                "memory_id": ltm['id'],
                "name": ltm['name'],
                "strategies": strategies,
                "elapsed_time": f"{total_elapsed:.2f}s",
                "message": f"LTM 创建成功: {ltm['id']}"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"")
            yield self._send_event("log", f"❌ LTM 创建失败: {str(e)}")
            yield self._send_event("log", f"⏱️  失败耗时: {elapsed:.2f}秒")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"LTM 创建失败: {str(e)}"
            })

    def _send_event(self, event_type: str, data: Any) -> str:
        """格式化SSE事件"""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, ensure_ascii=False)
        else:
            data_str = str(data)

        # SSE协议：多行数据时，每行都需要 "data: " 前缀
        lines = data_str.split('\n')
        data_lines = '\n'.join(f"data: {line}" for line in lines)

        return f"event: {event_type}\n{data_lines}\n\n"

    def create_stm_memory(self, name: str = None) -> Dict[str, Any]:
        """创建 Short-Term Memory (不配置策略)"""
        logs = []
        code_snippet = ""

        try:
            logs.append("🚀 开始创建 Short-Term Memory (STM)")

            if not self.memory_client:
                logs.append("📡 初始化 MemoryClient...")
                self.memory_client = MemoryClient(region_name=self.region_name)
                logs.append(f"✅ MemoryClient 初始化成功 (region: {self.region_name})")

            if not name:
                name = f"AgentCore_STM_Demo_{uuid.uuid4().hex[:8]}"
                logs.append(f"📝 生成 Memory 名称: {name}")

            # 构建代码片段
            code_snippet = f'''from bedrock_agentcore.memory import MemoryClient

# 初始化 Memory Client
client = MemoryClient(region_name="{self.region_name}")

# 创建 STM (不配置策略)
stm = client.create_memory_and_wait(
    name="{name}",
    strategies=[],  # 空列表 = 不配置提取策略
    description="Short-term memory demo - 仅存储原始对话",
    event_expiry_days=7  # 保存7天
)

print(f"STM 创建成功: {{stm['id']}}")'''

            logs.append("⏳ 调用 AWS Bedrock AgentCore API 创建 Memory...")
            logs.append(f"   - 名称: {name}")
            logs.append(f"   - 策略: 无 (STM 不需要提取策略)")
            logs.append(f"   - 事件保留期: 7 天")

            # 创建不带策略的 Memory
            stm = self.memory_client.create_memory_and_wait(
                name=name,
                strategies=[],  # 空列表 = 不配置提取策略
                description="Short-term memory demo - 仅存储原始对话",
                event_expiry_days=7  # 保存7天
            )

            logs.append(f"✅ STM 创建成功!")
            logs.append(f"   - Memory ID: {stm['id']}")
            logs.append(f"   - 状态: {stm.get('status', 'ACTIVE')}")
            logs.append(f"   - 创建时间: {stm.get('createdAt', 'N/A')}")
            logs.append("")
            logs.append("💡 提示: STM 适用于会话内的短期记忆，即时存储，无需等待")

            return {
                "success": True,
                "memory_id": stm['id'],
                "name": stm['name'],
                "code": code_snippet,
                "logs": logs,
                "message": f"STM 创建成功: {stm['id']}"
            }

        except Exception as e:
            logs.append(f"❌ STM 创建失败: {str(e)}")
            return {
                "success": False,
                "message": f"STM 创建失败: {str(e)}",
                "code": code_snippet,
                "logs": logs
            }

    def create_ltm_memory(self, name: str = None) -> Dict[str, Any]:
        """创建 Long-Term Memory (配置语义和偏好策略)"""
        logs = []
        code_snippet = ""

        try:
            logs.append("🚀 开始创建 Long-Term Memory (LTM)")

            if not self.memory_client:
                logs.append("📡 初始化 MemoryClient...")
                self.memory_client = MemoryClient(region_name=self.region_name)
                logs.append(f"✅ MemoryClient 初始化成功 (region: {self.region_name})")

            if not name:
                name = f"AgentCore_LTM_Demo_{uuid.uuid4().hex[:8]}"
                logs.append(f"📝 生成 Memory 名称: {name}")

            # 构建代码片段
            code_snippet = f'''from bedrock_agentcore.memory import MemoryClient

# 初始化 Memory Client
client = MemoryClient(region_name="{self.region_name}")

# 创建 LTM (配置语义和偏好策略)
ltm = client.create_memory_and_wait(
    name="{name}",
    strategies=[
        # 语义记忆策略: 提取重要的事实和信息
        {{
            "semanticMemoryStrategy": {{
                "name": "semantic_facts",
                "description": "提取用户提到的重要事实和信息",
                "namespaces": ["/strategies/{{memoryStrategyId}}/actors/{{actorId}}"]
            }}
        }},
        # 用户偏好策略: 提取用户的喜好和偏好
        {{
            "userPreferenceMemoryStrategy": {{
                "name": "user_preferences",
                "description": "提取用户的偏好、喜好和习惯",
                "namespaces": ["/strategies/{{memoryStrategyId}}/actors/{{actorId}}"]
            }}
        }}
    ],
    description="Long-term memory demo - 智能提取和跨会话记忆",
    event_expiry_days=30  # 保存30天
)

print(f"LTM 创建成功: {{ltm['id']}}")'''

            logs.append("⏳ 调用 AWS Bedrock AgentCore API 创建 Memory...")
            logs.append(f"   - 名称: {name}")
            logs.append(f"   - 策略: 2 个 (语义记忆 + 用户偏好)")
            logs.append(f"   - 事件保留期: 30 天")
            logs.append("")
            logs.append("⚙️ 配置策略 1: Semantic Memory Strategy")
            logs.append("   - 自动提取重要事实和信息")
            logs.append("   - 使用 LLM 进行语义分析")
            logs.append("")
            logs.append("⚙️ 配置策略 2: User Preference Memory Strategy")
            logs.append("   - 自动提取用户偏好")
            logs.append("   - 支持跨会话记忆")

            # 创建带策略的 Memory
            ltm = self.memory_client.create_memory_and_wait(
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

            logs.append("")
            logs.append(f"✅ LTM 创建成功!")
            logs.append(f"   - Memory ID: {ltm['id']}")
            logs.append(f"   - 状态: {ltm.get('status', 'ACTIVE')}")
            logs.append(f"   - 创建时间: {ltm.get('createdAt', 'N/A')}")

            # 提取策略信息
            strategies = []
            for strategy in ltm.get('strategies', []):
                strategy_info = {
                    "name": strategy.get('name', 'N/A'),
                    "type": strategy.get('type', 'N/A'),
                    "strategy_id": strategy.get('strategyId', 'N/A')
                }
                strategies.append(strategy_info)
                logs.append(f"   - 策略: {strategy_info['name']} ({strategy_info['type']})")

            logs.append("")
            logs.append("💡 提示: LTM 会异步提取记忆，通常需要 10-15 秒完成")

            return {
                "success": True,
                "memory_id": ltm['id'],
                "name": ltm['name'],
                "strategies": strategies,
                "code": code_snippet,
                "logs": logs,
                "message": f"LTM 创建成功: {ltm['id']}"
            }

        except Exception as e:
            logs.append(f"❌ LTM 创建失败: {str(e)}")
            return {
                "success": False,
                "message": f"LTM 创建失败: {str(e)}",
                "code": code_snippet,
                "logs": logs
            }

    def list_memories(self) -> Dict[str, Any]:
        """列出所有 Memory 资源"""
        try:
            if not self.memory_client:
                self.memory_client = MemoryClient(region_name=self.region_name)

            memories = self.memory_client.list_memories(max_results=100)

            memory_list = []
            for memory in memories:
                memory_info = {
                    "memory_id": memory.get('id', memory.get('memoryId', 'N/A')),
                    "name": memory.get('name', 'N/A'),
                    "status": memory.get('status', 'N/A'),
                    "created_at": memory.get('createdAt', 'N/A'),
                    "has_strategies": len(memory.get('strategies', [])) > 0,
                    "strategy_count": len(memory.get('strategies', []))
                }
                memory_list.append(memory_info)

            return {
                "success": True,
                "memories": memory_list,
                "count": len(memory_list),
                "message": f"找到 {len(memory_list)} 个 Memory 资源"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"列出 Memory 失败: {str(e)}"
            }

    def list_stm_events(self, actor_id: str, session_id: str = None, max_results: int = 10) -> Dict[str, Any]:
        """列出 STM 事件（对话记录）"""
        try:
            if not self.stm_manager:
                return {
                    "success": False,
                    "message": "请先初始化 STM Manager"
                }

            if session_id:
                # 获取特定会话的事件
                events = self.stm_manager.list_events(
                    actor_id=actor_id,
                    session_id=session_id,
                    max_results=max_results
                )
            else:
                # 获取用户的所有会话
                sessions = self.stm_manager.list_actor_sessions(
                    actor_id=actor_id,
                    max_results=10
                )
                events = []
                for session in sessions[:3]:  # 只获取前3个会话的事件
                    session_events = self.stm_manager.list_events(
                        actor_id=actor_id,
                        session_id=session['sessionId'],
                        max_results=5
                    )
                    events.extend(session_events)

            event_list = []
            for event in events:
                event_info = {
                    "event_id": event.get('eventId', 'N/A'),
                    "session_id": event.get('sessionId', 'N/A'),
                    "timestamp": event.get('eventTimestamp', 'N/A'),
                    "payload_count": len(event.get('payload', []))
                }

                # 提取对话内容
                messages = []
                for item in event.get('payload', []):
                    if 'conversational' in item:
                        conv = item['conversational']
                        messages.append({
                            "role": conv.get('role', 'N/A'),
                            "text": conv.get('content', {}).get('text', 'N/A')[:100]  # 只显示前100字符
                        })

                event_info["messages"] = messages
                event_list.append(event_info)

            return {
                "success": True,
                "events": event_list,
                "count": len(event_list),
                "message": f"找到 {len(event_list)} 条 STM 事件"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"列出 STM 事件失败: {str(e)}"
            }

    def list_ltm_records(self, actor_id: str = None, max_results: int = 10) -> Dict[str, Any]:
        """列出 LTM 记录（提取的记忆）"""
        try:
            if not self.ltm_manager:
                return {
                    "success": False,
                    "message": "请先初始化 LTM Manager"
                }

            # 构建命名空间前缀
            if actor_id:
                namespace_prefix = f"/strategies/{{memoryStrategyId}}/actors/{actor_id}"
            else:
                namespace_prefix = "/"

            # 列出记忆记录
            records = self.ltm_manager.list_long_term_memory_records(
                namespace_prefix=namespace_prefix,
                max_results=max_results
            )

            record_list = []
            for record in records:
                record_info = {
                    "record_id": record.get('memoryRecordId', 'N/A'),
                    "namespace": record.get('namespace', 'N/A'),
                    "created_at": record.get('createdAt', 'N/A'),
                }

                # 提取内容
                content = record.get('content', {})
                if isinstance(content, dict):
                    text = content.get('text', 'N/A')
                else:
                    text = str(content)

                record_info["content"] = text[:200]  # 只显示前200字符
                record_info["content_full"] = text  # 完整内容

                record_list.append(record_info)

            return {
                "success": True,
                "records": record_list,
                "count": len(record_list),
                "message": f"找到 {len(record_list)} 条 LTM 记录"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"列出 LTM 记录失败: {str(e)}"
            }

    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """删除 Memory 资源"""
        try:
            if not self.memory_client:
                self.memory_client = MemoryClient(region_name=self.region_name)

            self.memory_client.delete_memory(memory_id)

            return {
                "success": True,
                "message": f"Memory {memory_id} 删除成功"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"删除 Memory 失败: {str(e)}"
            }


# Global instance
memory_api = AgentCoreMemoryAPI()
