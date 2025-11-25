# AgentCore Runtime 文档

本目录包含 AgentCore Runtime 模块的完整技术文档。

---

## 📚 文档结构

### [01-功能概述.md](./01-功能概述.md)
**内容**: AgentCore Runtime 的功能介绍、核心特性、应用场景
**适合**: 初次了解、产品决策、架构设计

**章节**:
- 简介和核心价值
- 核心特性
- 部署方式详解 (Direct Code vs Container)
- 应用场景示例
- 技术优势
- 架构概览

---

### [02-设计实现.md](./02-设计实现.md)
**内容**: 技术架构、模块设计、API 设计、数据流
**适合**: 开发人员、技术实现、代码贡献

**章节**:
- 整体架构
- 后端模块设计 (agentcore_runtime_api.py)
- 前端模块设计 (HTML/JavaScript)
- 会话管理
- API 设计
- 数据流

---

### [03-运行步骤指南.md](./03-运行步骤指南.md)
**内容**: 详细的操作步骤、UI 使用说明、常见问题
**适合**: 用户使用、功能测试、问题排查

**章节**:
- Direct Code Deployment 完整步骤 (Part 1-8)
- Container Deployment 完整步骤 (Part 1-10)
- 常见问题 Q&A
- 最佳实践

---

### [04-快速参考.md](./04-快速参考.md)
**内容**: 速查表、常用命令、配置模板
**适合**: 快速查询、日常开发、故障排查

**章节**:
- 环境变量配置
- API 端点速查表
- 常用命令集合
- Runtime 状态说明
- 故障排查清单
- IAM 权限模板
- 性能基准和成本估算

---

## 🚀 快速开始

### 第一次使用?

**推荐阅读顺序**:
1. [01-功能概述.md](./01-功能概述.md) - 了解功能和架构
2. [03-运行步骤指南.md](./03-运行步骤指南.md) - 按步骤操作
3. [04-快速参考.md](./04-快速参考.md) - 遇到问题查询

### 开发人员?

**推荐阅读顺序**:
1. [02-设计实现.md](./02-设计实现.md) - 理解架构和设计
2. [04-快速参考.md](./04-快速参考.md) - 查看 API 和命令
3. 查看源码: `agentcore_runtime_api.py`, `static/js/runtime*.js`

### 遇到问题?

**问题排查流程**:
1. [04-快速参考.md](./04-快速参考.md#故障排查清单) - 查看故障排查清单
2. [03-运行步骤指南.md](./03-运行步骤指南.md#常见问题) - 查看常见问题 Q&A
3. 查看项目根目录的 `TROUBLESHOOTING_CONTAINER_INVOKE.md`

---

## 📖 相关文档

### 项目主文档
- [CLAUDE.md](../../CLAUDE.md) - 项目整体架构和开发指南
- [README.md](../../README.md) - 项目介绍和快速开始

### 开发文档 (原始草稿)
- [.runtime_dev_doc/](../../.runtime_dev_doc/) - 原始开发文档和设计稿
  - `agentcore_runtime.md` - Runtime 技术资料
  - `SETUP_GUIDE.md` - 环境设置指南
  - `design_spec.md` - 设计规格
  - `requirements_spec.md` - 需求规格
  - `container_deployment_design.md` - Container 设计文档
  - `container_deployment_quickref.md` - Container 快速参考
  - `container_deployment_quickstart.md` - Container 快速开始

### AWS 官方文档
- [Amazon Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [Strands Agents](https://docs.strands.ai/)

---

## 🎯 使用场景指引

### 场景 1: 我想快速体验 Runtime 功能
**推荐**:
1. 阅读 [01-功能概述.md](./01-功能概述.md)
2. 按照 [03-运行步骤指南.md](./03-运行步骤指南.md) 的 Direct Code 部分操作
3. 5-10 分钟即可完成体验

### 场景 2: 我想理解 Runtime 的技术实现
**推荐**:
1. 阅读 [02-设计实现.md](./02-设计实现.md)
2. 查看源码:
   - `agentcore_runtime_api.py:1-1000` - 后端实现
   - `templates/agentcore-runtime.html:1-500` - 前端页面
   - `static/js/runtime.js:1-500` - 前端逻辑

### 场景 3: 我想部署自己的 Agent
**推荐**:
1. 确定部署方式 (参考 [01-功能概述.md](./01-功能概述.md) 的对比表)
2. 准备环境 (参考 [04-快速参考.md](./04-快速参考.md) 的环境变量部分)
3. 按照 [03-运行步骤指南.md](./03-运行步骤指南.md) 操作

### 场景 4: 部署失败或调用出错
**推荐**:
1. 查看 [04-快速参考.md](./04-快速参考.md#故障排查清单)
2. 查看 [03-运行步骤指南.md](./03-运行步骤指南.md#常见问题)
3. 运行前置检查: `python scripts/check_runtime_prerequisites.py`
4. 查看 CloudWatch Logs

---

## 💡 技术亮点

### 混合模式设计
- **Mock API**: 快速演示流程,无需实际资源
- **真实 API**: 真实调用 AWS 服务,完整体验
- **SSE 流式输出**: 实时查看部署进度

### 用户体验优化
- **自动填充**: Runtime 信息自动传递到后续步骤
- **状态持久化**: 页面刷新后状态保持
- **代码变量替换**: 动态显示实际配置值

### 架构灵活性
- **模块化**: 前后端解耦,易于扩展
- **双部署方式**: Direct Code 和 Container 并行支持
- **会话隔离**: 多用户独立操作互不干扰

---

## 🔧 开发计划

### 已完成 ✅
- Direct Code Deployment 完整实现
- Container Deployment 完整实现
- SSE 流式日志输出
- 状态持久化和自动填充
- 完整文档体系

### 计划中 🚧
- 多 Runtime 并发管理
- Runtime 性能监控面板
- 成本追踪和优化建议
- 一键部署脚本

---

## 📞 反馈和贡献

### 问题反馈
- 提交 Issue: 描述问题、复现步骤、环境信息
- 参考文档: 先查看故障排查文档

### 贡献代码
- 遵循现有代码风格
- 更新相关文档
- 添加必要的测试

### 文档改进
- 发现错误或不清晰的地方请反馈
- 欢迎补充使用案例和最佳实践

---

## 📊 文档版本

| 版本 | 日期 | 说明 |
|-----|------|------|
| 1.0 | 2025-11 | 初始版本,包含 Direct Code 和 Container 文档 |

---

**文档持续更新中,欢迎反馈和贡献!** 🚀
