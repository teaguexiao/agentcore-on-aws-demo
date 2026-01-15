/**
 * AgentCore Runtime Container Deployment - Frontend Logic
 * 完整重写版本，支持真实命令执行和可编辑代码
 */

// ==================== 状态管理 ====================

const ContainerWorkspaceState = {
    initialized: false,
    workspace_id: null,
    workspace_path: null,
    runtime_id: null,
    runtime_arn: null,
    ecr_image_uri: null,
    agent_name: null,

    save() {
        localStorage.setItem('container_workspace_state', JSON.stringify({
            initialized: this.initialized,
            workspace_id: this.workspace_id,
            workspace_path: this.workspace_path,
            runtime_id: this.runtime_id,
            runtime_arn: this.runtime_arn,
            ecr_image_uri: this.ecr_image_uri,
            agent_name: this.agent_name
        }));
    },

    load() {
        const saved = localStorage.getItem('container_workspace_state');
        if (saved) {
            try {
                const data = JSON.parse(saved);
                Object.assign(this, data);
            } catch (e) {
                console.error('Failed to load container workspace state:', e);
            }
        }
    },

    clear() {
        this.initialized = false;
        this.workspace_id = null;
        this.workspace_path = null;
        this.runtime_id = null;
        this.runtime_arn = null;
        this.ecr_image_uri = null;
        this.agent_name = null;
        localStorage.removeItem('container_workspace_state');
    }
};

// 配置缓存
let containerConfig = null;

// ==================== 状态标识辅助函数 ====================

function updateContainerStatus(partId, status, message, duration = null) {
    const statusSpan = document.getElementById(`container-${partId}-status`);
    if (!statusSpan) return;

    switch (status) {
        case 'running':
            statusSpan.innerHTML = '<span class="text-primary"><i class="fas fa-spinner fa-spin me-1"></i>执行中...</span>';
            statusSpan.className = 'execution-status running';
            break;
        case 'success':
            const durationText = duration ? ` (${duration.toFixed(2)}s)` : '';
            statusSpan.innerHTML = `<span class="text-success"><i class="fas fa-check-circle me-1"></i>${message || '完成'}${durationText}</span>`;
            statusSpan.className = 'execution-status success';
            break;
        case 'error':
            statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>${message || '失败'}</span>`;
            statusSpan.className = 'execution-status error';
            break;
        default:
            statusSpan.innerHTML = '';
            statusSpan.className = 'execution-status';
    }
}

function clearAllContainerStatus() {
    for (let i = 2; i <= 11; i++) {
        updateContainerStatus(`part${i}`, 'clear');
    }
}

// ==================== 工作空间管理 ====================

async function initContainerWorkspace() {
    const btn = document.getElementById('btn-container-workspace-init');
    const spinner = btn.querySelector('.spinner-border');

    btn.disabled = true;
    spinner.style.display = 'inline-block';

    try {
        const response = await fetch('/api/runtime/demo/container/workspace/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.success) {
            ContainerWorkspaceState.initialized = true;
            ContainerWorkspaceState.workspace_id = data.workspace_id;
            ContainerWorkspaceState.workspace_path = data.workspace_path;
            ContainerWorkspaceState.save();

            updateContainerWorkspaceUI();
            showToast('Container 工作环境初始化成功', 'success');
        } else {
            showToast(data.message || '初始化失败', 'error');
        }
    } catch (error) {
        console.error('Init workspace error:', error);
        showToast('初始化失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
    }
}

async function cleanupContainerWorkspace() {
    let message = '确定要清理 Container 工作环境吗？所有文件将被删除。';
    if (ContainerWorkspaceState.runtime_id) {
        message = '⚠️ 警告：当前存在已部署的 Runtime！\n\n清理工作空间不会自动删除 Runtime。\n建议先执行 Part 11 删除 Runtime。\n\n确定要继续清理吗？';
    }
    if (!confirm(message)) {
        return;
    }

    const btn = document.getElementById('btn-container-workspace-cleanup');
    btn.disabled = true;

    try {
        const response = await fetch('/api/runtime/demo/container/workspace/cleanup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.success) {
            ContainerWorkspaceState.clear();
            updateContainerWorkspaceUI();
            // 重置所有代码模板和 UI
            resetAllContainerTemplates();
            clearAllContainerStatus();
            hideAllContainerLogAreas();
            showToast('Container 工作环境已清理', 'success');
        } else {
            showToast(data.message || '清理失败', 'error');
        }
    } catch (error) {
        console.error('Cleanup workspace error:', error);
        showToast('清理失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
    }
}

async function loadContainerWorkspaceStatus() {
    try {
        const response = await fetch('/api/runtime/demo/container/workspace/status');
        const data = await response.json();

        if (data.initialized) {
            ContainerWorkspaceState.initialized = true;
            ContainerWorkspaceState.workspace_id = data.workspace_id;
            ContainerWorkspaceState.workspace_path = data.workspace_path;
            ContainerWorkspaceState.runtime_id = data.runtime_id;
            ContainerWorkspaceState.runtime_arn = data.runtime_arn;
            ContainerWorkspaceState.ecr_image_uri = data.ecr_image_uri;
            ContainerWorkspaceState.save();
        }
        updateContainerWorkspaceUI();
        autoFillContainerRuntimeInfo();
    } catch (error) {
        console.error('Load workspace status error:', error);
    }
}

function updateContainerWorkspaceUI() {
    const statusDiv = document.getElementById('container-workspace-status');
    const infoDiv = document.getElementById('container-workspace-info');
    const initBtn = document.getElementById('btn-container-workspace-init');
    const cleanupBtn = document.getElementById('btn-container-workspace-cleanup');

    if (ContainerWorkspaceState.initialized) {
        statusDiv.innerHTML = '<span class="badge bg-success">已初始化</span>';
        infoDiv.style.display = 'block';
        document.getElementById('container-workspace-id').textContent = ContainerWorkspaceState.workspace_id;
        document.getElementById('container-workspace-path').textContent = ContainerWorkspaceState.workspace_path;

        initBtn.disabled = true;
        cleanupBtn.disabled = false;  // 始终允许清理
    } else {
        statusDiv.innerHTML = '<span class="badge bg-secondary">未初始化</span>';
        infoDiv.style.display = 'none';
        initBtn.disabled = false;
        cleanupBtn.disabled = true;
    }

    // 启用/禁用需要工作空间的按钮
    const workspaceButtons = [
        'btn-container-part2', 'btn-container-part3', 'btn-container-part4',
        'btn-container-part5', 'btn-container-part6', 'btn-container-part7',
        'btn-container-part8'
    ];
    workspaceButtons.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.disabled = !ContainerWorkspaceState.initialized;
        }
    });

    // 启用/禁用需要 Runtime 的按钮 (Part 9-11)
    const runtimeButtons = [
        'btn-container-part9', 'btn-container-part10', 'btn-container-part11'
    ];
    const hasRuntime = ContainerWorkspaceState.initialized && ContainerWorkspaceState.runtime_id;
    runtimeButtons.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.disabled = !hasRuntime;
        }
    });
}

// ==================== 配置加载 ====================

async function loadContainerConfig() {
    try {
        const response = await fetch('/api/runtime/demo/container/config');
        const data = await response.json();
        if (data.status === 'success') {
            containerConfig = data.config;
            updateContainerCodeVariables();
        }
    } catch (error) {
        console.error('Load config error:', error);
    }
}

function updateContainerCodeVariables() {
    if (!containerConfig) return;

    const config = {
        ...containerConfig,
        runtime_id: ContainerWorkspaceState.runtime_id || '{runtime_id}',
        runtime_arn: ContainerWorkspaceState.runtime_arn || '{runtime_arn}',
        agent_name: ContainerWorkspaceState.agent_name || '{agent_name}'
    };

    // 更新所有代码编辑器中的变量
    const codeElements = document.querySelectorAll('#container-tab .code-editor');
    codeElements.forEach(el => {
        let code = el.value;
        code = code.replace(/\{ACCOUNT_ID\}/g, config.ACCOUNT_ID);
        code = code.replace(/\{REGION\}/g, config.REGION);
        code = code.replace(/\{CONTAINER_ECR_REPOSITORY_NAME\}/g, config.CONTAINER_ECR_REPOSITORY_NAME);
        code = code.replace(/\{CONTAINER_IMAGE_TAG\}/g, config.CONTAINER_IMAGE_TAG);
        code = code.replace(/\{CONTAINER_EXECUTION_ROLE_ARN\}/g, config.CONTAINER_EXECUTION_ROLE_ARN);
        code = code.replace(/\{ECR_IMAGE_URI\}/g, config.ECR_IMAGE_URI);
        el.value = code;
    });
}

// ==================== SSE 命令执行 ====================

function executeContainerCommand(partId, command, onComplete) {
    console.log(`executeContainerCommand called: partId=${partId}`);
    const logArea = document.getElementById(`log-area-container-${partId}`);
    const logOutput = document.getElementById(`log-output-container-${partId}`);

    if (!logArea || !logOutput) {
        console.error(`Log elements not found for partId: ${partId}`);
        if (onComplete) {
            onComplete({ success: false, error: 'Log elements not found' });
        }
        return null;
    }

    logArea.style.display = 'block';
    logOutput.textContent = '';

    const encodedCommand = encodeURIComponent(command);
    const url = `/api/runtime/demo/container/workspace/execute?command=${encodedCommand}`;

    const eventSource = new EventSource(url);

    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);

            if (data.type === 'stdout' || data.type === 'stderr') {
                const prefix = data.type === 'stderr' ? '[stderr] ' : '';
                logOutput.textContent += prefix + data.line + '\n';
                logOutput.scrollTop = logOutput.scrollHeight;
            } else if (data.type === 'heartbeat') {
                // 心跳，忽略
            } else if (data.type === 'done') {
                eventSource.close();
                if (data.files) {
                    renderContainerFileTree(data.files, partId);
                }
                if (onComplete) {
                    onComplete(data);
                }
            } else if (data.type === 'error') {
                logOutput.textContent += '\n[ERROR] ' + data.message + '\n';
                eventSource.close();
                if (onComplete) {
                    onComplete({ success: false, error: data.message });
                }
            }
        } catch (e) {
            console.error('Parse error:', e);
        }
    };

    eventSource.onerror = function(error) {
        console.error('SSE error:', error);
        eventSource.close();
        logOutput.textContent += '\n[连接错误]\n';
        if (onComplete) {
            onComplete({ success: false, error: 'Connection error' });
        }
    };

    return eventSource;
}

// ==================== 文件写入 ====================

async function writeContainerFile(partId, filePath, content) {
    console.log(`writeContainerFile called: partId=${partId}, filePath=${filePath}`);
    try {
        const response = await fetch('/api/runtime/demo/container/workspace/write-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: filePath, content: content })
        });
        console.log('Response status:', response.status);
        const data = await response.json();
        console.log('Response data:', data);

        if (data.success) {
            showToast(`文件 ${filePath} 写入成功`, 'success');
            if (data.files) {
                console.log('Rendering file tree for partId:', partId);
                renderContainerFileTree(data.files, partId);
            }
        } else {
            showToast(data.message || '写入失败', 'error');
        }
        return data;
    } catch (error) {
        console.error('Write file error:', error);
        showToast('写入失败: ' + error.message, 'error');
        return { success: false, error: error.message };
    }
}

// ==================== Python 代码执行 ====================

function executeContainerPython(partId, code, onComplete) {
    const logArea = document.getElementById(`log-area-container-${partId}`);
    const logOutput = document.getElementById(`log-output-container-${partId}`);
    const resultArea = document.getElementById(`result-area-container-${partId}`);
    const resultOutput = document.getElementById(`result-output-container-${partId}`);

    if (logArea) {
        logArea.style.display = 'block';
        logOutput.textContent = '';
    }
    if (resultArea) {
        resultArea.style.display = 'none';
    }

    // 使用 POST 请求配合 SSE
    fetch('/api/runtime/demo/container/workspace/execute-python', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code, session_id: 'container_session' })
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        function processStream() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    return;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            handlePythonOutput(data, partId, logOutput, resultArea, resultOutput, onComplete);
                        } catch (e) {
                            // 忽略解析错误
                        }
                    }
                });

                processStream();
            });
        }

        processStream();
    }).catch(error => {
        console.error('Execute Python error:', error);
        if (onComplete) {
            onComplete({ success: false, error: error.message });
        }
    });
}

function handlePythonOutput(data, partId, logOutput, resultArea, resultOutput, onComplete) {
    if (data.type === 'stdout' || data.type === 'stderr') {
        const prefix = data.type === 'stderr' ? '[stderr] ' : '';
        if (logOutput) {
            logOutput.textContent += prefix + data.line + '\n';
            logOutput.scrollTop = logOutput.scrollHeight;
        }
    } else if (data.type === 'done') {
        if (data.result) {
            // 更新状态
            if (data.result.runtime_id) {
                ContainerWorkspaceState.runtime_id = data.result.runtime_id;
            }
            if (data.result.runtime_arn) {
                ContainerWorkspaceState.runtime_arn = data.result.runtime_arn;
            }
            if (data.result.agent_name) {
                ContainerWorkspaceState.agent_name = data.result.agent_name;
            }
            if (data.result.ecr_image_uri) {
                ContainerWorkspaceState.ecr_image_uri = data.result.ecr_image_uri;
            }
            ContainerWorkspaceState.save();
            updateContainerWorkspaceUI();
            autoFillContainerRuntimeInfo();
        }

        if (resultArea && resultOutput) {
            resultArea.style.display = 'block';
            resultOutput.textContent = data.stdout || '';
        }

        if (onComplete) {
            onComplete(data);
        }
    } else if (data.type === 'error') {
        if (logOutput) {
            logOutput.textContent += '\n[ERROR] ' + data.message + '\n';
        }
        if (onComplete) {
            onComplete({ success: false, error: data.message });
        }
    }
}

// ==================== Part 执行函数 ====================

function executeContainerPart2() {
    const btn = document.getElementById('btn-container-part2');
    const spinner = btn.querySelector('.spinner-border');
    const command = document.getElementById('container-part2-command').value;

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part2', 'running');

    executeContainerCommand('part2', command, (result) => {
        btn.disabled = false;
        spinner.style.display = 'none';
        if (result.success) {
            updateContainerStatus('part2', 'success', '完成', result.duration);
        } else {
            updateContainerStatus('part2', 'error', result.error || '执行失败');
        }
    });
}

function executeContainerPart3() {
    const btn = document.getElementById('btn-container-part3');
    const spinner = btn.querySelector('.spinner-border');
    const filePath = document.getElementById('container-part3-filepath').value;
    const content = document.getElementById('container-part3-content').value;

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part3', 'running');

    writeContainerFile('part3', filePath, content)
        .then(result => {
            if (result.success) {
                updateContainerStatus('part3', 'success', `写入成功 (${formatFileSize(result.size)})`);
            } else {
                updateContainerStatus('part3', 'error', result.message || '写入失败');
            }
        })
        .catch(error => {
            updateContainerStatus('part3', 'error', '写入失败');
        })
        .finally(() => {
            btn.disabled = false;
            spinner.style.display = 'none';
        });
}

function executeContainerPart4() {
    const btn = document.getElementById('btn-container-part4');
    const spinner = btn.querySelector('.spinner-border');
    const filePath = document.getElementById('container-part4-filepath').value;
    const content = document.getElementById('container-part4-content').value;

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part4', 'running');

    writeContainerFile('part4', filePath, content)
        .then(result => {
            if (result.success) {
                updateContainerStatus('part4', 'success', `写入成功 (${formatFileSize(result.size)})`);
            } else {
                updateContainerStatus('part4', 'error', result.message || '写入失败');
            }
        })
        .catch(error => {
            updateContainerStatus('part4', 'error', '写入失败');
        })
        .finally(() => {
            btn.disabled = false;
            spinner.style.display = 'none';
        });
}

function executeContainerPart5() {
    const btn = document.getElementById('btn-container-part5');
    const spinner = btn.querySelector('.spinner-border');
    const filePath = document.getElementById('container-part5-filepath').value;
    const content = document.getElementById('container-part5-content').value;

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part5', 'running');

    writeContainerFile('part5', filePath, content)
        .then(result => {
            if (result.success) {
                updateContainerStatus('part5', 'success', `写入成功 (${formatFileSize(result.size)})`);
            } else {
                updateContainerStatus('part5', 'error', result.message || '写入失败');
            }
        })
        .catch(error => {
            updateContainerStatus('part5', 'error', '写入失败');
        })
        .finally(() => {
            btn.disabled = false;
            spinner.style.display = 'none';
        });
}

function executeContainerPart6() {
    const btn = document.getElementById('btn-container-part6');
    const spinner = btn.querySelector('.spinner-border');
    const command = document.getElementById('container-part6-command').value;

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part6', 'running');

    executeContainerCommand('part6', command, (result) => {
        btn.disabled = false;
        spinner.style.display = 'none';
        if (result.success) {
            updateContainerStatus('part6', 'success', '登录成功', result.duration);
        } else {
            updateContainerStatus('part6', 'error', result.error || 'ECR 登录失败');
        }
    });
}

function executeContainerPart7() {
    const btn = document.getElementById('btn-container-part7');
    const spinner = btn.querySelector('.spinner-border');
    const commandEl = document.getElementById('container-part7-command');

    if (!commandEl) {
        updateContainerStatus('part7', 'error', '找不到命令输入框');
        return;
    }

    const command = commandEl.value;
    if (!command || !command.trim()) {
        updateContainerStatus('part7', 'error', '请输入构建命令');
        return;
    }

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part7', 'running');

    executeContainerCommand('part7', command, (result) => {
        btn.disabled = false;
        spinner.style.display = 'none';
        if (result.success) {
            updateContainerStatus('part7', 'success', '构建推送成功', result.duration);
        } else {
            updateContainerStatus('part7', 'error', result.error || '构建失败');
        }
    });
}

function executeContainerPart8() {
    const btn = document.getElementById('btn-container-part8');
    const spinner = btn.querySelector('.spinner-border');
    const code = document.getElementById('container-part8-code').value;

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part8', 'running');

    executeContainerPython('part8', code, (result) => {
        btn.disabled = false;
        spinner.style.display = 'none';
        if (result.success) {
            updateContainerStatus('part8', 'success', '部署成功', result.duration);
            // 更新 Part 9-11 的代码中的变量
            updatePart9to11CodeVariables();
        } else {
            updateContainerStatus('part8', 'error', result.error || '部署失败');
        }
    });
}

function executeContainerPart9() {
    const btn = document.getElementById('btn-container-part9');
    const spinner = btn.querySelector('.spinner-border');
    const code = document.getElementById('container-part9-code').value;

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part9', 'running');

    executeContainerPython('part9', code, (result) => {
        btn.disabled = false;
        spinner.style.display = 'none';
        if (result.success) {
            updateContainerStatus('part9', 'success', '查询成功', result.duration);
        } else {
            updateContainerStatus('part9', 'error', result.error || '查询失败');
        }
    });
}

function executeContainerPart10() {
    const btn = document.getElementById('btn-container-part10');
    const spinner = btn.querySelector('.spinner-border');
    const code = document.getElementById('container-part10-code').value;

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part10', 'running');

    executeContainerPython('part10', code, (result) => {
        btn.disabled = false;
        spinner.style.display = 'none';
        if (result.success) {
            updateContainerStatus('part10', 'success', '调用成功', result.duration);
        } else {
            updateContainerStatus('part10', 'error', result.error || '调用失败');
        }
    });
}

function executeContainerPart11() {
    if (!confirm('确定要删除 Runtime 吗？此操作不可逆！')) {
        return;
    }

    const btn = document.getElementById('btn-container-part11');
    const spinner = btn.querySelector('.spinner-border');
    const code = document.getElementById('container-part11-code').value;

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    updateContainerStatus('part11', 'running');

    executeContainerPython('part11', code, async (result) => {
        btn.disabled = false;
        spinner.style.display = 'none';
        if (result.success) {
            updateContainerStatus('part11', 'success', '已删除', result.duration);
            // 清除 runtime 相关状态（前端）
            ContainerWorkspaceState.runtime_id = null;
            ContainerWorkspaceState.runtime_arn = null;
            ContainerWorkspaceState.agent_name = null;
            ContainerWorkspaceState.save();

            // 通知后端清除 workspace 中的 runtime 关联
            try {
                await fetch('/api/runtime/demo/container/workspace/clear-runtime', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
            } catch (e) {
                console.error('Failed to clear runtime association:', e);
            }

            updateContainerWorkspaceUI();
        } else {
            updateContainerStatus('part11', 'error', result.error || '删除失败');
        }
    });
}

// ==================== 辅助函数 ====================

function renderContainerFileTree(files, partId) {
    console.log(`renderContainerFileTree called: partId=${partId}, files=`, files);
    const treeArea = document.getElementById(`file-tree-container-${partId}`);
    const treeContent = document.getElementById(`file-tree-content-container-${partId}`);
    console.log(`treeArea:`, treeArea, `treeContent:`, treeContent);

    if (!treeArea || !treeContent) return;

    treeArea.style.display = 'block';
    treeContent.innerHTML = renderFileTreeHTML(files);
}

function renderFileTreeHTML(items, indent = 0) {
    let html = '<ul class="file-tree-list" style="list-style: none; padding-left: ' + (indent * 20) + 'px; margin: 0;">';

    items.forEach(item => {
        const icon = item.type === 'directory' ? 'fa-folder text-warning' : 'fa-file text-secondary';
        html += `<li style="padding: 2px 0;">
            <i class="fas ${icon} me-2"></i>${item.name}`;
        if (item.type === 'file' && item.size !== undefined) {
            html += ` <small class="text-muted">(${formatFileSize(item.size)})</small>`;
        }
        if (item.children && item.children.length > 0) {
            html += renderFileTreeHTML(item.children, indent + 1);
        }
        html += '</li>';
    });

    html += '</ul>';
    return html;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function autoFillContainerRuntimeInfo() {
    // 更新 Part 9-11 的代码中的变量
    updatePart9to11CodeVariables();
}

function updatePart9to11CodeVariables() {
    if (!ContainerWorkspaceState.runtime_id && !ContainerWorkspaceState.runtime_arn) {
        return;
    }

    // 获取配置信息
    const region = containerConfig?.REGION || 'us-west-2';
    const runtimeId = ContainerWorkspaceState.runtime_id || '{runtime_id}';
    const runtimeArn = ContainerWorkspaceState.runtime_arn || '{runtime_arn}';

    // Part 9: 检查 Runtime 状态
    const part9Code = document.getElementById('container-part9-code');
    if (part9Code) {
        let code = part9Code.value;
        code = code.replace(/\{REGION\}/g, region);
        code = code.replace(/\{runtime_id\}/g, runtimeId);
        part9Code.value = code;
    }

    // Part 10: 调用 Agent
    const part10Code = document.getElementById('container-part10-code');
    if (part10Code) {
        let code = part10Code.value;
        code = code.replace(/\{REGION\}/g, region);
        code = code.replace(/\{runtime_arn\}/g, runtimeArn);
        part10Code.value = code;
    }

    // Part 11: 清理 Runtime
    const part11Code = document.getElementById('container-part11-code');
    if (part11Code) {
        let code = part11Code.value;
        code = code.replace(/\{REGION\}/g, region);
        code = code.replace(/\{runtime_id\}/g, runtimeId);
        if (containerConfig) {
            code = code.replace(/\{CONTAINER_ECR_REPOSITORY_NAME\}/g, containerConfig.CONTAINER_ECR_REPOSITORY_NAME);
            code = code.replace(/\{CONTAINER_IMAGE_TAG\}/g, containerConfig.CONTAINER_IMAGE_TAG);
        }
        part11Code.value = code;
    }
}

// 存储原始代码模板
const ContainerCodeTemplates = {};

function saveOriginalContainerTemplates() {
    // 保存所有代码编辑器的原始内容
    const codeElements = document.querySelectorAll('#container-tab .code-editor');
    codeElements.forEach(el => {
        const id = el.id;
        if (id && !ContainerCodeTemplates[id]) {
            ContainerCodeTemplates[id] = el.value;
        }
    });

    // 同样保存命令输入框
    const commandElements = ['container-part2-command', 'container-part6-command', 'container-part7-command'];
    commandElements.forEach(id => {
        const el = document.getElementById(id);
        if (el && !ContainerCodeTemplates[id]) {
            ContainerCodeTemplates[id] = el.value;
        }
    });
}

function resetContainerCodeTemplate(partId) {
    let elementId = null;

    // 根据 partId 确定元素 ID
    if (partId === 'part2') {
        elementId = 'container-part2-command';
    } else if (partId === 'part6') {
        elementId = 'container-part6-command';
    } else if (partId === 'part7') {
        elementId = 'container-part7-command';
    } else {
        elementId = `container-${partId}-code`;
    }

    const element = document.getElementById(elementId);
    const originalTemplate = ContainerCodeTemplates[elementId];

    if (element && originalTemplate) {
        element.value = originalTemplate;
        // 重新应用配置变量替换
        if (containerConfig) {
            let code = element.value;
            code = code.replace(/\{ACCOUNT_ID\}/g, containerConfig.ACCOUNT_ID);
            code = code.replace(/\{REGION\}/g, containerConfig.REGION);
            code = code.replace(/\{CONTAINER_ECR_REPOSITORY_NAME\}/g, containerConfig.CONTAINER_ECR_REPOSITORY_NAME);
            code = code.replace(/\{CONTAINER_IMAGE_TAG\}/g, containerConfig.CONTAINER_IMAGE_TAG);
            code = code.replace(/\{CONTAINER_EXECUTION_ROLE_ARN\}/g, containerConfig.CONTAINER_EXECUTION_ROLE_ARN);
            code = code.replace(/\{ECR_IMAGE_URI\}/g, containerConfig.ECR_IMAGE_URI);
            element.value = code;
        }
        showToast('代码已重置', 'success');
    } else {
        showToast('无法重置代码', 'error');
    }
}

function resetAllContainerTemplates() {
    // 重置所有代码模板到原始状态
    Object.keys(ContainerCodeTemplates).forEach(elementId => {
        const element = document.getElementById(elementId);
        const originalTemplate = ContainerCodeTemplates[elementId];
        if (element && originalTemplate) {
            element.value = originalTemplate;
        }
    });

    // 重新应用配置变量替换（不包含 runtime 相关变量）
    if (containerConfig) {
        updateContainerDemoCodeVariables(containerConfig);
    }
}

function hideAllContainerLogAreas() {
    // 隐藏所有日志区域和文件树区域
    for (let i = 2; i <= 11; i++) {
        const logArea = document.getElementById(`log-area-container-part${i}`);
        if (logArea) {
            logArea.style.display = 'none';
            const logOutput = document.getElementById(`log-output-container-part${i}`);
            if (logOutput) logOutput.textContent = '';
        }

        const fileTree = document.getElementById(`file-tree-container-part${i}`);
        if (fileTree) {
            fileTree.style.display = 'none';
        }

        const resultArea = document.getElementById(`result-area-container-part${i}`);
        if (resultArea) {
            resultArea.style.display = 'none';
            const resultOutput = document.getElementById(`result-output-container-part${i}`);
            if (resultOutput) resultOutput.textContent = '';
        }
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

function showContainerToast(message, type = 'info') {
    // 使用独立的 toast 实现，避免与 runtime.js 的 showToast 冲突
    console.log(`[Container Toast] [${type}] ${message}`);
    const container = document.getElementById('toast-container');
    if (container) {
        const toast = document.createElement('div');
        toast.className = `toast show align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'}`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }
}

// 别名，方便调用
function showToast(message, type = 'info') {
    showContainerToast(message, type);
}

// ==================== 页面初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Container Runtime page loaded');

    // 保存原始代码模板（在任何修改之前）
    saveOriginalContainerTemplates();

    // 加载状态
    ContainerWorkspaceState.load();

    // 从服务器加载最新状态
    loadContainerWorkspaceStatus();

    // 加载配置并更新变量
    loadContainerConfig().then(() => {
        // 自动填充
        autoFillContainerRuntimeInfo();
    });
});
