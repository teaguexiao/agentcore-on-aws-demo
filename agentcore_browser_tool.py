"""
Agentcore BrowserTool integration for web interface
Based on live_view_with_browser_use.py functionality
"""

import asyncio
import logging
import os
import uuid
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from contextlib import suppress

from browser_use import Agent
from browser_use.browser.session import BrowserSession
from bedrock_agentcore.tools.browser_client import BrowserClient
from browser_use.browser import BrowserProfile
from langchain_aws import ChatBedrockConverse

# Global variables for session management
agentcore_session_manager = None
agentcore_manager = None
agentcore_logger = None

# Session timeout in seconds (20 minutes)
AGENTCORE_SESSION_TIMEOUT = 1200

class AgentcoreBrowserSession:
    """Represents a single Agentcore browser session with isolated resources"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.browser_client: Optional[BrowserClient] = None
        self.browser_session: Optional[BrowserSession] = None
        self.bedrock_chat: Optional[ChatBedrockConverse] = None
        self.ws_url: Optional[str] = None
        self.presigned_url: Optional[str] = None  # DCV presigned URL for viewer
        self.headers: Optional[dict] = None
        self.connections: Set = set()
        self.last_activity = datetime.now()
        self.created_at = datetime.now()
        self.current_task = None
        
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = datetime.now()
        
    def is_expired(self) -> bool:
        """Check if the session has expired"""
        return datetime.now() - self.last_activity > timedelta(seconds=AGENTCORE_SESSION_TIMEOUT)

class AgentcoreSessionManager:
    """Manages multiple Agentcore browser sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, AgentcoreBrowserSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
    def create_session(self) -> str:
        """Create a new session and return its ID"""
        session_id = f"agentcore_{uuid.uuid4().hex[:12]}"
        session = AgentcoreBrowserSession(session_id)
        self.sessions[session_id] = session
        
        if agentcore_logger:
            agentcore_logger.info(f"Created new Agentcore browser session: {session_id}")
            
        # Start cleanup task if not already running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
        return session_id
    
    def get_session(self, session_id: str) -> Optional[AgentcoreBrowserSession]:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()
        return session
    
    async def cleanup_session(self, session_id: str):
        """Clean up a specific session"""
        session = self.sessions.get(session_id)
        if session:
            try:
                # Close browser session
                if session.browser_session:
                    with suppress(Exception):
                        await session.browser_session.close()

                # Stop viewer server
                if session.viewer_server:
                    with suppress(Exception):
                        session.viewer_server.stop()

                # Stop browser client
                if session.browser_client:
                    with suppress(Exception):
                        session.browser_client.stop()

                # Remove from sessions
                del self.sessions[session_id]

                if agentcore_logger:
                    agentcore_logger.info(f"Cleaned up Agentcore session: {session_id}")

            except Exception as e:
                if agentcore_logger:
                    agentcore_logger.error(f"Error cleaning up Agentcore session {session_id}: {e}")
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                expired_sessions = [
                    session_id for session_id, session in self.sessions.items()
                    if session.is_expired()
                ]
                
                for session_id in expired_sessions:
                    await self.cleanup_session(session_id)
                    
            except Exception as e:
                if agentcore_logger:
                    agentcore_logger.error(f"Error in Agentcore session cleanup: {e}")

# Initialize session manager
agentcore_session_manager = AgentcoreSessionManager()

async def start_agentcore_browser(session_id: str = None, region: str = "us-east-2"):
    """Start Agentcore browser session"""

    if agentcore_logger:
        agentcore_logger.info(f"[start_agentcore_browser] Called with session_id: {session_id}, region: {region}")

    if not agentcore_session_manager:
        return {"status": "error", "message": "Session manager not initialized"}

    # Create new session if none provided
    if not session_id:
        session_id = agentcore_session_manager.create_session()
        if agentcore_logger:
            agentcore_logger.info(f"[start_agentcore_browser] No session_id provided, created new: {session_id}")
    else:
        # Check if session exists, create if not
        session = agentcore_session_manager.get_session(session_id)
        if not session:
            session = AgentcoreBrowserSession(session_id)
            agentcore_session_manager.sessions[session_id] = session
            if agentcore_logger:
                agentcore_logger.info(f"[start_agentcore_browser] Created new Agentcore session with provided ID: {session_id}")
        else:
            if agentcore_logger:
                agentcore_logger.info(f"[start_agentcore_browser] Using existing session: {session_id}")
    
    session = agentcore_session_manager.get_session(session_id)
    if not session:
        return {"status": "error", "message": "Failed to create session"}
    
    try:
        if agentcore_logger:
            agentcore_logger.info(f"Starting Agentcore browser for session {session_id}")

        # Create browser client
        session.browser_client = BrowserClient(region)
        session.browser_client.start()

        # Generate WebSocket URL and headers for CDP automation
        session.ws_url, session.headers = session.browser_client.generate_ws_headers()

        # Generate the DCV live view presigned URL for frontend viewer
        # This is different from the CDP WebSocket URL used for automation
        # Max expiry is 300 seconds (5 minutes)
        session.presigned_url = session.browser_client.generate_live_view_url(expires=300)

        if agentcore_logger:
            agentcore_logger.info(f"Generated DCV live view URL for session {session_id}")
            agentcore_logger.info(f"CDP WebSocket URL: {session.ws_url}")
            agentcore_logger.info(f"DCV Live View URL: {session.presigned_url}")
            agentcore_logger.info(f"DCV Live View URL length: {len(session.presigned_url)} characters")

        # Create browser profile with headers
        browser_profile = BrowserProfile(
            headers=session.headers,
            timeout=1500000,  # 150 seconds timeout
        )

        # Create browser session
        session.browser_session = BrowserSession(
            cdp_url=session.ws_url,
            browser_profile=browser_profile,
            keep_alive=True,  # Keep browser alive between tasks
        )

        # Initialize the browser session
        await session.browser_session.start()

        # Create ChatBedrockConverse
        session.bedrock_chat = ChatBedrockConverse(
            model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            region_name=region,
        )

        if agentcore_logger:
            agentcore_logger.info(f"Agentcore browser session {session_id} started successfully")

        # Send success message to connected clients with presigned URL
        if agentcore_manager:
            # Wait a moment to ensure WebSocket has identified itself
            import asyncio
            await asyncio.sleep(0.5)

            if agentcore_logger:
                agentcore_logger.info(f"Sending agentcore_browser_started message to session {session_id}")

            await agentcore_manager.send_to_session(session_id, {
                "type": "agentcore_browser_started",
                "data": {
                    "session_id": session_id,
                    "presigned_url": session.presigned_url,
                    "status": "ready"
                }
            })

            if agentcore_logger:
                agentcore_logger.info(f"Message sent to session {session_id}")

        return {
            "status": "success",
            "message": "Agentcore browser started successfully",
            "session_id": session_id,
            "presigned_url": session.presigned_url
        }
        
    except Exception as e:
        if agentcore_logger:
            agentcore_logger.error(f"Error starting Agentcore browser for session {session_id}: {e}")
        
        # Clean up on error
        await agentcore_session_manager.cleanup_session(session_id)
        
        return {"status": "error", "message": f"Failed to start Agentcore browser: {str(e)}"}

async def run_agentcore_browser_task(prompt: str, session_id: str):
    """Run a browser automation task using Agentcore BrowserTool"""
    
    if not session_id:
        return {"status": "error", "message": "Session ID required"}
    
    session = agentcore_session_manager.get_session(session_id)
    if not session or not session.browser_session or not session.bedrock_chat:
        return {"status": "error", "message": "No active browser session available"}
    
    try:
        if agentcore_logger:
            agentcore_logger.info(f"Running Agentcore browser task for session {session_id}: {prompt}")
        
        # Send task start message
        if agentcore_manager:
            await agentcore_manager.send_to_session(session_id, {
                "type": "info",
                "data": f"🤖 Executing browser task: {prompt}"
            })
        
        # Create and run the agent
        agent = Agent(task=prompt, llm=session.bedrock_chat, browser_session=session.browser_session)
        
        # Store current task reference
        session.current_task = agent
        
        # Run the agent
        await agent.run()
        
        # Clear current task reference
        session.current_task = None
        
        if agentcore_logger:
            agentcore_logger.info(f"Agentcore browser task completed for session {session_id}")
        
        # Send completion message
        if agentcore_manager:
            await agentcore_manager.send_to_session(session_id, {
                "type": "agentcore_task_completed",
                "data": "✅ Browser task completed successfully!"
            })
        
        return {"status": "success", "message": "Browser task completed successfully"}
        
    except Exception as e:
        if agentcore_logger:
            agentcore_logger.error(f"Error running Agentcore browser task for session {session_id}: {e}")
        
        # Clear current task reference
        session.current_task = None
        
        # Send error message
        if agentcore_manager:
            await agentcore_manager.send_to_session(session_id, {
                "type": "error",
                "data": f"❌ Error during browser task execution: {str(e)}"
            })
        
        return {"status": "error", "message": f"Browser task failed: {str(e)}"}

async def stop_agentcore_browser(session_id: str):
    """Stop Agentcore browser session"""
    
    if not session_id:
        return {"status": "error", "message": "Session ID required"}
    
    session = agentcore_session_manager.get_session(session_id)
    if not session:
        return {"status": "error", "message": "Session not found"}
    
    try:
        if agentcore_logger:
            agentcore_logger.info(f"Stopping Agentcore browser session {session_id}")
        
        # Clean up the session
        await agentcore_session_manager.cleanup_session(session_id)
        
        # Send stop message
        if agentcore_manager:
            await agentcore_manager.send_to_session(session_id, {
                "type": "agentcore_browser_stopped",
                "data": "Agentcore browser session stopped"
            })
        
        return {"status": "success", "message": "Agentcore browser session stopped"}
        
    except Exception as e:
        if agentcore_logger:
            agentcore_logger.error(f"Error stopping Agentcore browser session {session_id}: {e}")
        
        return {"status": "error", "message": f"Failed to stop browser session: {str(e)}"}

def init_agentcore_vars(app_manager, app_logger):
    """Initialize shared variables from app.py"""
    global agentcore_manager, agentcore_logger
    agentcore_manager = app_manager
    agentcore_logger = app_logger
