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

    def __init__(self, region_name: str = "us-east-2"):
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

    def initialize_stream_unified(self, memory_id: str) -> Generator[str, None, None]:
        """Initialize unified Memory Manager with both STM and LTM (流式输出)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始初始化 Memory Manager（统一实例，包含 STM 和 LTM）")
            yield self._send_event("log", f"⏱️  开始时间: {datetime.now().strftime('%H:%M:%S')}")
            yield self._send_event("log", "")
            time_module.sleep(0.1)

            yield self._send_event("log", f"📡 初始化 MemoryClient...")
            time_module.sleep(0.1)
            if not self.memory_client:
                self.memory_client = MemoryClient(region_name=self.region_name)
            if not self.bedrock_runtime:
                import boto3
                self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region_name)
            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ MemoryClient 初始化成功 [{elapsed:.2f}s]")
            time_module.sleep(0.1)

            yield self._send_event("log", f"📦 创建 MemorySessionManager (Memory ID: {memory_id[:20]}...)")
            time_module.sleep(0.1)
            manager = MemorySessionManager(
                memory_id=memory_id,
                region_name=self.region_name
            )

            # 保存到实例变量，供demo函数使用
            # 由于是统一的Memory实例，STM和LTM使用同一个manager
            self.stm_manager = manager
            self.ltm_manager = manager

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ Memory Manager 创建成功 [{elapsed:.2f}s]")
            time_module.sleep(0.1)

            yield self._send_event("log", "")
            yield self._send_event("log", "💡 说明:")
            yield self._send_event("log", "   - 该 Memory 实例包含:")
            yield self._send_event("log", "     • STM: 原始对话事件（即时存储和检索）")
            yield self._send_event("log", "     • LTM: 提取的语义记忆（5-15秒后异步生成）")
            yield self._send_event("log", "   - 使用同一个 manager 实例同时访问 STM 和 LTM")
            time_module.sleep(0.1)

            elapsed = time_module.time() - start_time
            yield self._send_event("result", {
                "success": True,
                "memory_id": memory_id,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"✅ Memory Manager 初始化成功 (用时 {elapsed:.2f}s)"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"❌ 初始化失败: {str(e)} [{elapsed:.2f}s]")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"初始化失败: {str(e)}"
            })

    def initialize_stream(self, stm_memory_id: str = None, ltm_memory_id: str = None) -> Generator[str, None, None]:
        """Initialize Memory Managers (流式输出) - deprecated, use initialize_stream_unified"""
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
                    modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
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

    def create_memory(self, name: str = None, username: str = None) -> Dict[str, Any]:
        """创建 Memory (包含 STM 和 LTM 功能，配置提取策略)"""
        logs = []
        code_snippet = ""

        try:
            logs.append("🚀 开始创建 Memory 资源（包含 STM 和 LTM 功能）")

            if not self.memory_client:
                logs.append("📡 初始化 MemoryClient...")
                self.memory_client = MemoryClient(region_name=self.region_name)
                logs.append(f"✅ MemoryClient 初始化成功 (region: {self.region_name})")

            # 检查用户是否已达到创建限制
            if username:
                user_memories = self.list_memories(username=username)
                if user_memories['success']:
                    total_count = user_memories.get('count', 0)
                    if total_count >= 5:
                        return {
                            "success": False,
                            "message": f"❌ 已达到 Memory 创建上限 (5个)。当前已有 {total_count} 个 Memory。",
                            "code": "",
                            "logs": [f"❌ 用户 {username} 已创建 {total_count} 个 Memory，已达到上限 (5个)"]
                        }

            # 添加用户前缀
            if not name:
                base_name = f"Memory_{uuid.uuid4().hex[:8]}"
                name = f"{username}_{base_name}" if username else base_name
                logs.append(f"📝 生成 Memory 名称: {name}")

            # 构建代码片段
            code_snippet = f'''from bedrock_agentcore.memory import MemoryClient

# 初始化 Memory Client
client = MemoryClient(region_name="{self.region_name}")

# 创建 Memory (包含 STM 和 LTM 功能)
memory = client.create_memory_and_wait(
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
    description="Memory with both STM (raw events) and LTM (extracted memories)",
    event_expiry_days=30  # 保存30天
)

print(f"Memory 创建成功: {{memory['id']}}")'''

            logs.append("⏳ 调用 AWS Bedrock AgentCore API 创建 Memory...")
            logs.append(f"   - 名称: {name}")
            logs.append(f"   - 策略: 语义记忆 + 用户偏好")
            logs.append(f"   - 事件保留期: 30 天")

            # 创建带策略的 Memory
            memory = self.memory_client.create_memory_and_wait(
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
                description="Memory with both STM (raw events) and LTM (extracted memories)",
                event_expiry_days=30
            )

            logs.append(f"✅ Memory 创建成功!")
            logs.append(f"   - Memory ID: {memory['id']}")
            logs.append(f"   - 状态: {memory.get('status', 'ACTIVE')}")
            logs.append(f"   - 策略数量: {len(memory.get('strategies', []))}")
            logs.append("")
            logs.append("💡 说明:")
            logs.append("   - STM: 原始对话事件会即时存储")
            logs.append("   - LTM: 5-15秒后异步提取语义和偏好信息")

            return {
                "success": True,
                "memory_id": memory['id'],
                "name": memory['name'],
                "code": code_snippet,
                "logs": logs,
                "strategies": [
                    {
                        "name": s.get("name", "N/A"),
                        "type": s.get("type", "N/A"),
                        "strategy_id": s.get("strategyId", "N/A")
                    }
                    for s in memory.get('strategies', [])
                ],
                "message": f"Memory 创建成功: {memory['id']}"
            }

        except Exception as e:
            logs.append(f"❌ Memory 创建失败: {str(e)}")
            return {
                "success": False,
                "message": f"Memory 创建失败: {str(e)}",
                "code": code_snippet,
                "logs": logs
            }

    def create_memory_stream(self, name: str = None, username: str = None) -> Generator[str, None, None]:
        """创建 Memory (流式输出，包含 STM 和 LTM 功能)"""
        import time as time_module
        start_time = time_module.time()

        try:
            yield self._send_event("log", "🚀 开始创建 Memory 资源（包含 STM 和 LTM 功能）")
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

            # 检查用户是否已达到创建限制
            if username:
                yield self._send_event("log", f"🔍 检查用户 {username} 的 Memory 数量...")
                user_memories = self.list_memories(username=username)
                if user_memories['success']:
                    total_count = user_memories.get('count', 0)
                    yield self._send_event("log", f"   当前已有 {total_count} 个 Memory (上限: 5)")
                    if total_count >= 5:
                        yield self._send_event("log", f"❌ 已达到 Memory 创建上限 (5个)")
                        yield self._send_event("result", {
                            "success": False,
                            "message": f"❌ 已达到 Memory 创建上限 (5个)。当前已有 {total_count} 个 Memory。"
                        })
                        return
                time_module.sleep(0.1)

            # 添加用户前缀
            if not name:
                base_name = f"Memory_{uuid.uuid4().hex[:8]}"
                name = f"{username}_{base_name}" if username else base_name
                elapsed = time_module.time() - start_time
                yield self._send_event("log", f"📝 生成 Memory 名称: {name} [{elapsed:.2f}s]")
                time_module.sleep(0.1)

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"⏳ 调用 AWS Bedrock AgentCore API 创建 Memory... [{elapsed:.2f}s]")
            yield self._send_event("log", f"   - 名称: {name}")
            yield self._send_event("log", f"   - 策略: 语义记忆 + 用户偏好")
            yield self._send_event("log", f"   - 事件保留期: 30 天")
            time_module.sleep(0.1)

            # 创建带策略的 Memory
            memory = self.memory_client.create_memory_and_wait(
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
                description="Memory with both STM (raw events) and LTM (extracted memories)",
                event_expiry_days=30
            )

            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"✅ Memory 创建成功! [{elapsed:.2f}s]")
            yield self._send_event("log", f"   - Memory ID: {memory['id']}")
            yield self._send_event("log", f"   - 状态: {memory.get('status', 'ACTIVE')}")
            yield self._send_event("log", f"   - 策略数量: {len(memory.get('strategies', []))}")
            yield self._send_event("log", "")
            yield self._send_event("log", "💡 说明:")
            yield self._send_event("log", "   - STM: 原始对话事件会即时存储")
            yield self._send_event("log", "   - LTM: 5-15秒后异步提取语义和偏好信息")

            yield self._send_event("result", {
                "success": True,
                "memory_id": memory['id'],
                "name": memory['name'],
                "strategies": [
                    {
                        "name": s.get("name", "N/A"),
                        "type": s.get("type", "N/A"),
                        "strategy_id": s.get("strategyId", "N/A")
                    }
                    for s in memory.get('strategies', [])
                ],
                "message": f"Memory 创建成功: {memory['id']}",
                "elapsed_time": f"{elapsed:.2f}s"
            })

        except Exception as e:
            elapsed = time_module.time() - start_time
            yield self._send_event("log", f"❌ Memory 创建失败: {str(e)} [{elapsed:.2f}s]")
            yield self._send_event("result", {
                "success": False,
                "elapsed_time": f"{elapsed:.2f}s",
                "message": f"Memory 创建失败: {str(e)}"
            })

    def list_memories(self, username: str = None) -> Dict[str, Any]:
        """列出当前用户的 Memory 资源"""
        try:
            if not self.memory_client:
                self.memory_client = MemoryClient(region_name=self.region_name)

            memories = self.memory_client.list_memories(max_results=100)

            memory_list = []
            stm_count = 0
            ltm_count = 0

            for memory in memories:
                # Memory 资源的名称实际上存储在 id/memoryId 字段中，不是 name 字段
                memory_id = memory.get('id', memory.get('memoryId', 'N/A'))
                memory_name = memory.get('name', memory_id)  # fallback to ID if name is missing

                # 过滤：仅显示属于当前用户的 Memory
                # 使用 memory_id 来判断（因为创建时我们设置的 name 实际上变成了 id）
                if username:
                    # 检查 memory_id 是否匹配用户名前缀
                    if not memory_id.startswith(f"{username}_"):
                        continue

                created_at = memory.get('createdAt', 'N/A')
                # Convert datetime to string if needed
                if created_at != 'N/A' and hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                elif created_at != 'N/A':
                    created_at = str(created_at)

                has_strategies = len(memory.get('strategies', [])) > 0
                memory_type = 'LTM' if has_strategies else 'STM'

                if memory_type == 'STM':
                    stm_count += 1
                else:
                    ltm_count += 1

                memory_info = {
                    "memory_id": memory.get('id', memory.get('memoryId', 'N/A')),
                    "name": memory_name,
                    "status": memory.get('status', 'N/A'),
                    "created_at": created_at,
                    "has_strategies": has_strategies,
                    "strategy_count": len(memory.get('strategies', [])),
                    "memory_type": memory_type
                }
                memory_list.append(memory_info)

            return {
                "success": True,
                "memories": memory_list,
                "count": len(memory_list),
                "stm_count": stm_count,
                "ltm_count": ltm_count,
                "message": f"找到 {len(memory_list)} 个 Memory 资源 (STM: {stm_count}, LTM: {ltm_count})"
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
