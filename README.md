# AgentCore on AWS Demo

A comprehensive web application demonstrating Amazon Bedrock AgentCore capabilities for building AI-powered applications. This project showcases browser automation, code interpretation, and other AgentCore platform services in a secure, production-ready web interface powered by Claude models.

## 🌟 Key Features

- **🤖 Amazon Bedrock AgentCore Integration**: Built entirely on AWS managed services
- **🔒 Enhanced Security**: Complete isolation with AWS-managed sandboxes
- **📈 Scalable Infrastructure**: AWS-backed infrastructure that handles multiple concurrent users
- **⚡ Production Ready**: Enterprise-grade reliability and performance
- **💰 Cost Efficient**: Serverless architecture with pay-per-use model
- **🌐 Real-time Monitoring**: WebSocket-based live updates and comprehensive logging
- **🎯 Multiple Services**: Browser automation, code execution, memory, and gateway features

## ✨ Features

### Current Features

The web application provides an intuitive interface for accessing AgentCore capabilities:

1. **🏠 Home** - Main dashboard with overview and quick start guide

2. **🌐 Browser Automation** - AI-powered browser automation using AgentCore BrowserTool:
   - Live browser viewing with real-time interaction
   - Natural language browser control
   - Automated web research and data extraction
   - Built-in safety and monitoring

3. **💻 Code Interpreter** - Secure Python code execution via AgentCore:
   - Isolated execution environment
   - Session management and persistence
   - Support for data science libraries (numpy, pandas, matplotlib, etc.)
   - Real-time output streaming

4. **🧠 AgentCore Memory** - Persistent knowledge management with interactive demonstrations:
   - **Short-term Memory (STM)**: Session-based conversational memory
   - **Long-term Memory (LTM)**: Cross-session semantic memory with intelligent extraction
   - **Combined Mode**: Best practice integration of STM + LTM
   - Real-time streaming execution with code examples
   - Interactive web UI with live demonstrations
   - Memory resource management and monitoring

### Roadmap Features

The following AgentCore platform services are planned for future releases:

- **🔗 AgentCore Gateway** - Transform existing APIs into agent-compatible tools
- **⚙️ AgentCore Runtime** - Deploy and scale agents with managed infrastructure

## 📦 Prerequisites

### Required Services

1. **AWS Account** with access to:
   - Amazon Bedrock (Claude Sonnet 3.7/4 models)
   - Amazon Bedrock AgentCore
   - IAM for role management

2. **Python 3.11+** installed on your system

### AWS Setup

#### 1. Enable Amazon Bedrock Model Access

1. Navigate to the [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Go to **Model access** in the left sidebar
3. Request access to the following models:
   - **Claude 3.7 Sonnet** (`us.anthropic.claude-3-7-sonnet-20250219-v1:0`)
   - **Claude 4 Sonnet** (if available in your region)
4. Wait for approval (usually instant for most regions)

**Supported Regions:**
- `us-west-2` (Oregon) - Recommended
- `us-east-1` (N. Virginia)

#### 2. Enable Amazon Bedrock AgentCore

1. In the Bedrock Console, navigate to **AgentCore**
2. Enable AgentCore services for your account
3. Note the AgentCore endpoint URL for your region

#### 3. Configure IAM Permissions

Create an IAM role or user with the following permissions:

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
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:*"
      ],
      "Resource": "*"
    }
  ]
}
```

Or attach these managed policies:
- `AmazonBedrockFullAccess`
- Custom policy for AgentCore access (as shown above)

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
pip install -r requirements.txt
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root directory:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-west-2

# Bedrock Configuration
MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0

# AgentCore Configuration
AGENTCORE_ENDPOINT=https://bedrock-agentcore.us-west-2.amazonaws.com

# Session Configuration
SESSION_TIMEOUT_SECONDS=1200
TIMEOUT=1200

# Optional: Authentication (set to "false" to disable login)
LOGIN_ENABLE=true
LOGIN_USERNAME=admin
LOGIN_PASSWORD=your_secure_password
```

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `AWS_DEFAULT_REGION` | AWS region | `us-west-2` |
| `MODEL_ID` | Bedrock model ID | Claude 3.7 Sonnet |
| `AGENTCORE_ENDPOINT` | AgentCore endpoint URL | Region-specific |
| `SESSION_TIMEOUT_SECONDS` | Session timeout | `1200` (20 min) |
| `LOGIN_ENABLE` | Enable authentication | `true` |

## 🎯 Usage

### Starting the Application

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the application
python app.py
```

The application will start on `http://localhost:8090` by default.

### Accessing the Web Interface

1. Open your browser and navigate to `http://localhost:8090`
2. Log in with your credentials (if authentication is enabled)
3. Navigate through the tabs to access different features

### Using Browser Automation

**AgentCore BrowserTool**

1. Navigate to **Browser Use** → **AgentCore BrowserTool** tab
2. Click **Start Browser Session** to initialize a browser instance
3. Enter your browser automation task in the prompt field:
   ```
   Example: "Search for the latest AWS news and summarize the top 3 articles"
   ```
4. Click **Run Browser Task**
5. Watch the AI interact with the browser in real-time via the embedded viewer
6. View detailed execution logs and results

**Example Prompts:**
- "Find the top-rated Python books on Amazon and compare prices"
- "Research the latest developments in quantum computing"
- "Browse GitHub for trending AI/ML repositories this week"
- "Navigate to Wikipedia and summarize the article on neural networks"

### Using Code Interpreter

**AgentCore Code Interpreter**

1. Navigate to **Code Interpreter** → **AgentCore** tab
2. Enter your Python code in the editor
3. Click **Execute Code**
4. View execution results with session information

**Example Code:**

```python
import numpy as np
import matplotlib.pyplot as plt

# Generate sample data
x = np.linspace(0, 2*np.pi, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Create visualization
plt.figure(figsize=(12, 6))
plt.plot(x, y1, label='sin(x)', linewidth=2)
plt.plot(x, y2, label='cos(x)', linewidth=2)
plt.title('Trigonometric Functions')
plt.xlabel('X')
plt.ylabel('Y')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('trig_functions.png', dpi=300, bbox_inches='tight')
print("✓ Visualization saved successfully!")
```

**Supported Libraries:**
- Data Science: `numpy`, `pandas`, `scipy`, `scikit-learn`
- Visualization: `matplotlib`, `seaborn`, `plotly`
- General: Standard Python library

### Using AgentCore Memory

**Interactive Memory Demonstrations**

1. Navigate to **AgentCore Memory** tab
2. Choose from three demonstration modes:

**Demo 1: Short-term Memory (STM)**
- Step 1: Introduce yourself with personal information
- Step 2: Ask questions about the information you just provided
- STM stores raw conversation turns within the current session
- Perfect for maintaining conversation context

**Demo 2: Long-term Memory (LTM)**
- Step 1: Express your preferences or important information
- Wait 10-15 seconds for LTM to asynchronously extract semantic information
- Step 2: Start a new session and ask related questions
- LTM retrieves relevant information across different sessions
- Ideal for building user profiles and preferences

**Demo 3: Combined Mode (Best Practice)**
- Combines STM for conversation continuity + LTM for long-term knowledge
- Demonstrates production-ready memory architecture
- Shows how to build context-aware, personalized AI assistants

**Features:**
- Real-time streaming execution logs
- Live code examples showing actual implementation
- Memory resource management (create, list, view records)
- Visual architecture diagrams for STM and LTM workflows
- Interactive demonstrations with immediate feedback

**Setup Requirements:**
```bash
# Memory IDs will be created automatically on first use
# Or set environment variables for existing memories:
export STM_MEMORY_ID=your-stm-memory-id
export LTM_MEMORY_ID=your-ltm-memory-id
```

### Session Management

- **Browser Sessions**: Automatically managed with 20-minute timeout
- **Code Sessions**: Persistent across executions within the same session
- **Session Status**: View active sessions via the `/api/sessions/status` endpoint

## 🏗️ Project Structure

```
agentcore-on-aws-demo/
├── app.py                          # Main FastAPI application
├── agentcore_browser_tool.py       # Browser automation integration
├── agentcore_code_interpreter.py   # Code interpreter integration
├── agentcore_memory_api.py         # Memory API backend module
├── requirements.txt                # Python dependencies
├── .env                           # Environment configuration (create this)
├── templates/                     # HTML templates
│   ├── index.html                 # Home page
│   ├── login.html                 # Login page
│   ├── browser-use-agentcore.html # Browser automation UI
│   ├── code-interpreter-agentcore.html # Code interpreter UI
│   ├── agentcore-memory.html      # Memory demonstrations UI
│   └── agentcore-*.html          # Other feature templates
├── static/                        # Static assets
│   ├── css/                       # Stylesheets
│   ├── js/                        # JavaScript files
│   └── images/                    # Images and diagrams
│       └── memory/                # Memory architecture diagrams
├── interactive_tools/             # Browser viewer and utilities
├── setup_memory.py                # Memory setup utility script
└── docs/                          # Documentation files
    ├── MEMORY_DEMO_README.md      # Memory demo guide
    ├── MEMORY_ARCHITECTURE.md     # Memory architecture details
    └── STREAMING_RESPONSE_GUIDE.md # Streaming implementation guide
```

## 🔧 Development

### Running Tests

```bash
# Run syntax check
python -m py_compile app.py

# Test dependencies
pip check
```

### Debugging

Enable debug logging in your `.env`:

```bash
LOG_LEVEL=DEBUG
```

View logs in real-time through the web interface or console output.

## 📊 Monitoring

The application provides built-in monitoring:

- **WebSocket Logs**: Real-time execution logs in the web UI
- **Session Status API**: `GET /api/sessions/status` for active session info
- **Health Check**: Application health and status endpoints

## 🔐 Security Considerations

- **Authentication**: Enable login for production deployments
- **API Keys**: Never commit `.env` file with credentials
- **IAM Roles**: Use IAM roles with least privilege principle
- **Network**: Configure appropriate security groups and firewalls
- **HTTPS**: Use reverse proxy (nginx/Apache) with SSL for production

## 🐛 Troubleshooting

### Common Issues

**1. "Module not found" errors**
```bash
pip install -r requirements.txt --force-reinstall
```

**2. AWS credentials not found**
```bash
# Verify .env file exists and contains valid credentials
cat .env | grep AWS_ACCESS_KEY_ID
```

**3. Browser session fails to start**
- Verify AgentCore is enabled in your AWS region
- Check IAM permissions for AgentCore services
- Review CloudWatch logs for detailed error messages

**4. Port already in use**
```bash
# Change port in app.py or kill existing process
lsof -ti:8090 | xargs kill -9
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For questions, issues, or feedback:

- **Issues**: Open an issue on GitHub
- **Documentation**: [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- **AWS Support**: Contact AWS Support for service-related issues

## 🙏 Acknowledgments

Built with:
- [Amazon Bedrock](https://aws.amazon.com/bedrock/) - Foundation models and AI services
- [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) - Agent platform services
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [browser-use](https://github.com/browser-use/browser-use) - Browser automation library

## 🚀 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

---

**Built with ❤️ using Amazon Bedrock AgentCore and FastAPI**

*Last Updated: 2025-11-07*
