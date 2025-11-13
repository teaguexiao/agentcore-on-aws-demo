import os
import asyncio
import sys
import threading
from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends, Response, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from typing import List, Dict, Optional, Set
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import io
import secrets
from fastapi.middleware.wsgi import WSGIMiddleware
from pydantic import BaseModel
import time
import httpx

# Load environment variables BEFORE importing modules that depend on them
load_dotenv()

# Import computer use functions
# COMMENTED OUT: sandbox_computer_use.py module is missing
# from sandbox_computer_use import (
#     start_computer_desktop, run_computer_use_task, take_computer_screenshot,
#     stop_computer_task, kill_computer_desktop, init_computer_use_vars
# )

# Import Agentcore browser tool functions
from agentcore_browser_tool import (
    start_agentcore_browser, run_agentcore_browser_task, stop_agentcore_browser,
    init_agentcore_vars, agentcore_session_manager
)

# Import AgentCore code interpreter functions
from agentcore_code_interpreter import (
    execute_agentcore_code, reset_agentcore_sessions, get_active_sessions,
    execute_file_management_demo, execute_shell_command_demo, init_agentcore_code_interpreter_vars
)

# Import AgentCore memory API
from agentcore_memory_api import memory_api

# Import AgentCore runtime API
from agentcore_runtime_api import router as runtime_router, init_runtime_vars

# Configure logging
class WebSocketLogHandler(logging.Handler):
    def __init__(self, connection_manager):
        super().__init__()
        self.connection_manager = connection_manager
        self.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        self.buffer = []
        
    def clear_buffer(self):
        """Clear the log buffer"""
        self.buffer = []

    def emit(self, record):
        try:
            log_entry = self.format(record)
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_type = record.levelname.lower()
            
            # Map log levels to UI log types
            if log_type == 'warning':
                log_type = 'stderr'
            elif log_type == 'error' or log_type == 'critical':
                log_type = 'error'
            elif log_type == 'info':
                log_type = 'info'
            elif log_type == 'debug':
                log_type = 'stdout'
            
            # Store in buffer instead of trying to send immediately
            # Will be sent when a client connects
            self.buffer.append({
                "type": log_type,
                "timestamp": timestamp,
                "data": log_entry
            })
            
            # Only keep the last 1000 log entries to avoid memory issues
            if len(self.buffer) > 1000:
                self.buffer = self.buffer[-1000:]
                
        except Exception as e:
            # Don't use self.handleError to avoid potential infinite recursion
            print(f"Error in WebSocketLogHandler: {e}", file=sys.stderr)

# Set up connection manager first (will be initialized later)
connection_manager = None

# Configure root logger
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler()])

logger = logging.getLogger(__name__)

app = FastAPI(title="AgentCore on AWS Demo UI")

# Include routers
app.include_router(runtime_router)

# Mount static files directory
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Store active connections and desktop instance
connections: List[WebSocket] = []
desktop_instance = None
stream_url = None
# Current running background command reference
current_command = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.message_queue: List[Dict] = []
        # Session-aware connection management
        self.session_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_sessions: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # If session_id provided, associate connection with session
        if session_id:
            self.associate_session(websocket, session_id)
    
    def associate_session(self, websocket: WebSocket, session_id: str):
        """Associate an existing WebSocket connection with a session"""
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(websocket)
        self.connection_sessions[websocket] = session_id
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from session connections
        if websocket in self.connection_sessions:
            session_id = self.connection_sessions[websocket]
            if session_id in self.session_connections:
                self.session_connections[session_id].discard(websocket)
                # Clean up empty session connection sets
                if not self.session_connections[session_id]:
                    del self.session_connections[session_id]
            del self.connection_sessions[websocket]
    
    async def send_message(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending message: {e}", file=sys.stderr)
    
    async def send_json(self, data: Dict):
        # If no active connections, queue the message
        if not self.active_connections:
            self.message_queue.append(data)
            # Keep queue size reasonable
            if len(self.message_queue) > 1000:
                self.message_queue = self.message_queue[-1000:]
            return
            
        # Otherwise send to all connections
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                print(f"Error sending JSON: {e}", file=sys.stderr)
    
    async def send_to_session(self, session_id: str, data: Dict):
        """Send message only to connections in a specific session"""
        if session_id not in self.session_connections:
            # No connections for this session, queue the message
            print(f"No connections found for session {session_id}. Available sessions: {list(self.session_connections.keys())}", file=sys.stderr)
            if not hasattr(self, 'session_message_queues'):
                self.session_message_queues = {}
            if session_id not in self.session_message_queues:
                self.session_message_queues[session_id] = []
            
            self.session_message_queues[session_id].append(data)
            # Keep queue size reasonable
            if len(self.session_message_queues[session_id]) > 1000:
                self.session_message_queues[session_id] = self.session_message_queues[session_id][-1000:]
            return
        
        # Send to all connections in this session
        connections_to_remove = []
        connection_count = len(self.session_connections[session_id])
        print(f"Sending message to session {session_id} with {connection_count} connections", file=sys.stderr)
        
        for connection in self.session_connections[session_id]:
            try:
                await connection.send_json(data)
            except Exception as e:
                print(f"Error sending JSON to session {session_id}: {e}", file=sys.stderr)
                connections_to_remove.append(connection)
        
        # Clean up failed connections
        for connection in connections_to_remove:
            self.disconnect(connection)
    
    def get_session_id(self, websocket: WebSocket) -> Optional[str]:
        """Get the session ID for a WebSocket connection"""
        return self.connection_sessions.get(websocket)

manager = ConnectionManager()

# Now initialize the WebSocketLogHandler
ws_handler = WebSocketLogHandler(manager)

# Add the WebSocket handler to the root logger to capture all logs
root_logger = logging.getLogger()
root_logger.addHandler(ws_handler)

# Capture stdout and stderr
class StdoutCaptureHandler(io.StringIO):
    def __init__(self, connection_manager, log_type="stdout"):
        super().__init__()
        self.connection_manager = connection_manager
        self.log_type = log_type
        self.original = None
        self.buffer = []
    
    def write(self, data):
        if data and data.strip():
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Store in buffer instead of trying to send immediately
            self.buffer.append({
                "type": self.log_type,
                "timestamp": timestamp,
                "data": data
            })
            
            # Only keep the last 1000 log entries
            if len(self.buffer) > 1000:
                self.buffer = self.buffer[-1000:]
                
        # Write to the original stdout/stderr as well
        if self.original:
            self.original.write(data)
    
    def flush(self):
        if self.original:
            self.original.flush()

# Capture stdout and stderr
stdout_capture = StdoutCaptureHandler(manager, "stdout")
stdout_capture.original = sys.stdout
sys.stdout = stdout_capture

stderr_capture = StdoutCaptureHandler(manager, "stderr")
stderr_capture.original = sys.stderr
sys.stderr = stderr_capture

# Custom stdout/stderr handler for desktop commands
class WebSocketLogger:
    def __init__(self, manager, log_type="stdout"):
        self.manager = manager
        self.log_type = log_type
        self.loop = None
    
    def __call__(self, data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_data = {
            "type": self.log_type,
            "timestamp": timestamp,
            "data": data
        }
        
        # Store in manager's message queue for later delivery
        self.manager.message_queue.append(log_data)
        
        # Try to get event loop if we don't have one yet
        if not self.loop:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop, just use the queue
                pass
        
        # If we have an event loop and it's running, try to send immediately
        if self.loop and self.loop.is_running() and self.manager.active_connections:
            asyncio.run_coroutine_threadsafe(self.manager.send_json(log_data), self.loop)
            
        # Use print instead of logger to avoid duplicate logs
        print(f"[{self.log_type}] {data}")

# Session management
sessions = {}

def get_current_user(session_token: str = Cookie(None)):
    # Check if login is enabled
    login_enabled = os.getenv("LOGIN_ENABLE", "true").lower() == "true"
    
    # If login is disabled, return a default user
    if not login_enabled:
        return {"username": "default_user", "aws_login": "", "customer_name": ""}
    
    # Otherwise, check for valid session
    if session_token and session_token in sessions:
        return sessions[session_token]
    return None

# Login route
@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    # Check if login is enabled
    login_enabled = os.getenv("LOGIN_ENABLE", "true").lower() == "true"
    
    # If login is disabled, redirect to home page
    if not login_enabled:
        return RedirectResponse(url="/", status_code=303)
        
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def post_login(request: Request, response: Response, username: str = Form(...), password: str = Form(...), aws_login: str = Form(""), customer_name: str = Form("")):
    # Check if login is enabled
    login_enabled = os.getenv("LOGIN_ENABLE", "true").lower() == "true"
    
    # If login is disabled, redirect to home page
    if not login_enabled:
        return RedirectResponse(url="/", status_code=303)
    
    # Get credentials from .env
    expected_username = os.getenv("LOGIN_USERNAME")
    expected_password = os.getenv("LOGIN_PASSWORD")
    
    # Log the login attempt
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} | Username: {username} | Password: {'*' * len(password)} | AWS Login: {aws_login} | Customer Name: {customer_name}\n"
    
    try:
        with open("login_history.txt", "a") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        logger.error(f"Failed to write to login history: {e}")
    
    # Validate credentials
    if username == expected_username and password == expected_password:
        # Create session
        session_token = secrets.token_hex(16)
        sessions[session_token] = {"username": username, "aws_login": aws_login, "customer_name": customer_name}
        
        # Set cookie and redirect
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session_token", value=session_token, httponly=True)
        return response
    else:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Invalid username or password"}
        )

# Logout route
@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_token")
    return response

# Main route
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "active_page": "home"})


@app.get("/browser-use-agentcore", response_class=HTMLResponse)
async def get_browser_use_agentcore(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("browser-use-agentcore.html", {"request": request, "user": user, "active_page": "browser-use"})

# Removed - Computer Use feature
# @app.get("/computer-use", response_class=HTMLResponse)
# async def get_computer_use(request: Request, user: dict = Depends(get_current_user)):
#     if not user:
#         return RedirectResponse(url="/login", status_code=303)
#     return templates.TemplateResponse("computer-use.html", {"request": request, "user": user})

# Removed - Old Lambda Code Interpreter
# @app.get("/code-interpreter", response_class=HTMLResponse)
# async def get_code_interpreter(request: Request, user: dict = Depends(get_current_user)):
#     if not user:
#         return RedirectResponse(url="/login", status_code=303)
#     return templates.TemplateResponse("code-interpreter.html", {"request": request, "user": user, "active_page": "code-interpreter"})


@app.get("/code-interpreter-agentcore", response_class=HTMLResponse)
async def get_code_interpreter_agentcore(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("code-interpreter-agentcore.html", {"request": request, "user": user, "active_page": "code-interpreter"})


@app.get("/agentcore-runtime", response_class=HTMLResponse)
async def get_agentcore_runtime(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("agentcore-runtime.html", {"request": request, "user": user, "active_page": "agentcore-runtime"})

@app.get("/agentcore-memory", response_class=HTMLResponse)
async def get_agentcore_memory(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("agentcore-memory.html", {"request": request, "user": user, "active_page": "agentcore-memory"})

@app.get("/agentcore-gateway", response_class=HTMLResponse)
async def get_agentcore_gateway(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("agentcore-gateway.html", {"request": request, "user": user, "active_page": "agentcore-gateway"})

# Removed - Old EC2 Code Interpreter
# @app.get("/code-interpreter-ec2", response_class=HTMLResponse)
# async def get_code_interpreter_ec2(request: Request, user: dict = Depends(get_current_user)):
#     if not user:
#         return RedirectResponse(url="/login", status_code=303)
#     return templates.TemplateResponse("code-interpreter-ec2.html", {"request": request, "user": user, "active_page": "code-interpreter"})

# Removed - AI Search feature
# @app.get("/ai-search", response_class=HTMLResponse)
# async def get_ai_search(request: Request, user: dict = Depends(get_current_user)):
#     if not user:
#         return RedirectResponse(url="/login", status_code=303)
#     return templates.TemplateResponse("ai-search.html", {"request": request, "user": user})

# Removed - AI PPT feature
# @app.get("/ai-ppt", response_class=HTMLResponse)
# async def get_ai_ppt(request: Request, user: dict = Depends(get_current_user)):
#     if not user:
#         return RedirectResponse(url="/login", status_code=303)
#     return templates.TemplateResponse("ai-ppt.html", {"request": request, "user": user})


# Computer Use API endpoints
# COMMENTED OUT: sandbox_computer_use module is missing
# @app.post("/start-computer-desktop")
# async def start_computer_desktop_endpoint(session_id: str = Form(None)):
#     """Start computer use desktop"""
#     return await start_computer_desktop(session_id=session_id)
#
# @app.post("/run-computer-use-task")
# async def run_computer_use_task_endpoint(query: str = Form(...), session_id: str = Form(None), background_tasks: BackgroundTasks = BackgroundTasks()):
#     """Run computer use task (starts desktop if needed)"""
#     try:
#         return await run_computer_use_task(query, session_id=session_id, background_tasks=background_tasks)
#     except Exception as e:
#         logger.error(f"Error in run_computer_use_task_endpoint: {e}", exc_info=True)
#         return {"status": "error", "message": str(e)}
#
# @app.post("/run-computer-task")
# async def run_computer_task_endpoint(query: str = Form(...), session_id: str = Form(None), sandbox_id: str = Form(None), background_tasks: BackgroundTasks = BackgroundTasks()):
#     """Run computer task on existing desktop"""
#     try:
#         return await run_computer_use_task(query, session_id=session_id, sandbox_id=sandbox_id, background_tasks=background_tasks)
#     except Exception as e:
#         logger.error(f"Error in run_computer_task_endpoint: {e}", exc_info=True)
#         return {"status": "error", "message": str(e)}
#
# @app.post("/take-computer-screenshot")
# async def take_computer_screenshot_endpoint(session_id: str = Form(None), sandbox_id: str = Form(None)):
#     """Take a screenshot of the computer desktop"""
#     try:
#         return await take_computer_screenshot(session_id=session_id, sandbox_id=sandbox_id)
#     except Exception as e:
#         logger.error(f"Error in take_computer_screenshot_endpoint: {e}", exc_info=True)
#         return {"status": "error", "message": str(e)}
#
# @app.post("/stop-computer-task")
# async def stop_computer_task_endpoint(session_id: str = Form(None)):
#     """Stop the currently running computer task"""
#     try:
#         return await stop_computer_task(session_id=session_id)
#     except Exception as e:
#         logger.error(f"Error in stop_computer_task_endpoint: {e}", exc_info=True)
#         return {"status": "error", "message": str(e)}
#
# @app.post("/kill-computer-desktop")
# async def kill_computer_desktop_endpoint(session_id: str = Form(None)):
#     """Kill the computer desktop instance"""
#     try:
#         return await kill_computer_desktop(session_id=session_id)
#     except Exception as e:
#         logger.error(f"Error in kill_computer_desktop_endpoint: {e}", exc_info=True)
#         return {"status": "error", "message": str(e)}

# Agentcore BrowserTool API endpoints
@app.post("/start-agentcore-browser")
async def start_agentcore_browser_endpoint(session_id: str = Form(None), region: str = Form("us-west-2")):
    """Start Agentcore browser session"""
    try:
        return await start_agentcore_browser(session_id=session_id, region=region)
    except Exception as e:
        logger.error(f"Error in start_agentcore_browser_endpoint: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@app.post("/run-agentcore-browser-task")
async def run_agentcore_browser_task_endpoint(prompt: str = Form(...), session_id: str = Form(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """Run Agentcore browser automation task"""
    try:
        # Run task in background
        background_tasks.add_task(run_agentcore_browser_task, prompt, session_id)
        return {"status": "success", "message": "Agentcore browser task started"}
    except Exception as e:
        logger.error(f"Error in run_agentcore_browser_task_endpoint: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@app.post("/stop-agentcore-browser")
async def stop_agentcore_browser_endpoint(session_id: str = Form(...)):
    """Stop Agentcore browser session"""
    try:
        return await stop_agentcore_browser(session_id=session_id)
    except Exception as e:
        logger.error(f"Error in stop_agentcore_browser_endpoint: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@app.get("/api/sessions/status")
async def get_sessions_status():
    """Get status of all active sessions (computer-use and browser-use)"""
    try:
        # Computer-use sessions - DISABLED (module missing)
        computer_sessions = []

        # Browser-use sessions - REMOVED (E2B dependency removed)
        browser_sessions = []

        # Agentcore browser sessions
        agentcore_sessions = []
        for session_id, session in agentcore_session_manager.sessions.items():
            session_info = {
                "session_id": session_id,
                "type": "agentcore-browser",
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "has_browser_client": session.browser_client is not None,
                "has_browser_session": session.browser_session is not None,
                "has_viewer_url": session.viewer_url is not None,
                "task_running": session.current_task is not None,
                "connections": len(session.connections)
            }
            agentcore_sessions.append(session_info)

        all_sessions = computer_sessions + browser_sessions + agentcore_sessions
        
        # Also include WebSocket connection info
        websocket_info = {
            "total_connections": len(manager.active_connections),
            "session_connections": {k: len(v) for k, v in manager.session_connections.items()},
            "connection_sessions": len(manager.connection_sessions)
        }
        
        return {
            "status": "success",
            "total_sessions": len(all_sessions),
            "computer_use_sessions": len(computer_sessions),
            "browser_use_sessions": len(browser_sessions),
            "agentcore_browser_sessions": len(agentcore_sessions),
            "sessions": all_sessions,
            "websocket_info": websocket_info
        }
    except Exception as e:
        logger.error(f"Error getting sessions status: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

# AWS Bedrock AgentCore Code Interpreter API endpoints
class CodeRequest(BaseModel):
    code: str

@app.post("/api/agentcore/execute")
async def execute_agentcore_code_endpoint(code_request: CodeRequest):
    """Execute code using AWS Bedrock AgentCore and return the result"""
    result = await execute_agentcore_code(code_request.code)

    if result["success"]:
        return JSONResponse({
            "success": True,
            "output": result["output"],
            "session_id": result["session_id"]
        })
    else:
        return JSONResponse({
            "success": False,
            "error": result["error"]
        }, status_code=500)

@app.post("/api/agentcore/reset")
async def reset_agentcore_session_endpoint():
    """Reset AgentCore session by stopping all active sessions"""
    result = await reset_agentcore_sessions()

    if result["success"]:
        return JSONResponse({
            "success": True,
            "message": result["message"]
        })
    else:
        return JSONResponse({
            "success": False,
            "error": result["error"]
        }, status_code=500)

@app.post("/api/agentcore/file-management")
async def execute_file_management_demo_endpoint():
    """Execute file management demonstration using AWS Bedrock AgentCore"""
    result = await execute_file_management_demo()

    if result["success"]:
        return JSONResponse({
            "success": True,
            "output": result["output"],
            "session_id": result["session_id"]
        })
    else:
        return JSONResponse({
            "success": False,
            "error": result["error"]
        }, status_code=500)

@app.post("/api/agentcore/shell-command")
async def execute_shell_command_demo_endpoint():
    """Execute shell command demonstration using AWS Bedrock AgentCore"""
    result = await execute_shell_command_demo()

    if result["success"]:
        return JSONResponse({
            "success": True,
            "output": result["output"],
            "session_id": result["session_id"]
        })
    else:
        return JSONResponse({
            "success": False,
            "error": result["error"]
        }, status_code=500)

# AgentCore Memory API endpoints
class MemoryInitRequest(BaseModel):
    stm_memory_id: str
    ltm_memory_id: str

class MemorySTMStep1Request(BaseModel):
    user_message: str
    actor_id: str

class MemorySTMStep2Request(BaseModel):
    user_message: str
    session_id: str
    actor_id: str

class MemoryLTMStep1Request(BaseModel):
    user_preference: str
    actor_id: str

class MemoryLTMStep2Request(BaseModel):
    user_question: str
    actor_id: str

class MemoryCombinedRequest(BaseModel):
    user_question: str
    actor_id: str

@app.post("/api/memory/initialize")
async def initialize_memory(request: MemoryInitRequest):
    """Initialize Memory Managers"""
    result = memory_api.initialize(request.stm_memory_id, request.ltm_memory_id)
    return JSONResponse(result)

@app.get("/api/memory/initialize-stream")
async def initialize_memory_stream(stm_memory_id: str, ltm_memory_id: str):
    """Initialize Memory Managers (streaming)"""
    async def event_generator():
        for event in memory_api.initialize_stream(stm_memory_id, ltm_memory_id):
            yield event
            await asyncio.sleep(0.05)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/memory/stm/step1")
async def memory_stm_step1(request: MemorySTMStep1Request):
    """STM Demo - Step 1: Store first message"""
    result = memory_api.demo_stm_step1(request.user_message, request.actor_id)
    return JSONResponse(result)

@app.get("/api/memory/stm/step1-stream")
async def memory_stm_step1_stream(user_message: str, actor_id: str):
    """STM Demo - Step 1: Store first message (streaming)"""
    async def event_generator():
        for event in memory_api.demo_stm_step1_stream(user_message, actor_id):
            yield event
            await asyncio.sleep(0.05)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/memory/stm/step2")
async def memory_stm_step2(request: MemorySTMStep2Request):
    """STM Demo - Step 2: Query with history"""
    result = memory_api.demo_stm_step2(request.user_message, request.session_id, request.actor_id)
    return JSONResponse(result)

@app.get("/api/memory/stm/step2-stream")
async def memory_stm_step2_stream(user_message: str, session_id: str, actor_id: str):
    """STM Demo - Step 2: Query with history (streaming)"""
    async def event_generator():
        for event in memory_api.demo_stm_step2_stream(user_message, session_id, actor_id):
            yield event
            await asyncio.sleep(0.05)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/memory/ltm/step1")
async def memory_ltm_step1(request: MemoryLTMStep1Request):
    """LTM Demo - Step 1: Express preferences"""
    result = memory_api.demo_ltm_step1(request.user_preference, request.actor_id)
    return JSONResponse(result)

@app.post("/api/memory/ltm/step2")
async def memory_ltm_step2(request: MemoryLTMStep2Request):
    """LTM Demo - Step 2: Retrieve from new session"""
    result = memory_api.demo_ltm_step2(request.user_question, request.actor_id)
    return JSONResponse(result)

@app.get("/api/memory/ltm/step1-stream")
async def memory_ltm_step1_stream(user_preference: str, actor_id: str):
    """LTM Demo - Step 1: Express preferences (streaming)"""
    async def event_generator():
        for event in memory_api.demo_ltm_step1_stream(user_preference, actor_id):
            yield event
            await asyncio.sleep(0.05)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/memory/ltm/step2-stream")
async def memory_ltm_step2_stream(user_question: str, actor_id: str):
    """LTM Demo - Step 2: Retrieve from new session (streaming)"""
    async def event_generator():
        for event in memory_api.demo_ltm_step2_stream(user_question, actor_id):
            yield event
            await asyncio.sleep(0.05)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/memory/combined")
async def memory_combined(request: MemoryCombinedRequest):
    """Combined Demo: STM + LTM"""
    result = memory_api.demo_combined(request.user_question, request.actor_id)
    return JSONResponse(result)

@app.get("/api/memory/combined-stream")
async def memory_combined_stream(user_question: str, actor_id: str):
    """Combined Demo: STM + LTM (streaming)"""
    async def event_generator():
        for event in memory_api.demo_combined_stream(user_question, actor_id):
            yield event
            await asyncio.sleep(0.05)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Memory Management API endpoints
class CreateMemoryRequest(BaseModel):
    name: Optional[str] = None

class ListEventsRequest(BaseModel):
    actor_id: str
    session_id: Optional[str] = None
    max_results: Optional[int] = 10

class ListRecordsRequest(BaseModel):
    actor_id: Optional[str] = None
    max_results: Optional[int] = 10

class DeleteMemoryRequest(BaseModel):
    memory_id: str

@app.post("/api/memory/create-stm")
async def create_stm_memory(request: CreateMemoryRequest):
    """Create STM Memory"""
    result = memory_api.create_stm_memory(request.name)
    return JSONResponse(result)

@app.get("/api/memory/create-stm-stream")
async def create_stm_memory_stream(name: str = None):
    """Create STM Memory with streaming response"""
    async def event_generator():
        for event in memory_api.create_stm_memory_stream(name):
            yield event
            # Small delay to ensure proper streaming
            await asyncio.sleep(0.1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/memory/create-ltm")
async def create_ltm_memory(request: CreateMemoryRequest):
    """Create LTM Memory"""
    result = memory_api.create_ltm_memory(request.name)
    return JSONResponse(result)

@app.get("/api/memory/create-ltm-stream")
async def create_ltm_memory_stream(name: str = None):
    """Create LTM Memory with streaming response"""
    async def event_generator():
        for event in memory_api.create_ltm_memory_stream(name):
            yield event
            # Small delay to ensure proper streaming
            await asyncio.sleep(0.1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/memory/list")
async def list_memories():
    """List all Memory resources"""
    result = memory_api.list_memories()
    return JSONResponse(result)

@app.post("/api/memory/list-stm-events")
async def list_stm_events(request: ListEventsRequest):
    """List STM events"""
    result = memory_api.list_stm_events(request.actor_id, request.session_id, request.max_results)
    return JSONResponse(result)

@app.post("/api/memory/list-ltm-records")
async def list_ltm_records(request: ListRecordsRequest):
    """List LTM records"""
    result = memory_api.list_ltm_records(request.actor_id, request.max_results)
    return JSONResponse(result)

@app.post("/api/memory/delete")
async def delete_memory(request: DeleteMemoryRequest):
    """Delete Memory resource"""
    result = memory_api.delete_memory(request.memory_id)
    return JSONResponse(result)

# Initialize shared variables
if __name__ == "__main__":

    # Initialize shared variables in computer_use.py - DISABLED (module missing)
    # init_computer_use_vars(manager, logger, ws_handler, stdout_capture, stderr_capture, sessions)

    # Initialize shared variables in agentcore_browser_tool.py
    init_agentcore_vars(manager, logger)

    # Initialize shared variables in agentcore_code_interpreter.py
    init_agentcore_code_interpreter_vars(logger)

    # Initialize shared variables in agentcore_runtime_api.py
    init_runtime_vars(manager)

    # Log startup message
    logger.info("Starting AgentCore on AWS Demo UI")
    logger.info("All logs will be streamed to the WebUI")
    
    # Start the FastAPI application
    uvicorn.run("app:app", host="0.0.0.0", port=8090, log_level="info")
