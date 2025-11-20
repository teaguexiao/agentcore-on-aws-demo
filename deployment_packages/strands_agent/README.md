# Strands Agent Deployment Package

此目录用于存放预制的 Agent 部署包。

## 文件说明

- `deployment_package.zip`: 预制的部署包，包含 Agent 代码和依赖
- `main.py`: Agent 源代码（仅供参考）

## 使用说明

1. 将准备好的 `deployment_package.zip` 放到此目录
2. 确保 zip 包包含以下内容：
   - Agent 代码（如 main.py）
   - 所有 Python 依赖库
   - 为 ARM64/Linux 平台编译

## 部署包要求

- 平台：`linux/arm64`
- Python 版本：3.13
- 必须包含：
  - `bedrock-agentcore`
  - `strands-agents`
  - Agent 入口文件

## 创建部署包参考

详见项目文档：`.runtime_dev_doc/design_spec.md` 第 6.2 节
