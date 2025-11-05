# AgentCore on AWS Demo

A comprehensive web application demonstrating how to leverage multiple sandbox environments on AWS (E2B, AWS Lambda, and AWS EC2) to run AI agents safely and efficiently. This solution showcases browser automation, code interpretation, and desktop automation capabilities powered by Amazon Bedrock's Claude 3.7/4 Sonnet models within secure, isolated containerized sandboxes.

## 🌟 Key Features

- **🔒 Enhanced Security**: Complete isolation prevents AI agents from affecting your local system
- **📈 Scalable Infrastructure**: AWS-backed sandboxes that handle multiple concurrent users
- **⚡ Reliable Performance**: Dedicated compute resources ensure consistent agent execution
- **🎯 Easy Management**: Streamlined sandbox lifecycle management with automated provisioning
- **💰 Cost Efficiency**: Pay-per-use model with automatic resource cleanup
- **🌐 Real-time Monitoring**: WebSocket-based live updates and logging
- **🖥️ Multiple Sandbox Types**: Support for E2B Desktop, AWS Lambda, and EC2 environments

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🏗️ Architecture Overview

The application is built using a modern web stack with FastAPI backend and Bootstrap frontend, integrating multiple AWS services and sandbox environments:

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Application (FastAPI)                 │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Browser    │  │     Code     │  │   Computer   │      │
│  │     Use      │  │  Interpreter │  │     Use      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                    Sandbox Environments                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ E2B Desktop  │  │ AWS Lambda   │  │   AWS EC2    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                    Amazon Bedrock                            │
│              Claude 3.7/4 Sonnet Models                      │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Features

### Frontend Interface

The web application provides an intuitive tabbed interface for accessing different sandbox functionalities:

1. **🏠 Home** - Main dashboard with overview and quick start guide
2. **🔄 Sandbox Lifecycle** - Create, manage, and monitor sandbox instances
3. **🌐 Browser Use** - AI-powered browser automation with two modes:
   - **E2B Desktop**: Traditional E2B sandbox-based browser automation
   - **AgentCore BrowserTool**: Advanced browser automation with live viewing using Amazon Bedrock AgentCore
4. **💻 Code Interpreter** - Execute Python code in isolated environments:
   - **E2B Code Interpreter**: Fast code execution in E2B sandboxes
   - **AgentCore Code Interpreter**: Managed code execution via Amazon Bedrock AgentCore
5. **🖥️ Computer Use** - Desktop automation and computer interaction powered by Claude
6. **🔍 AI Search** - AI-powered search functionality *(Coming Soon)*
7. **📊 AI PPT** - AI-powered presentation generation *(Coming Soon)*

### Core Capabilities

#### Browser Automation
- **Intelligent Web Navigation**: AI-driven browser interactions using natural language prompts
- **Live Browser Viewing**: Real-time browser session monitoring with DCV-based viewer
- **Session Recording**: Capture and replay browser automation sessions
- **Multi-tab Support**: Handle complex workflows across multiple browser tabs
- **Example Tasks**: Google search, Amazon product search, Wikipedia research, GitHub browsing

#### Code Interpretation
- **Python Code Execution**: Run Python code in secure, isolated environments
- **Multiple Backends**: Choose between E2B and AgentCore interpreters
- **Session Management**: Persistent sessions with automatic cleanup
- **Real-time Output**: Stream execution results via WebSocket

#### Computer Use
- **Desktop Automation**: Control virtual desktops programmatically
- **Screenshot Analysis**: AI-powered visual understanding of desktop state
- **Mouse & Keyboard Control**: Automated interactions with desktop applications
- **Multi-step Workflows**: Execute complex desktop automation tasks

## 📦 Prerequisites

### Required Accounts & Services

1. **AWS Account** with access to:
   - Amazon Bedrock (Claude 3.7/4 Sonnet models)
   - IAM for role management
   - Optional: Lambda, EC2 for additional sandbox types

2. **E2B Account**:
   - Sign up at [e2b.dev](https://e2b.dev)
   - Obtain API key and template IDs

3. **Python 3.11+** installed on your system

### AWS Setup

#### 1. Create IAM Role for Bedrock Access

Create an IAM role named `Bedrock-Role` with the following configuration:

**Permissions Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel"
      ],
      "Resource": "*"
    }
  ]
}
```

Alternatively, attach the AWS managed policy: `AmazonBedrockFullAccess`

#### 2. Configure Trust Relationship

Add the following trust policy to your IAM role (replace placeholders with your values):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:user/your_iam_user_name"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Replace:**
- `ACCOUNT_ID` - Your 12-digit AWS account ID
- `your_iam_user_name` - Your IAM user name

#### 3. Enable Bedrock Model Access

1. Navigate to the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Go to **Model access** in the left sidebar
3. Request access to **Claude 3.7 Sonnet** and **Claude 4 Sonnet** models
4. Wait for approval (usually instant for most regions)

**Supported Regions:**
- `us-west-2` (Oregon) - Recommended
- `us-east-1` (N. Virginia)
- Check AWS documentation for latest region availability

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd agentcore-on-aws-demo
```

### 2. Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirement.txt
```

**Key Dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `boto3` - AWS SDK
- `langchain-aws` - LangChain AWS integrations
- `e2b` - E2B sandbox SDK
- `e2b-desktop` - E2B desktop sandbox
- `e2b-code-interpreter` - E2B code interpreter
- `browser-use` - Browser automation library
- `websockets` - WebSocket support

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root directory with the following configuration:

```bash
# E2B Configuration
API_KEY=your_e2b_api_key_here
TEMPLATE=your_e2b_template_id_here
DOMAIN=your_e2b_domain_here

# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-west-2

# Bedrock Configuration
MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0

# Sandbox Configuration
TIMEOUT=1200
CODE_INTERPRETER_TEMPLATE_ID=nlhz8vlwyupq845jsdg9

# Optional: Session Configuration
SESSION_TIMEOUT_SECONDS=1200
```

### Configuration Details

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_KEY` | E2B API key from your E2B account | - | Yes |
| `TEMPLATE` | E2B template ID for desktop sandboxes | - | Yes |
| `DOMAIN` | E2B domain for sandbox access | - | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key for your IAM user | - | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for your IAM user | - | Yes |
| `AWS_DEFAULT_REGION` | AWS region for Bedrock | `us-west-2` | No |
| `MODEL_ID` | Bedrock model identifier | Claude 3.7 Sonnet | No |
| `TIMEOUT` | Sandbox timeout in seconds | `1200` | No |
| `CODE_INTERPRETER_TEMPLATE_ID` | E2B template for code interpreter | - | No |

### Obtaining E2B Credentials

1. Sign up at [e2b.dev](https://e2b.dev)
2. Navigate to your dashboard
3. Create a new API key
4. Create templates for:
   - Desktop sandbox (for browser use)
   - Code interpreter sandbox
5. Copy the template IDs and API key to your `.env` file

## 🎯 Usage

### Starting the Application

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the application
python app.py
```

The application will start on `http://localhost:8000` by default.

### Accessing the Web Interface

1. Open your browser and navigate to `http://localhost:8000`
2. You'll see the main dashboard with navigation tabs
3. Click on any tab to access specific functionality

### Using Browser Automation

#### E2B Desktop Mode

1. Navigate to **Browser Use** → **E2B Desktop** tab
2. Click **Start Desktop** to initialize the sandbox
3. Wait for the desktop stream to load
4. Click **Setup Environment** to install browser dependencies
5. Enter your task in the prompt field (e.g., "Search for Python tutorials on Google")
6. Click **Run Task** to execute
7. Monitor progress in the real-time logs
8. View browser interactions in the desktop stream

#### AgentCore BrowserTool Mode

1. Navigate to **Browser Use** → **AgentCore BrowserTool** tab
2. Enter your browser automation task in the prompt field
3. Click **Run Browser Task**
4. The system will:
   - Start a browser session
   - Launch the live viewer
   - Execute your task using AI
   - Display the browser in an embedded iframe
5. Watch the AI interact with the browser in real-time
6. View detailed logs of all actions

**Example Prompts:**
- "Search for the latest news about AI on Google"
- "Find the top-rated Python books on Amazon"
- "Look up the Wikipedia page for quantum computing"
- "Browse the trending repositories on GitHub"

### Using Code Interpreter

#### E2B Code Interpreter

1. Navigate to **Code Interpreter** → **E2B** tab
2. Enter your Python code in the code editor
3. Click **Execute Code**
4. View the output in the results panel

#### AgentCore Code Interpreter

1. Navigate to **Code Interpreter** → **AgentCore** tab
2. Enter your Python code
3. Click **Execute Code**
4. View execution results with session information

**Example Code:**
```python
import numpy as np
import matplotlib.pyplot as plt

# Generate data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('X')
plt.ylabel('Y')
plt.grid(True)
plt.savefig('sine_wave.png')
print("Plot saved successfully!")
```

### Using Computer Use

1. Navigate to **Computer Use** tab
2. Click **Start Desktop** to initialize the virtual desktop
3. Wait for the desktop to load
4. Enter your automation task (e.g., "Open Firefox and navigate to example.com")
5. Click **Run Task**
6. The AI will:
   - Analyze the desktop screenshot
   - Plan the required actions
   - Execute mouse clicks, keyboard inputs, etc.
   - Provide step-by-step feedback
7. Monitor progress through screenshots and logs

### Managing Sandbox Lifecycle

1. Navigate to **Sandbox Lifecycle** tab
2. View active sandboxes and their status
3. Create new sandboxes with custom configurations
4. Monitor resource usage
5. Terminate sandboxes when no longer needed


## 🔌 API Endpoints

The application exposes several REST and WebSocket endpoints for programmatic access:

### Browser Use Endpoints

#### E2B Desktop Browser

```http
POST /start-desktop
```
Start a new E2B desktop sandbox for browser automation.

**Response:**
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "message": "Desktop started successfully"
}
```

```http
POST /setup-env
```
Install browser dependencies in the sandbox.

**Request Body:**
```json
{
  "session_id": "uuid-string"
}
```

```http
POST /run-task
```
Execute a browser automation task.

**Request Body:**
```json
{
  "query": "Search for Python tutorials",
  "session_id": "uuid-string"
}
```

```http
POST /kill-desktop
```
Terminate the desktop sandbox.

**Request Body:**
```json
{
  "session_id": "uuid-string"
}
```

#### AgentCore BrowserTool

```http
POST /start-agentcore-browser
```
Start an AgentCore browser session with live viewer.

```http
POST /run-agentcore-browser-task
```
Execute browser automation using AgentCore.

**Request Body:**
```json
{
  "prompt": "Find the latest AI news",
  "session_id": "uuid-string"
}
```

```http
POST /stop-agentcore-browser
```
Stop the AgentCore browser session.

### Code Interpreter Endpoints

```http
POST /execute-code
```
Execute Python code in E2B sandbox.

**Request Body:**
```json
{
  "code": "print('Hello, World!')"
}
```

**Response:**
```json
{
  "success": true,
  "output": "Hello, World!",
  "sandbox_id": "sandbox-id"
}
```

```http
POST /execute-agentcore-code
```
Execute Python code using AgentCore.

**Request Body:**
```json
{
  "code": "import numpy as np\nprint(np.array([1,2,3]))"
}
```

### Computer Use Endpoints

```http
POST /start-computer-desktop
```
Start a desktop for computer use automation.

```http
POST /run-computer-task
```
Execute a computer automation task.

**Request Body:**
```json
{
  "task": "Open a text editor and write a poem",
  "session_id": "uuid-string"
}
```

```http
POST /stop-computer-task
```
Stop the current computer automation task.

```http
GET /computer-screenshot
```
Get the current desktop screenshot.

### WebSocket Endpoints

```http
WS /ws/{session_id}
```
WebSocket connection for real-time logs and updates.

**Message Format:**
```json
{
  "type": "info|error|stdout|stderr|screenshot",
  "timestamp": "HH:MM:SS",
  "data": "message content"
}
```

### Session Management

```http
GET /api/sessions/status
```
Get status of all active sessions.

**Response:**
```json
{
  "browser_use_sessions": ["session-1", "session-2"],
  "computer_use_sessions": ["session-3"],
  "agentcore_sessions": ["session-4"]
}
```


## 🔧 Technical Details

### Technology Stack

**Backend:**
- **FastAPI** - Modern, fast web framework for building APIs
- **Uvicorn** - Lightning-fast ASGI server
- **Python 3.11+** - Core programming language
- **asyncio** - Asynchronous I/O for concurrent operations

**Frontend:**
- **Bootstrap 5.3** - Responsive UI framework
- **JavaScript (ES6+)** - Client-side interactivity
- **WebSocket API** - Real-time bidirectional communication
- **Jinja2** - Server-side templating

**AI & ML:**
- **Amazon Bedrock** - Managed AI service
- **Claude 3.7/4 Sonnet** - Advanced language models
- **LangChain** - LLM application framework
- **browser-use** - AI-powered browser automation

**Sandbox Environments:**
- **E2B** - Cloud-based code execution sandboxes
- **AWS Lambda** - Serverless compute
- **AWS EC2** - Virtual machines for desktop automation

**Additional Tools:**
- **DCV (NICE DCV)** - High-performance remote display protocol
- **Playwright** - Browser automation library
- **boto3** - AWS SDK for Python

### Project Structure

```
agentcore-on-aws-demo/
├── app.py                          # Main FastAPI application
├── bedrock.py                      # Bedrock API integration
├── sandbox_desktop.py              # E2B desktop sandbox management
├── sandbox_browser_use.py          # Browser automation with E2B
├── sandbox_computer_use.py         # Computer use automation
├── agentcore_browser_tool.py       # AgentCore browser integration
├── agentcore_code_interpreter.py   # AgentCore code interpreter
├── computer_use.py                 # Computer use agent logic
├── requirement.txt                 # Python dependencies
├── .env                            # Environment configuration
├── templates/                      # HTML templates
│   ├── index.html                  # Home page
│   ├── browser-use.html            # Browser automation UI
│   ├── code-interpreter.html       # Code interpreter UI
│   ├── sandbox-lifecycle.html      # Sandbox management UI
│   └── ...
├── static/                         # Static assets
│   ├── css/
│   │   └── style.css              # Application styles
│   ├── js/
│   │   ├── agentcore-browser.js   # AgentCore browser client
│   │   └── ...
│   ├── images/                     # Image assets
│   └── dcvjs/                      # DCV viewer SDK
├── interactive_tools/              # Additional tools
│   ├── browser_viewer.py           # Browser live viewer
│   ├── dynamic_research_agent_langgraph.py
│   └── ...
└── amazon-bedrock-agentcore-samples/  # Sample code and tutorials
```

### Session Management

The application implements sophisticated session management:

1. **Session Isolation**: Each user session is completely isolated
2. **Automatic Cleanup**: Sessions are automatically terminated after timeout
3. **Resource Management**: Efficient allocation and deallocation of sandbox resources
4. **Concurrent Sessions**: Support for multiple simultaneous users
5. **State Persistence**: Session state maintained across WebSocket reconnections

### Security Considerations

- **Sandbox Isolation**: All code execution happens in isolated containers
- **IAM Role-based Access**: AWS resources accessed via IAM roles
- **Environment Variable Protection**: Sensitive credentials stored in `.env`
- **Session Tokens**: WebSocket connections authenticated with session tokens
- **Resource Limits**: Timeouts and resource quotas prevent abuse
- **HTTPS Support**: SSL/TLS encryption for production deployments

### Performance Optimization

- **Async/Await**: Non-blocking I/O for better concurrency
- **Connection Pooling**: Reuse of HTTP connections to AWS services
- **Lazy Loading**: Resources loaded on-demand
- **Caching**: Strategic caching of static assets
- **Background Tasks**: Long-running operations executed asynchronously

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors

**Problem:** `ModuleNotFoundError` when starting the application

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirement.txt --upgrade
```

#### 2. AWS Credentials Error

**Problem:** `NoCredentialsError` or `AccessDenied` when accessing Bedrock

**Solution:**
- Verify AWS credentials in `.env` file
- Check IAM role trust relationship
- Ensure Bedrock model access is enabled in your region
- Test credentials:
```bash
aws sts get-caller-identity
```

#### 3. E2B Connection Issues

**Problem:** Cannot connect to E2B sandbox

**Solution:**
- Verify E2B API key is correct
- Check template IDs exist in your E2B account
- Ensure sufficient E2B credits
- Test E2B connection:
```python
from e2b import Sandbox
sandbox = Sandbox(api_key="your-key")
print(sandbox.sandbox_id)
```

#### 4. WebSocket Connection Failures

**Problem:** Real-time logs not appearing

**Solution:**
- Check browser console for WebSocket errors
- Verify session ID is valid
- Ensure firewall allows WebSocket connections
- Try refreshing the page

#### 5. Browser Viewer Not Loading

**Problem:** Embedded browser iframe shows blank screen

**Solution:**
- Check if DCV SDK files are present in `static/dcvjs/`
- Verify port availability (8000-8999 range)
- Check browser console for CORS errors
- Ensure viewer server started successfully in logs

#### 6. Sandbox Timeout Issues

**Problem:** Tasks fail with timeout errors

**Solution:**
- Increase `TIMEOUT` value in `.env` (default: 1200 seconds)
- Break complex tasks into smaller steps
- Check sandbox resource limits
- Monitor sandbox logs for performance issues

#### 7. Model Access Denied

**Problem:** `AccessDeniedException` when invoking Bedrock models

**Solution:**
- Request model access in Bedrock console
- Wait for approval (usually instant)
- Verify region supports the model
- Check IAM permissions include `bedrock:InvokeModel`

### Debug Mode

Enable detailed logging for troubleshooting:

```python
# Add to app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Getting Help

If you encounter issues not covered here:

1. Check application logs for detailed error messages
2. Review the [E2B Documentation](https://e2b.dev/docs)
3. Consult [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
4. Open an issue in the repository with:
   - Error message
   - Steps to reproduce
   - Environment details (OS, Python version, etc.)

## 📚 Additional Resources

### Documentation

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/)
- [E2B Documentation](https://e2b.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Claude AI Documentation](https://docs.anthropic.com/)

### Sample Code

The `amazon-bedrock-agentcore-samples/` directory contains:
- Tutorial notebooks and guides
- Real-world use case examples
- Integration samples with various tools
- Best practices and patterns

### Related Projects

- [browser-use](https://github.com/browser-use/browser-use) - AI browser automation library
- [E2B](https://github.com/e2b-dev/e2b) - Cloud sandboxes for AI agents
- [LangChain](https://github.com/langchain-ai/langchain) - LLM application framework
- [Amazon Bedrock Samples](https://github.com/aws-samples/amazon-bedrock-samples)

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/agentcore-on-aws-demo.git
cd agentcore-on-aws-demo

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies including dev tools
pip install -r requirement.txt
pip install pytest black flake8

# Run tests (if available)
pytest

# Format code
black .

# Lint code
flake8 .
```

### Code Style

- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Write unit tests for new features
- Keep functions focused and modular

## 🔄 System Service (Optional)

For production deployments, you can run the application as a systemd service:

### Create Service File

Create `/etc/systemd/system/agentcore.service`:

```ini
[Unit]
Description=AgentCore on AWS Demo
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/agentcore-on-aws-demo
Environment="PATH=/home/ubuntu/agentcore-on-aws-demo/venv/bin"
ExecStart=/home/ubuntu/agentcore-on-aws-demo/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable agentcore

# Start the service
sudo systemctl start agentcore

# Check status
sudo systemctl status agentcore

# View logs
sudo journalctl -u agentcore -f
```

### Restart After Changes

After making changes to Python files:

```bash
sudo systemctl restart agentcore
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Amazon Web Services** for Bedrock and cloud infrastructure
- **E2B** for providing excellent sandbox environments
- **Anthropic** for Claude AI models
- **FastAPI** community for the amazing web framework
- **LangChain** team for the LLM framework
- All contributors and users of this project

## 📞 Support

For questions, issues, or feedback:

- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check the docs in `amazon-bedrock-agentcore-samples/`

## 🚀 Roadmap

Future enhancements planned:

- [ ] AI Search functionality
- [ ] AI-powered presentation generation
- [ ] Multi-user authentication and authorization
- [ ] Session persistence and recovery
- [ ] Advanced monitoring and analytics
- [ ] Docker containerization
- [ ] Kubernetes deployment support
- [ ] Additional sandbox providers
- [ ] Enhanced error handling and recovery
- [ ] Performance optimizations

## 📊 Performance Metrics

Typical performance characteristics:

- **Sandbox Startup**: 5-15 seconds
- **Browser Automation**: 10-60 seconds per task
- **Code Execution**: 1-5 seconds
- **WebSocket Latency**: <100ms
- **Concurrent Users**: 10+ (depends on resources)

## 🔐 Security Best Practices

1. **Never commit `.env` file** to version control
2. **Rotate AWS credentials** regularly
3. **Use IAM roles** instead of access keys when possible
4. **Enable CloudTrail** for AWS API auditing
5. **Monitor sandbox usage** for anomalies
6. **Set resource limits** to prevent abuse
7. **Use HTTPS** in production
8. **Implement rate limiting** for API endpoints

---

**Built with ❤️ using Amazon Bedrock, E2B, and FastAPI**

*Last Updated: 2025-11-05*
