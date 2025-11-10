"""
AWS Bedrock AgentCore Code Interpreter integration for web interface
Provides code execution capabilities using AWS Bedrock AgentCore service
"""

import os
import boto3
import logging
import traceback
from typing import Dict, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables to ensure AWS credentials are available
load_dotenv()

# Global variables for session management
agentcore_logger = None

# Global AgentCore session tracking
agentcore_sessions: Dict[str, Any] = {}

# Configuration constants
AGENTCORE_REGION = "us-west-2"
AGENTCORE_ENDPOINT = "https://bedrock-agentcore.us-west-2.amazonaws.com"
CODE_INTERPRETER_IDENTIFIER = "aws.codeinterpreter.v1"
SESSION_TIMEOUT_SECONDS = 900
SESSION_NAME = "my-code-session"


class AgentCoreCodeInterpreter:
    """AWS Bedrock AgentCore Code Interpreter client wrapper"""
    
    def __init__(self, region: str = AGENTCORE_REGION, endpoint_url: str = AGENTCORE_ENDPOINT):
        self.region = region
        self.endpoint_url = endpoint_url
        self.client = None
        
    def _get_client(self):
        """Get or create boto3 client for Bedrock AgentCore"""
        if self.client is None:
            self.client = boto3.client(
                "bedrock-agentcore", 
                region_name=self.region, 
                endpoint_url=self.endpoint_url
            )
        return self.client
    
    def start_session(self, session_name: str = SESSION_NAME) -> str:
        """Start a new code interpreter session"""
        client = self._get_client()
        
        session_response = client.start_code_interpreter_session(
            codeInterpreterIdentifier=CODE_INTERPRETER_IDENTIFIER,
            name=session_name,
            sessionTimeoutSeconds=SESSION_TIMEOUT_SECONDS
        )
        
        session_id = session_response["sessionId"]
        
        if agentcore_logger:
            agentcore_logger.info(f"Started AgentCore session: {session_id}")
        
        return session_id
    
    def execute_code(self, session_id: str, code: str) -> str:
        """Execute code in the specified session and return output"""
        client = self._get_client()

        execute_response = client.invoke_code_interpreter(
            codeInterpreterIdentifier=CODE_INTERPRETER_IDENTIFIER,
            sessionId=session_id,
            name="executeCode",
            arguments={
                "language": "python",
                "code": code
            }
        )

        # Extract text output from the stream
        output_text = ""
        for event in execute_response['stream']:
            if 'result' in event:
                result = event['result']
                if 'content' in result:
                    for content_item in result['content']:
                        if content_item['type'] == 'text':
                            output_text += content_item['text'] + "\n"

        return output_text.strip()

    def write_files(self, session_id: str, files: list) -> Dict[str, Any]:
        """
        Write files to the code interpreter session

        Args:
            session_id: The session ID
            files: List of file dictionaries with 'path' and 'text' keys

        Returns:
            Dictionary with success status and result
        """
        client = self._get_client()

        write_response = client.invoke_code_interpreter(
            codeInterpreterIdentifier=CODE_INTERPRETER_IDENTIFIER,
            sessionId=session_id,
            name="writeFiles",
            arguments={
                "content": files
            }
        )

        # Extract result from the stream
        result_data = {}
        for event in write_response['stream']:
            if 'result' in event:
                result_data = event['result']
                break

        return result_data

    def list_files(self, session_id: str, path: str = "") -> Dict[str, Any]:
        """
        List files in the code interpreter session

        Args:
            session_id: The session ID
            path: Path to list files from (empty string for root)

        Returns:
            Dictionary with success status and file list
        """
        client = self._get_client()

        list_response = client.invoke_code_interpreter(
            codeInterpreterIdentifier=CODE_INTERPRETER_IDENTIFIER,
            sessionId=session_id,
            name="listFiles",
            arguments={
                "path": path
            }
        )

        # Extract result from the stream
        result_data = {}
        for event in list_response['stream']:
            if 'result' in event:
                result_data = event['result']
                break

        return result_data

    def delete_files(self, session_id: str, paths: list) -> Dict[str, Any]:
        """
        Delete files from the code interpreter session

        Args:
            session_id: The session ID
            paths: List of file paths to delete

        Returns:
            Dictionary with success status and result
        """
        client = self._get_client()

        delete_response = client.invoke_code_interpreter(
            codeInterpreterIdentifier=CODE_INTERPRETER_IDENTIFIER,
            sessionId=session_id,
            name="removeFiles",  # Correct operation name is 'removeFiles', not 'deleteFiles'
            arguments={
                "paths": paths
            }
        )

        # Extract result from the stream
        result_data = {}
        for event in delete_response['stream']:
            if 'result' in event:
                result_data = event['result']
                break

        return result_data

    def execute_command(self, session_id: str, command: str) -> str:
        """
        Execute a shell command in the code interpreter session

        Args:
            session_id: The session ID
            command: Shell command to execute

        Returns:
            String containing the command output
        """
        client = self._get_client()

        command_response = client.invoke_code_interpreter(
            codeInterpreterIdentifier=CODE_INTERPRETER_IDENTIFIER,
            sessionId=session_id,
            name="executeCommand",
            arguments={
                "command": command
            }
        )

        # Extract text output from the stream
        output_text = ""
        for event in command_response['stream']:
            if 'result' in event:
                result = event['result']
                if 'content' in result:
                    for content_item in result['content']:
                        if content_item['type'] == 'text':
                            output_text += content_item['text'] + "\n"

        return output_text.strip()

    def stop_session(self, session_id: str) -> bool:
        """Stop a code interpreter session"""
        try:
            client = self._get_client()
            client.stop_code_interpreter_session(
                codeInterpreterIdentifier=CODE_INTERPRETER_IDENTIFIER,
                sessionId=session_id
            )
            
            if agentcore_logger:
                agentcore_logger.info(f"Stopped AgentCore session: {session_id}")
            
            return True
        except Exception as e:
            if agentcore_logger:
                agentcore_logger.warning(f"Error stopping session {session_id}: {e}")
            return False


async def execute_agentcore_code(code: str) -> Dict[str, Any]:
    """
    Execute code using AWS Bedrock AgentCore and return the result
    
    Args:
        code: Python code to execute
        
    Returns:
        Dictionary with success status, output, session_id, and error (if any)
    """
    try:
        # Create AgentCore client
        interpreter = AgentCoreCodeInterpreter()
        
        # Start a new session
        session_id = interpreter.start_session()
        
        # Execute the code
        output_text = interpreter.execute_code(session_id, code)
        
        # Store session and client for later cleanup
        agentcore_sessions[session_id] = interpreter
        
        return {
            "success": True,
            "output": output_text,
            "session_id": session_id
        }
    except Exception as e:
        if agentcore_logger:
            agentcore_logger.error(f"Error executing code in AgentCore: {str(e)}")
        
        return {
            "success": False,
            "error": str(e)
        }


async def execute_file_management_demo() -> Dict[str, Any]:
    """
    Execute a file management demonstration showing writeFiles, listFiles, and deleteFiles

    Returns:
        Dictionary with success status, output, session_id, and error (if any)
    """
    try:
        # Create AgentCore client
        interpreter = AgentCoreCodeInterpreter()

        # Start a new session
        session_id = interpreter.start_session()

        # Store session for later cleanup
        agentcore_sessions[session_id] = interpreter

        output_lines = []

        # Step 1: Write sample files
        output_lines.append("📝 Step 1: Writing files to sandbox...")
        output_lines.append("")

        files_to_create = [
            {
                "path": "data.csv",
                "text": "Date,Sales,Region\n2024-01-01,1500,North\n2024-01-02,1800,South\n2024-01-03,1200,East"
            },
            {
                "path": "stats.py",
                "text": "import pandas as pd\n\ndf = pd.read_csv('data.csv')\nprint('Sales Summary:')\nprint(df.describe())"
            }
        ]

        write_result = interpreter.write_files(session_id, files_to_create)
        output_lines.append(f"✅ Files written successfully!")
        output_lines.append(f"   - data.csv (3 rows of sales data)")
        output_lines.append(f"   - stats.py (Python analysis script)")
        output_lines.append("")

        # Step 2: List files
        output_lines.append("📂 Step 2: Listing files in sandbox...")
        output_lines.append("")

        list_result = interpreter.list_files(session_id, "")

        if 'content' in list_result:
            for content_item in list_result['content']:
                if content_item['type'] == 'text':
                    output_lines.append(content_item['text'])

        output_lines.append("")

        # Step 3: Execute the Python script to verify files work
        output_lines.append("▶️  Step 3: Executing stats.py to verify files...")
        output_lines.append("")

        code_output = interpreter.execute_code(session_id, files_to_create[1]['text'])
        output_lines.append(code_output)
        output_lines.append("")

        # Step 4: Delete one file
        output_lines.append("🗑️  Step 4: Deleting stats.py...")
        output_lines.append("")

        delete_result = interpreter.delete_files(session_id, ["stats.py"])
        output_lines.append("✅ File deleted successfully!")
        output_lines.append("")

        # Step 5: List files again to confirm deletion
        output_lines.append("📂 Step 5: Listing files after deletion...")
        output_lines.append("")

        list_result_after = interpreter.list_files(session_id, "")

        if 'content' in list_result_after:
            for content_item in list_result_after['content']:
                if content_item['type'] == 'text':
                    output_lines.append(content_item['text'])

        output_lines.append("")
        output_lines.append("✅ File Management Demo Complete!")

        return {
            "success": True,
            "output": "\n".join(output_lines),
            "session_id": session_id
        }
    except Exception as e:
        error_msg = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        if agentcore_logger:
            agentcore_logger.error(f"Error in file management demo: {error_msg}")

        # Also print to stderr for systemd logging
        print(f"ERROR in file management demo: {error_msg}", file=__import__('sys').stderr)

        return {
            "success": False,
            "error": error_msg
        }


async def execute_shell_command_demo() -> Dict[str, Any]:
    """
    Execute a shell command demonstration showing system information collection

    Returns:
        Dictionary with success status, output, session_id, and error (if any)
    """
    try:
        # Create AgentCore client
        interpreter = AgentCoreCodeInterpreter()

        # Start a new session
        session_id = interpreter.start_session()

        # Store session for later cleanup
        agentcore_sessions[session_id] = interpreter

        output_lines = []

        # Step 1: System Information
        output_lines.append("🖥️  Step 1: Collecting system information...")
        output_lines.append("")

        command_output = interpreter.execute_command(session_id, "uname -a")
        output_lines.append("System: " + command_output)
        output_lines.append("")

        # Step 2: CPU Information
        output_lines.append("⚙️  Step 2: Checking CPU information...")
        output_lines.append("")

        command_output = interpreter.execute_command(
            session_id,
            "cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d':' -f2 | xargs"
        )
        output_lines.append("CPU Model: " + command_output)

        command_output = interpreter.execute_command(
            session_id,
            "nproc"
        )
        output_lines.append("CPU Cores: " + command_output)
        output_lines.append("")

        # Step 3: Memory Information
        output_lines.append("💾 Step 3: Checking memory information...")
        output_lines.append("")

        command_output = interpreter.execute_command(session_id, "free -h")
        output_lines.append(command_output)
        output_lines.append("")

        # Step 4: Disk Usage
        output_lines.append("💿 Step 4: Checking disk usage...")
        output_lines.append("")

        command_output = interpreter.execute_command(session_id, "df -h")
        output_lines.append(command_output)
        output_lines.append("")

        # Step 5: Network Interfaces
        output_lines.append("🌐 Step 5: Checking network interfaces...")
        output_lines.append("")

        command_output = interpreter.execute_command(session_id, "ip addr show | head -20")
        output_lines.append(command_output)
        output_lines.append("")

        # Step 6: Environment Summary
        output_lines.append("📊 Step 6: Environment summary...")
        output_lines.append("")

        command_output = interpreter.execute_command(session_id, "uptime")
        output_lines.append("Uptime: " + command_output)

        command_output = interpreter.execute_command(session_id, "whoami")
        output_lines.append("Current User: " + command_output)

        command_output = interpreter.execute_command(session_id, "pwd")
        output_lines.append("Working Directory: " + command_output)
        output_lines.append("")

        output_lines.append("✅ System Information Collection Complete!")

        return {
            "success": True,
            "output": "\n".join(output_lines),
            "session_id": session_id
        }
    except Exception as e:
        error_msg = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        if agentcore_logger:
            agentcore_logger.error(f"Error in shell command demo: {error_msg}")

        # Also print to stderr for systemd logging
        print(f"ERROR in shell command demo: {error_msg}", file=__import__('sys').stderr)

        return {
            "success": False,
            "error": error_msg
        }


async def reset_agentcore_sessions() -> Dict[str, Any]:
    """
    Reset AgentCore sessions by stopping all active sessions

    Returns:
        Dictionary with success status, message, and error (if any)
    """
    try:
        # Stop all active sessions
        stopped_sessions = []

        for session_id, interpreter in agentcore_sessions.items():
            if interpreter.stop_session(session_id):
                stopped_sessions.append(session_id)

        # Clear the sessions dictionary
        agentcore_sessions.clear()

        return {
            "success": True,
            "message": f"Reset completed. Stopped {len(stopped_sessions)} sessions."
        }
    except Exception as e:
        if agentcore_logger:
            agentcore_logger.error(f"Error resetting AgentCore sessions: {str(e)}")

        return {
            "success": False,
            "error": str(e)
        }


def get_active_sessions() -> Dict[str, Any]:
    """
    Get information about active AgentCore sessions
    
    Returns:
        Dictionary with session information
    """
    session_info = {}
    for session_id, interpreter in agentcore_sessions.items():
        session_info[session_id] = {
            "session_id": session_id,
            "region": interpreter.region,
            "created_at": datetime.now().isoformat()  # This would be better tracked in a session object
        }
    
    return {
        "total_sessions": len(agentcore_sessions),
        "sessions": session_info
    }


def init_agentcore_code_interpreter_vars(app_logger):
    """Initialize shared variables from app.py"""
    global agentcore_logger
    agentcore_logger = app_logger
