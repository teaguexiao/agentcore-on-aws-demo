# AgentCore on AWS Demo

A comprehensive web application demonstrating how to leverage multiple sandbox environments on AWS (AWS Lambda and AWS EC2) to run AI agents safely and efficiently. This solution showcases browser automation, code interpretation, and desktop automation capabilities powered by Amazon Bedrock's Claude 3.7/4 Sonnet models within secure, isolated containerized sandboxes.

## 🌟 Key Features

- **🔒 Enhanced Security**: Complete isolation prevents AI agents from affecting your local system
- **📈 Scalable Infrastructure**: AWS-backed sandboxes that handle multiple concurrent users
- **⚡ Reliable Performance**: Dedicated compute resources ensure consistent agent execution
- **🎯 Easy Management**: Streamlined sandbox lifecycle management with automated provisioning
- **💰 Cost Efficiency**: Pay-per-use model with automatic resource cleanup
- **🌐 Real-time Monitoring**: WebSocket-based live updates and logging
- **🖥️ Multiple Sandbox Types**: Support for AWS Lambda and EC2 environments

## ✨ Features

### Frontend Interface

The web application provides an intuitive tabbed interface for accessing different sandbox functionalities:

1. **🏠 Home** - Main dashboard with overview and quick start guide
2. **🔄 Sandbox Lifecycle** - Create, manage, and monitor sandbox instances
3. **🌐 Browser Use** - AI-powered browser automation:
   - **AgentCore BrowserTool**: Advanced browser automation with live viewing using Amazon Bedrock AgentCore
4. **💻 Code Interpreter** - Execute Python code in isolated environments:
   - **AgentCore Code Interpreter**: Managed code execution via Amazon Bedrock AgentCore

## 📦 Prerequisites

### Required Accounts & Services

1. **AWS Account** with access to:
   - Amazon Bedrock (Claude 4/4.5 Sonnet models)
   - IAM for role management

2. **Python 3.11+** installed on your system

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

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root directory with the following configuration:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-west-2

# Bedrock Configuration
MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0

# Sandbox Configuration
TIMEOUT=1200

# Optional: Session Configuration
SESSION_TIMEOUT_SECONDS=1200
```

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

### Managing Sandbox Lifecycle

1. Navigate to **Sandbox Lifecycle** tab
2. View active sandboxes and their status
3. Create new sandboxes with custom configurations
4. Monitor resource usage
5. Terminate sandboxes when no longer needed

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Amazon Web Services** for Bedrock and cloud infrastructure
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

- [ ] DeepResearch functionality

---

**Built with ❤️ using Amazon Bedrock and FastAPI**

*Last Updated: 2025-11-05*
