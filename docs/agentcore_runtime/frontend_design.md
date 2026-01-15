# Runtime 模块前端设计文档

> 版本: v1.0
> 日期: 2025-01-14

## 1. 概述

本文档定义 Runtime 模块迭代的前端设计，包括页面布局、组件设计、交互逻辑。

## 2. 页面整体布局

### 2.1 改造后的布局结构

```
┌─────────────────────────────────────────────────────────────────┐
│  Tab: Direct Code Deployment | Container Deployment             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  工作环境状态栏 (新增)                                      │  │
│  │  状态: ● 未初始化 / ● 已初始化 (ws_xxx)                     │  │
│  │  路径: /tmp/agentcore_workspaces/ws_xxx                    │  │
│  │  [初始化工作环境]  [清理工作环境]                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Part 1: 前置要求检查 (保持不变)                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  静态检查清单...                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Part 2: 初始化项目 (改造)                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  命令编辑区 + 执行按钮 + 输出区 + 文件树                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Part 3: 创建 Agent 代码 (改造)                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  文件路径 + 代码编辑区 + 写入按钮 + 文件树                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Part 4: 本地测试 (保持不变)                                    │
│  Part 5-1: 创建部署包 (改造)                                    │
│  Part 5-2 ~ Part 8: (保持不变)                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3. 组件设计

### 3.1 工作环境状态栏

**HTML 结构**:

```html
<div class="workspace-status-bar card mb-4">
    <div class="card-body">
        <div class="d-flex justify-content-between align-items-center">
            <div class="workspace-info">
                <h5 class="mb-1">
                    <span class="status-indicator" id="workspace-status-dot"></span>
                    工作环境状态:
                    <span id="workspace-status-text">未初始化</span>
                </h5>
                <p class="mb-0 text-muted" id="workspace-path-text" style="display: none;">
                    路径: <code id="workspace-path"></code>
                </p>
            </div>
            <div class="workspace-actions">
                <button class="btn btn-primary me-2" id="btn-init-workspace">
                    <i class="bi bi-folder-plus"></i> 初始化工作环境
                </button>
                <button class="btn btn-outline-danger" id="btn-cleanup-workspace" disabled>
                    <i class="bi bi-trash"></i> 清理工作环境
                </button>
            </div>
        </div>
        <!-- 安全警告 -->
        <div class="alert alert-warning mt-3 mb-0" id="security-warning" style="display: none;">
            <i class="bi bi-exclamation-triangle"></i>
            <strong>安全提示:</strong> 命令将在服务器上真实执行，请确保命令安全。
        </div>
    </div>
</div>
```

**CSS 样式**:

```css
.workspace-status-bar {
    border-left: 4px solid #6c757d;
}

.workspace-status-bar.initialized {
    border-left-color: #28a745;
}

.status-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background-color: #6c757d;
    margin-right: 8px;
}

.workspace-status-bar.initialized .status-indicator {
    background-color: #28a745;
}
```

---

### 3.2 命令执行步骤卡片 (Part 2, Part 5-1)

**HTML 结构**:

```html
<div class="runtime-part card mb-4" id="part-2">
    <div class="card-header">
        <h5 class="mb-0">Part 2: 初始化项目</h5>
    </div>
    <div class="card-body">
        <!-- 命令编辑区 -->
        <div class="mb-3">
            <label class="form-label">Shell 命令:</label>
            <textarea class="form-control command-editor" id="part2-command" rows="4">uv init agentcore_runtime_direct_deploy
cd agentcore_runtime_direct_deploy
uv add bedrock-agentcore strands-agents</textarea>
            <small class="text-muted">每行一条命令，将按顺序执行</small>
        </div>

        <!-- 执行按钮 -->
        <div class="mb-3">
            <button class="btn btn-primary" id="btn-execute-part2" disabled>
                <i class="bi bi-play-fill"></i> 执行
            </button>
            <span class="ms-2 text-muted" id="part2-status"></span>
        </div>

        <!-- 输出区 -->
        <div class="output-section" id="part2-output-section" style="display: none;">
            <label class="form-label">输出:</label>
            <div class="output-log" id="part2-output">
                <!-- 动态填充 stdout/stderr -->
            </div>
        </div>

        <!-- 文件树区 -->
        <div class="file-tree-section mt-3" id="part2-files-section" style="display: none;">
            <label class="form-label">
                <i class="bi bi-folder2-open"></i> 当前目录文件:
            </label>
            <div class="file-tree" id="part2-files">
                <!-- 动态填充文件树 -->
            </div>
        </div>
    </div>
</div>
```

**CSS 样式**:

```css
.command-editor {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 13px;
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
}

.output-log {
    max-height: 300px;
    overflow-y: auto;
    background-color: #1e1e1e;
    color: #d4d4d4;
    padding: 12px;
    border-radius: 4px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 12px;
}

.output-log .stdout {
    color: #d4d4d4;
}

.output-log .stderr {
    color: #f48771;
}

.file-tree {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 12px;
    max-height: 200px;
    overflow-y: auto;
}

.file-tree-item {
    display: flex;
    align-items: center;
    padding: 2px 0;
}

.file-tree-item.directory {
    font-weight: 500;
}

.file-tree-item .icon {
    margin-right: 6px;
    color: #6c757d;
}

.file-tree-item.directory .icon {
    color: #ffc107;
}

.file-tree-item .size {
    margin-left: auto;
    color: #6c757d;
    font-size: 11px;
}

.file-tree-children {
    margin-left: 20px;
}
```

---

### 3.3 代码编辑步骤卡片 (Part 3)

**HTML 结构**:

```html
<div class="runtime-part card mb-4" id="part-3">
    <div class="card-header">
        <h5 class="mb-0">Part 3: 创建 Agent 代码</h5>
    </div>
    <div class="card-body">
        <!-- 文件路径 -->
        <div class="mb-3">
            <label class="form-label">文件路径:</label>
            <input type="text" class="form-control" id="part3-filepath"
                   value="agentcore_runtime_direct_deploy/main.py">
        </div>

        <!-- 代码编辑区 -->
        <div class="mb-3">
            <label class="form-label">代码内容:</label>
            <textarea class="form-control code-editor" id="part3-code" rows="20">from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload, context):
    prompt = payload.get("prompt", "Hello")
    # Agent 逻辑...
    return {"response": f"You said: {prompt}"}</textarea>
        </div>

        <!-- 写入按钮 -->
        <div class="mb-3">
            <button class="btn btn-primary" id="btn-write-part3" disabled>
                <i class="bi bi-save"></i> 写入文件
            </button>
            <span class="ms-2 text-muted" id="part3-status"></span>
        </div>

        <!-- 文件树区 -->
        <div class="file-tree-section mt-3" id="part3-files-section" style="display: none;">
            <label class="form-label">
                <i class="bi bi-folder2-open"></i> 当前目录文件:
            </label>
            <div class="file-tree" id="part3-files">
                <!-- 动态填充文件树 -->
            </div>
        </div>
    </div>
</div>
```

**CSS 样式**:

```css
.code-editor {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 13px;
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    line-height: 1.5;
}
```

---

## 4. JavaScript 逻辑设计

### 4.1 状态管理

```javascript
// runtime.js 中添加

const WorkspaceState = {
    initialized: false,
    workspace_id: null,
    workspace_path: null,
    runtime_id: null,

    // 从后端加载状态
    async load() {
        try {
            const response = await fetch('/api/runtime/workspace/status');
            const data = await response.json();
            this.initialized = data.initialized;
            this.workspace_id = data.workspace_id;
            this.workspace_path = data.workspace_path;
            this.runtime_id = data.runtime_id;
            this.updateUI();
        } catch (error) {
            console.error('Failed to load workspace status:', error);
        }
    },

    // 更新 UI
    updateUI() {
        const statusBar = document.querySelector('.workspace-status-bar');
        const statusText = document.getElementById('workspace-status-text');
        const pathText = document.getElementById('workspace-path-text');
        const pathValue = document.getElementById('workspace-path');
        const btnInit = document.getElementById('btn-init-workspace');
        const btnCleanup = document.getElementById('btn-cleanup-workspace');
        const securityWarning = document.getElementById('security-warning');

        if (this.initialized) {
            statusBar.classList.add('initialized');
            statusText.textContent = `已初始化 (${this.workspace_id})`;
            pathText.style.display = 'block';
            pathValue.textContent = this.workspace_path;
            btnInit.disabled = true;
            btnCleanup.disabled = false;
            securityWarning.style.display = 'block';

            // 启用命令执行按钮
            this.enableExecuteButtons(true);
        } else {
            statusBar.classList.remove('initialized');
            statusText.textContent = '未初始化';
            pathText.style.display = 'none';
            btnInit.disabled = false;
            btnCleanup.disabled = true;
            securityWarning.style.display = 'none';

            // 禁用命令执行按钮
            this.enableExecuteButtons(false);
        }
    },

    enableExecuteButtons(enabled) {
        document.getElementById('btn-execute-part2').disabled = !enabled;
        document.getElementById('btn-write-part3').disabled = !enabled;
        document.getElementById('btn-execute-part5-1').disabled = !enabled;
    }
};
```

---

### 4.2 工作空间操作

```javascript
// 初始化工作空间
async function initWorkspace() {
    const btn = document.getElementById('btn-init-workspace');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 初始化中...';

    try {
        const response = await fetch('/api/runtime/workspace/init', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            WorkspaceState.initialized = true;
            WorkspaceState.workspace_id = data.workspace_id;
            WorkspaceState.workspace_path = data.workspace_path;
            WorkspaceState.updateUI();
            showToast('成功', '工作环境初始化成功', 'success');
        } else {
            showToast('失败', data.message, 'error');
        }
    } catch (error) {
        showToast('错误', '初始化失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-folder-plus"></i> 初始化工作环境';
    }
}

// 清理工作空间
async function cleanupWorkspace() {
    // 确认对话框
    if (!confirm('确定要清理工作环境吗？这将删除所有文件。')) {
        return;
    }

    const btn = document.getElementById('btn-cleanup-workspace');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 清理中...';

    try {
        const response = await fetch('/api/runtime/workspace/cleanup', {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            WorkspaceState.initialized = false;
            WorkspaceState.workspace_id = null;
            WorkspaceState.workspace_path = null;
            WorkspaceState.updateUI();
            clearAllOutputs();
            showToast('成功', '工作环境已清理', 'success');
        } else {
            showToast('失败', data.message, 'error');
        }
    } catch (error) {
        showToast('错误', '清理失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-trash"></i> 清理工作环境';
    }
}
```

---

### 4.3 命令执行 (SSE)

```javascript
// 执行命令并流式显示输出
function executeCommand(partId, command) {
    const outputSection = document.getElementById(`${partId}-output-section`);
    const outputLog = document.getElementById(`${partId}-output`);
    const filesSection = document.getElementById(`${partId}-files-section`);
    const filesTree = document.getElementById(`${partId}-files`);
    const statusSpan = document.getElementById(`${partId}-status`);
    const btn = document.getElementById(`btn-execute-${partId}`);

    // 显示输出区，清空旧内容
    outputSection.style.display = 'block';
    outputLog.innerHTML = '';
    filesSection.style.display = 'none';

    // 禁用按钮
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 执行中...';
    statusSpan.textContent = '执行中...';

    // 建立 SSE 连接
    const encodedCommand = encodeURIComponent(command);
    const eventSource = new EventSource(`/api/runtime/workspace/execute?command=${encodedCommand}`);

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'stdout':
                appendLogLine(outputLog, data.line, 'stdout');
                break;

            case 'stderr':
                appendLogLine(outputLog, data.line, 'stderr');
                break;

            case 'heartbeat':
                // 心跳，可以更新状态显示
                statusSpan.textContent = '执行中...';
                break;

            case 'done':
                eventSource.close();
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-play-fill"></i> 执行';

                if (data.success) {
                    statusSpan.innerHTML = `<span class="text-success">✓ 完成 (${data.duration.toFixed(2)}s)</span>`;
                } else {
                    statusSpan.innerHTML = `<span class="text-danger">✗ 失败 (返回码: ${data.return_code})</span>`;
                }

                // 显示文件树
                if (data.files && data.files.length > 0) {
                    filesSection.style.display = 'block';
                    renderFileTree(filesTree, data.files);
                }
                break;

            case 'error':
                eventSource.close();
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-play-fill"></i> 执行';
                statusSpan.innerHTML = `<span class="text-danger">✗ 错误: ${data.message}</span>`;
                break;
        }
    };

    eventSource.onerror = function(event) {
        eventSource.close();
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-play-fill"></i> 执行';
        statusSpan.innerHTML = '<span class="text-danger">✗ 连接断开</span>';
    };
}

// 追加日志行
function appendLogLine(container, line, type) {
    const lineDiv = document.createElement('div');
    lineDiv.className = type;
    lineDiv.textContent = line;
    container.appendChild(lineDiv);
    // 自动滚动到底部
    container.scrollTop = container.scrollHeight;
}
```

---

### 4.4 文件写入

```javascript
// 写入文件
async function writeFile(partId) {
    const filepath = document.getElementById(`${partId}-filepath`).value;
    const content = document.getElementById(`${partId}-code`).value;
    const filesSection = document.getElementById(`${partId}-files-section`);
    const filesTree = document.getElementById(`${partId}-files`);
    const statusSpan = document.getElementById(`${partId}-status`);
    const btn = document.getElementById(`btn-write-${partId}`);

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 写入中...';
    statusSpan.textContent = '';

    try {
        const response = await fetch('/api/runtime/workspace/write-file', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_path: filepath,
                content: content
            })
        });
        const data = await response.json();

        if (data.success) {
            statusSpan.innerHTML = `<span class="text-success">✓ 文件写入成功 (${formatSize(data.size)})</span>`;

            // 显示文件树
            if (data.files && data.files.length > 0) {
                filesSection.style.display = 'block';
                renderFileTree(filesTree, data.files);
            }
        } else {
            statusSpan.innerHTML = `<span class="text-danger">✗ ${data.message}</span>`;
        }
    } catch (error) {
        statusSpan.innerHTML = `<span class="text-danger">✗ 写入失败: ${error.message}</span>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-save"></i> 写入文件';
    }
}
```

---

### 4.5 文件树渲染

```javascript
// 渲染文件树
function renderFileTree(container, files, depth = 0) {
    container.innerHTML = '';
    renderFileTreeRecursive(container, files, depth);
}

function renderFileTreeRecursive(container, files, depth) {
    for (const file of files) {
        const item = document.createElement('div');
        item.className = `file-tree-item ${file.type}`;
        item.style.paddingLeft = `${depth * 16}px`;

        const icon = document.createElement('span');
        icon.className = 'icon';
        icon.innerHTML = file.type === 'directory' ? '📁' : '📄';

        const name = document.createElement('span');
        name.className = 'name';
        name.textContent = file.name;

        item.appendChild(icon);
        item.appendChild(name);

        if (file.type === 'file' && file.size !== undefined) {
            const size = document.createElement('span');
            size.className = 'size';
            size.textContent = formatSize(file.size);
            item.appendChild(size);
        }

        container.appendChild(item);

        // 递归渲染子目录
        if (file.type === 'directory' && file.children) {
            renderFileTreeRecursive(container, file.children, depth + 1);
        }
    }
}

// 格式化文件大小
function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
```

---

### 4.6 事件绑定

```javascript
// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    // 加载工作空间状态
    WorkspaceState.load();

    // 绑定工作空间按钮
    document.getElementById('btn-init-workspace').addEventListener('click', initWorkspace);
    document.getElementById('btn-cleanup-workspace').addEventListener('click', cleanupWorkspace);

    // 绑定命令执行按钮
    document.getElementById('btn-execute-part2').addEventListener('click', function() {
        const command = document.getElementById('part2-command').value;
        executeCommand('part2', command);
    });

    document.getElementById('btn-execute-part5-1').addEventListener('click', function() {
        const command = document.getElementById('part5-1-command').value;
        executeCommand('part5-1', command);
    });

    // 绑定文件写入按钮
    document.getElementById('btn-write-part3').addEventListener('click', function() {
        writeFile('part3');
    });
});
```

---

## 5. 默认命令模板

### 5.1 Part 2: 初始化项目

```bash
uv init agentcore_runtime_direct_deploy
cd agentcore_runtime_direct_deploy
uv add bedrock-agentcore strands-agents
```

### 5.2 Part 3: Agent 代码

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload, context):
    """
    Agent 入口点
    payload: {"prompt": "用户输入"}
    """
    prompt = payload.get("prompt", "Hello")

    # 在这里实现 Agent 逻辑
    response = f"You said: {prompt}"

    return {"response": response}
```

### 5.3 Part 5-1: 创建部署包

```bash
cd agentcore_runtime_direct_deploy
pip install -t build/ bedrock-agentcore strands-agents
cp main.py build/
cd build && zip -r ../deployment_package.zip .
```

---

## 6. 响应式设计

### 6.1 移动端适配

```css
@media (max-width: 768px) {
    .workspace-status-bar .d-flex {
        flex-direction: column;
        align-items: flex-start;
    }

    .workspace-actions {
        margin-top: 12px;
        width: 100%;
    }

    .workspace-actions .btn {
        width: 100%;
        margin-bottom: 8px;
    }

    .command-editor,
    .code-editor {
        font-size: 12px;
    }

    .output-log {
        max-height: 200px;
    }
}
```

---

## 7. 错误处理 UI

### 7.1 Toast 通知

```javascript
function showToast(title, message, type = 'info') {
    // 使用 Bootstrap Toast 或自定义实现
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'}`;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong>: ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}
```

### 7.2 清空输出

```javascript
function clearAllOutputs() {
    // 清空所有步骤的输出
    ['part2', 'part3', 'part5-1'].forEach(partId => {
        const outputSection = document.getElementById(`${partId}-output-section`);
        const filesSection = document.getElementById(`${partId}-files-section`);
        if (outputSection) outputSection.style.display = 'none';
        if (filesSection) filesSection.style.display = 'none';
    });
}
```
