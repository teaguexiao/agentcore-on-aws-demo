# Runtime 模块实现计划

> 版本: v1.0
> 日期: 2025-01-14

## 1. 实现概述

本文档定义 Runtime 模块迭代的分阶段实现计划。

### 1.1 涉及文件

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `agentcore_runtime_api.py` | 修改 | 新增 API 端点，添加登录验证 |
| `templates/agentcore-runtime.html` | 修改 | 新增工作环境状态栏，改造步骤 UI |
| `static/js/runtime.js` | 修改 | 新增工作空间管理，命令执行逻辑 |
| `static/css/runtime.css` | 新增 | 新增样式文件 |
| `app.py` | 修改 | 导入 get_current_user 供 runtime 模块使用 |

### 1.2 依赖关系

```
Phase 1 (后端基础) ──► Phase 2 (前端基础) ──► Phase 3 (命令执行) ──► Phase 4 (整合测试)
```

---

## 2. 分阶段实现

### Phase 1: 后端基础设施

**目标**: 实现工作空间管理的后端 API

**任务清单**:

- [ ] 1.1 添加数据模型和全局存储
  - 在 `agentcore_runtime_api.py` 中添加 `WorkspaceInfo` dataclass
  - 添加 `user_workspaces` 全局字典
  - 添加常量定义 (`WORKSPACE_BASE_PATH` 等)

- [ ] 1.2 实现工作空间初始化 API
  - `POST /api/runtime/workspace/init`
  - 生成唯一 workspace_id
  - 创建目录
  - 关联用户 session_id

- [ ] 1.3 实现工作空间状态查询 API
  - `GET /api/runtime/workspace/status`
  - 返回当前用户的工作空间状态

- [ ] 1.4 实现工作空间清理 API
  - `POST /api/runtime/workspace/cleanup`
  - 检查是否有 Runtime
  - 删除目录

- [ ] 1.5 添加登录验证
  - 为所有现有 runtime API 端点添加 `Depends(get_current_user)`
  - 从 `app.py` 导入或复制 `get_current_user` 函数

**验收标准**:
- 可以通过 curl 测试所有工作空间 API
- 未登录时返回 401

---

### Phase 2: 前端基础设施

**目标**: 实现工作环境状态栏和基础交互

**任务清单**:

- [ ] 2.1 创建 CSS 样式文件
  - 创建 `static/css/runtime.css`
  - 添加工作环境状态栏样式
  - 添加命令编辑器、输出区、文件树样式

- [ ] 2.2 修改 HTML 模板
  - 在 `templates/agentcore-runtime.html` 中添加工作环境状态栏
  - 引入新 CSS 文件

- [ ] 2.3 实现 WorkspaceState 管理
  - 在 `static/js/runtime.js` 中添加 `WorkspaceState` 对象
  - 实现 `load()` 和 `updateUI()` 方法

- [ ] 2.4 实现工作空间按钮交互
  - 实现 `initWorkspace()` 函数
  - 实现 `cleanupWorkspace()` 函数
  - 绑定按钮事件

**验收标准**:
- 页面加载时显示工作空间状态
- 可以点击按钮初始化/清理工作空间
- 状态栏 UI 正确更新

---

### Phase 3: 命令执行功能

**目标**: 实现真实命令执行和文件写入

**任务清单**:

- [ ] 3.1 实现命令执行 API (SSE)
  - `GET /api/runtime/workspace/execute`
  - 异步执行命令
  - 流式返回 stdout/stderr
  - 心跳机制
  - 返回文件树

- [ ] 3.2 实现文件写入 API
  - `POST /api/runtime/workspace/write-file`
  - 路径安全检查
  - 创建父目录
  - 写入文件
  - 返回文件树

- [ ] 3.3 实现文件树查询 API
  - `GET /api/runtime/workspace/files`
  - 递归扫描目录
  - 限制深度和文件数

- [ ] 3.4 修改 Part 2 前端
  - 添加命令编辑区
  - 添加输出区
  - 添加文件树区
  - 实现 SSE 连接和输出显示

- [ ] 3.5 修改 Part 3 前端
  - 添加文件路径输入
  - 添加代码编辑区
  - 实现文件写入交互

- [ ] 3.6 修改 Part 5-1 前端
  - 添加命令编辑区
  - 复用 Part 2 的 SSE 逻辑

**验收标准**:
- 可以在 Part 2 执行命令并看到实时输出
- 可以在 Part 3 写入代码文件
- 可以在 Part 5-1 执行打包命令
- 每步执行后显示文件树

---

### Phase 4: 整合与优化

**目标**: 整合所有功能，完善细节

**任务清单**:

- [ ] 4.1 Runtime 关联
  - 在 `step5-deploy-stream` 成功后更新 workspace.runtime_id
  - 在 `step8-cleanup` 成功后清除 workspace.runtime_id

- [ ] 4.2 部署包路径集成
  - Part 5-2 部署时使用工作空间中的 deployment_package.zip
  - 修改 `step5_deploy_runtime_stream` 读取工作空间路径

- [ ] 4.3 错误处理完善
  - 添加 Toast 通知组件
  - 统一错误消息显示

- [ ] 4.4 UI 细节优化
  - 按钮状态管理（禁用/启用）
  - 加载动画
  - 响应式适配

- [ ] 4.5 测试
  - 完整流程测试
  - 边界情况测试
  - 多用户并发测试

**验收标准**:
- 完整流程可以从 Part 0 走到 Part 8
- 部署使用的是工作空间中的文件
- 清理工作空间前必须先清理 Runtime

---

## 3. 代码修改详情

### 3.1 agentcore_runtime_api.py

```python
# 新增导入
import secrets
import shutil
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, List

# 从 app.py 导入（或复制）
# from app import get_current_user, sessions

# ========== 新增数据模型 ==========

WORKSPACE_BASE_PATH = "/tmp/agentcore_workspaces"
SSE_HEARTBEAT_INTERVAL = 15
FILE_TREE_MAX_DEPTH = 5
FILE_TREE_MAX_FILES = 100

@dataclass
class WorkspaceInfo:
    workspace_id: str
    user_session_id: str
    workspace_path: str
    created_at: float = field(default_factory=time.time)
    runtime_id: Optional[str] = None

user_workspaces: Dict[str, WorkspaceInfo] = {}

# ========== 新增 API 端点 ==========

@runtime_router.post("/workspace/init")
async def init_workspace(request: Request, user: dict = Depends(get_current_user)):
    # ... 实现见 api_design.md

@runtime_router.get("/workspace/status")
async def get_workspace_status(request: Request, user: dict = Depends(get_current_user)):
    # ... 实现见 api_design.md

@runtime_router.post("/workspace/cleanup")
async def cleanup_workspace(request: Request, user: dict = Depends(get_current_user)):
    # ... 实现见 api_design.md

@runtime_router.get("/workspace/execute")
async def execute_command_stream(request: Request, command: str, user: dict = Depends(get_current_user)):
    # ... 实现见 api_design.md

@runtime_router.post("/workspace/write-file")
async def write_file(request: Request, body: WriteFileRequest, user: dict = Depends(get_current_user)):
    # ... 实现见 api_design.md

@runtime_router.get("/workspace/files")
async def get_files(request: Request, user: dict = Depends(get_current_user)):
    # ... 实现见 api_design.md

# ========== 修改现有端点（添加登录验证）==========

# 在所有现有端点添加: user: dict = Depends(get_current_user)
```

### 3.2 templates/agentcore-runtime.html

```html
<!-- 在 Tab 内容开始处添加工作环境状态栏 -->
<div class="tab-content">
    <!-- Direct Code Deployment Tab -->
    <div class="tab-pane fade show active" id="direct-code">

        <!-- 新增：工作环境状态栏 -->
        {% include 'partials/runtime-workspace-status.html' %}

        <!-- Part 1 保持不变 -->

        <!-- Part 2 改造 -->
        {% include 'partials/runtime-part2-execute.html' %}

        <!-- Part 3 改造 -->
        {% include 'partials/runtime-part3-code.html' %}

        <!-- Part 4 保持不变 -->

        <!-- Part 5-1 改造 -->
        {% include 'partials/runtime-part5-1-package.html' %}

        <!-- Part 5-2 ~ Part 8 保持不变 -->
    </div>
</div>

<!-- 引入新 CSS -->
<link rel="stylesheet" href="/static/css/runtime.css">
```

### 3.3 static/js/runtime.js

```javascript
// 在文件开头添加 WorkspaceState
const WorkspaceState = {
    // ... 实现见 frontend_design.md
};

// 添加工作空间操作函数
async function initWorkspace() { ... }
async function cleanupWorkspace() { ... }

// 添加命令执行函数
function executeCommand(partId, command) { ... }

// 添加文件写入函数
async function writeFile(partId) { ... }

// 添加文件树渲染函数
function renderFileTree(container, files) { ... }

// 修改 DOMContentLoaded 事件
document.addEventListener('DOMContentLoaded', function() {
    // 加载工作空间状态
    WorkspaceState.load();

    // 绑定新按钮事件
    // ...

    // 现有初始化代码...
});
```

---

## 4. 测试计划

### 4.1 单元测试

| 测试项 | 预期结果 |
|-------|---------|
| 初始化工作空间 | 创建目录，返回 workspace_id |
| 重复初始化 | 返回错误，提示已存在 |
| 查询状态（已初始化） | 返回 initialized=true |
| 查询状态（未初始化） | 返回 initialized=false |
| 清理工作空间 | 删除目录，清除状态 |
| 清理时存在 Runtime | 返回错误，提示先清理 Runtime |
| 执行命令 | SSE 返回 stdout/stderr |
| 写入文件 | 文件创建成功 |
| 路径穿越攻击 | 返回错误"非法文件路径" |

### 4.2 集成测试

| 测试场景 | 步骤 |
|---------|------|
| 完整部署流程 | Part 0 → Part 2 → Part 3 → Part 5-1 → Part 5-2 → Part 6 → Part 7 → Part 8 → 清理 |
| 多用户隔离 | 两个用户同时使用，工作空间独立 |
| 页面刷新恢复 | 刷新页面后，工作空间状态正确恢复 |
| 断线重连 | SSE 断开后重新执行命令 |

### 4.3 边界测试

| 测试项 | 预期结果 |
|-------|---------|
| 超长命令 | 正常执行或返回合理错误 |
| 大文件写入 | 正常写入 |
| 深层目录 | 文件树限制深度 |
| 大量文件 | 文件树限制数量 |

---

## 5. 回滚计划

如果新功能出现严重问题，可以快速回滚：

1. **代码回滚**: `git revert` 相关提交
2. **功能开关**: 可以在配置中添加 `ENABLE_REAL_EXECUTION=false` 开关，回退到 Mock 模式
3. **数据清理**: 删除 `/tmp/agentcore_workspaces/` 目录

---

## 6. 后续迭代

本次迭代完成后，可考虑的后续功能：

1. **文件在线编辑**: 支持修改已存在的文件
2. **文件下载**: 支持下载工作目录中的文件
3. **命令历史**: 记录用户执行过的命令
4. **模板保存**: 用户可以保存自定义的命令/代码模板
5. **Container Deployment 改造**: 将同样的模式应用到 Container 部署流程
