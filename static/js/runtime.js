/**
 * AgentCore Runtime Demo - Frontend Logic
 *
 * 管理 Runtime 演示页面的所有交互逻辑
 */

// ==================== 代码模板存储 ====================
// 存储原始代码模板，用于清理后重置
const CODE_TEMPLATES = {};

// ==================== 工作空间状态管理 ====================

const WorkspaceState = {
    initialized: false,
    workspace_id: null,
    workspace_path: null,
    runtime_id: null,
    deployment_package_path: null,  // 上一步生成的部署包路径

    // 从后端加载状态
    async load() {
        try {
            const response = await fetch('/api/runtime/demo/workspace/status', {
                credentials: 'include'
            });
            if (!response.ok) {
                if (response.status === 401) {
                    console.log('Not logged in, workspace status unavailable');
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            this.initialized = data.initialized;
            this.workspace_id = data.workspace_id;
            this.workspace_path = data.workspace_path;
            this.runtime_id = data.runtime_id;
            this.updateUI();
            console.log('Workspace state loaded:', this);
        } catch (error) {
            console.error('Failed to load workspace status:', error);
        }
    },

    // 更新 UI
    updateUI() {
        const statusBar = document.getElementById('workspace-status-bar');
        const statusText = document.getElementById('workspace-status-text');
        const pathText = document.getElementById('workspace-path-text');
        const pathValue = document.getElementById('workspace-path');
        const btnInit = document.getElementById('btn-init-workspace');
        const btnCleanup = document.getElementById('btn-cleanup-workspace');
        const securityWarning = document.getElementById('security-warning');

        if (!statusBar) return;

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
        const buttons = [
            'btn-step2',
            'btn-step3',
            'btn-step5-package'
        ];
        buttons.forEach(id => {
            const btn = document.getElementById(id);
            if (btn) btn.disabled = !enabled;
        });
    }
};

// ==================== 状态管理 ====================

const RuntimeState = {
    session_id: generateSessionId(),
    runtime_arn: null,
    runtime_id: null,
    runtime_version: "1",
    agent_name: null,
    created_at: null,

    save() {
        localStorage.setItem('runtime_demo_state', JSON.stringify(this));
    },

    load() {
        const saved = localStorage.getItem('runtime_demo_state');
        if (saved) {
            try {
                const data = JSON.parse(saved);
                Object.assign(this, data);
                console.log('Runtime state loaded:', this);
            } catch (e) {
                console.error('Failed to load state:', e);
            }
        }
    },

    clear() {
        this.runtime_arn = null;
        this.runtime_id = null;
        this.created_at = null;
        localStorage.removeItem('runtime_demo_state');
        console.log('Runtime state cleared');
    }
};

// ==================== SSE (Server-Sent Events) 管理 ====================

// 存储活动的 EventSource 连接
const activeEventSources = new Map();

/**
 * 创建 SSE 连接并监听流式输出
 * @param {string} url - SSE 端点 URL
 * @param {string} step - 步骤标识 (如 '2', '3', '5-package')
 * @param {function} onComplete - 完成回调函数
 */
function connectSSE(url, step, onComplete) {
    // 关闭旧连接（如果存在）
    if (activeEventSources.has(step)) {
        activeEventSources.get(step).close();
    }

    const eventSource = new EventSource(url);
    activeEventSources.set(step, eventSource);

    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);

            if (data.done) {
                // 流式输出完成
                eventSource.close();
                activeEventSources.delete(step);

                if (data.error) {
                    // 有错误
                    onComplete({ success: false, error: data.error });
                } else {
                    // 成功
                    onComplete({ success: true, data: data });
                }
            } else {
                // 追加日志行
                if (data.line !== undefined) {
                    appendLog(step, data.line + '\n');
                }
            }
        } catch (e) {
            console.error('SSE message parse error:', e);
        }
    };

    eventSource.onerror = function(error) {
        console.error('SSE error:', error);
        eventSource.close();
        activeEventSources.delete(step);
        onComplete({ success: false, error: 'SSE connection error' });
    };

    return eventSource;
}

// ==================== 工具函数 ====================

function generateSessionId() {
    return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
}

function showLoading(buttonElement, show = true) {
    if (show) {
        buttonElement.disabled = true;
        const spinner = buttonElement.querySelector('.spinner-border');
        if (spinner) spinner.classList.add('active');
    } else {
        buttonElement.disabled = false;
        const spinner = buttonElement.querySelector('.spinner-border');
        if (spinner) spinner.classList.remove('active');
    }
}

function displayResult(step, message, output = '', isError = false) {
    const resultArea = document.getElementById(`result-${step}`);
    if (!resultArea) return;

    const outputElement = resultArea.querySelector('.result-output');
    if (outputElement) {
        outputElement.textContent = output || message;
    }

    const alertDiv = resultArea.querySelector('.alert');
    if (alertDiv) {
        alertDiv.classList.remove('alert-success', 'alert-danger');
        alertDiv.classList.add(isError ? 'alert-danger' : 'alert-success');
    }

    resultArea.style.display = 'block';
}

// 新增：显示流式日志输出
function showLogArea(step) {
    const logArea = document.getElementById(`log-area-${step}`);
    if (logArea) {
        logArea.style.display = 'block';
        const logOutput = document.getElementById(`log-output-${step}`);
        if (logOutput) {
            logOutput.textContent = '';
        }
    }
}

// 新增：追加日志内容（模拟流式输出）
function appendLog(step, text) {
    const logOutput = document.getElementById(`log-output-${step}`);
    if (logOutput) {
        logOutput.textContent += text;
        // 自动滚动到底部
        const logArea = logOutput.closest('.code-snippet');
        if (logArea) {
            logArea.scrollTop = logArea.scrollHeight;
        }
    }
}

// 新增：模拟流式输出
async function simulateStreamOutput(step, lines, delay = 50) {
    showLogArea(step);
    for (const line of lines) {
        await new Promise(resolve => setTimeout(resolve, delay));
        appendLog(step, line + '\n');
    }
}

// 新增：显示代码样式的结果
function displayCodeResult(step, content, title = "输出结果") {
    const resultArea = document.getElementById(`result-area-${step}`);
    const resultOutput = document.getElementById(`result-output-${step}`);

    if (resultArea && resultOutput) {
        resultOutput.textContent = content;
        resultArea.style.display = 'block';
    }
}

function showError(message) {
    alert(`错误: ${message}`);
}

// ==================== API 调用封装 ====================

async function callRuntimeAPI(endpoint, data = {}) {
    try {
        const requestBody = {
            session_id: RuntimeState.session_id,
            ...data
        };

        console.log(`调用 API: /api/runtime/demo/${endpoint}`, requestBody);

        const response = await fetch(`/api/runtime/demo/${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API调用失败:', error);
        throw error;
    }
}

// ==================== Step 执行函数 ====================

async function executeStep2() {
    const button = document.getElementById('btn-step2');
    showLoading(button, true);

    // 显示日志区域
    showLogArea(2);

    // 使用 SSE 连接流式输出
    const url = `/api/runtime/demo/step2-stream?session_id=${RuntimeState.session_id}`;

    connectSSE(url, '2', (result) => {
        showLoading(button, false);

        if (result.success) {
            // 显示最终结果
            displayCodeResult(2, result.data.output, "执行结果");
        } else {
            displayCodeResult(2, `错误: ${result.error}`, "执行失败");
        }
    });
}

async function executeStep3() {
    const button = document.getElementById('btn-step3');
    showLoading(button, true);

    // 显示日志区域
    showLogArea(3);

    // 使用 SSE 连接流式输出
    const url = `/api/runtime/demo/step3-stream?session_id=${RuntimeState.session_id}`;

    connectSSE(url, '3', (result) => {
        showLoading(button, false);

        if (result.success) {
            // 显示最终结果
            displayCodeResult(3, result.data.output, "执行结果");
        } else {
            displayCodeResult(3, `错误: ${result.error}`, "执行失败");
        }
    });
}

async function executeStep5Package() {
    const button = document.getElementById('btn-step5-package');
    showLoading(button, true);

    // 显示日志区域
    showLogArea('5-package');

    // 使用 SSE 连接流式输出
    const url = `/api/runtime/demo/step5-package-stream?session_id=${RuntimeState.session_id}`;

    connectSSE(url, '5-package', (result) => {
        showLoading(button, false);

        if (result.success) {
            // 显示最终结果
            const resultText = `✓ 打包完成！

Package size: ${result.data.package_size}
Package path: ${result.data.package_path}`;
            displayCodeResult('5-package', resultText, "打包结果");
        } else {
            displayCodeResult('5-package', `错误: ${result.error}`, "打包失败");
        }
    });
}

async function executeStep5Deploy() {
    const button = document.getElementById('btn-step5-deploy');
    showLoading(button, true);

    // 显示日志区域
    showLogArea('5-deploy');

    // 使用 SSE 连接流式输出
    const url = `/api/runtime/demo/step5-deploy-stream?session_id=${RuntimeState.session_id}`;

    connectSSE(url, '5-deploy', (result) => {
        showLoading(button, false);

        if (result.success) {
            const data = result.data;

            // 保存 runtime 信息到状态
            RuntimeState.runtime_arn = data.runtime_arn;
            RuntimeState.runtime_id = data.runtime_id;
            RuntimeState.runtime_version = data.runtime_version;
            RuntimeState.agent_name = data.agent_name;
            RuntimeState.created_at = Date.now();
            RuntimeState.save();

            // 自动填充到后续步骤
            autoFillRuntimeInfo();

            // 更新 demo 代码中的变量
            updateDemoCodeVariables();

            const resultText = `✓ Runtime 部署成功！

Runtime ARN: ${data.runtime_arn}
Runtime ID: ${data.runtime_id}
Runtime Version: ${data.runtime_version}
Agent Name: ${data.agent_name}

已自动填充到 Part 6, 7, 8 的输入框和代码示例中。`;

            displayCodeResult('5-deploy', resultText, "部署结果");
        } else {
            displayCodeResult('5-deploy', `部署失败: ${result.error}`, "错误");
        }
    });
}

function updateDeployProgress(progressData) {
    const progressBar = document.getElementById('deploy-progress-bar');
    const progressText = document.getElementById('deploy-progress-text');

    if (progressBar) {
        progressBar.style.width = `${progressData.progress}%`;
        progressBar.setAttribute('aria-valuenow', progressData.progress);
    }

    if (progressText) {
        progressText.textContent = progressData.message;
    }
}

async function executeStep6() {
    const button = document.getElementById('btn-step6');
    const runtimeIdInput = document.getElementById('input-runtime-id');
    const runtimeVersionInput = document.getElementById('input-runtime-version');

    const runtimeId = runtimeIdInput.value.trim();
    const runtimeVersion = runtimeVersionInput.value.trim() || "1";

    if (!runtimeId) {
        showError('请输入 Runtime ID');
        return;
    }

    showLoading(button, true);

    try {
        const result = await callRuntimeAPI('step6-status', {
            runtime_id: runtimeId,
            runtime_version: runtimeVersion
        });

        const statusInfo = `Runtime Status: ${result.runtime_status}

详细信息:
${JSON.stringify(result.details, null, 2)}

状态说明:
- READY: 就绪，可以调用
- CREATING: 创建中
- UPDATING: 更新中
- CREATE_FAILED: 创建失败
- UPDATE_FAILED: 更新失败
- DELETING: 删除中`;

        displayCodeResult(6, statusInfo, "Runtime 状态");
    } catch (error) {
        displayCodeResult(6, `错误: ${error.message}`, "查询失败");
    } finally {
        showLoading(button, false);
    }
}

async function executeStep7() {
    const button = document.getElementById('btn-step7');
    const runtimeArnInput = document.getElementById('input-runtime-arn');
    const sessionIdInput = document.getElementById('input-session-id');
    const promptInput = document.getElementById('input-prompt');

    const runtimeArn = runtimeArnInput.value.trim();
    const sessionId = sessionIdInput.value.trim();
    const prompt = promptInput.value.trim();

    if (!runtimeArn) {
        showError('请输入 Runtime ARN');
        return;
    }

    if (!sessionId || sessionId.length < 33) {
        showError('Session ID 长度必须至少 33 个字符');
        return;
    }

    if (!prompt) {
        showError('请输入 Prompt');
        return;
    }

    showLoading(button, true);

    try {
        const result = await callRuntimeAPI('step7-invoke', {
            runtime_arn: runtimeArn,
            runtime_session_id: sessionId,
            prompt: prompt,
            deployment_type: "code"  // Direct Code Deployment
        });

        const responseText = `调用成功！耗时: ${result.execution_time}

Prompt:
${result.prompt}

Agent 响应:
${JSON.stringify(result.response, null, 2)}`;

        displayCodeResult(7, responseText, "Agent 响应");
    } catch (error) {
        displayCodeResult(7, `调用失败: ${error.message}`, "错误");
    } finally {
        showLoading(button, false);
    }
}

async function executeStep8() {
    const button = document.getElementById('btn-step8');
    const runtimeIdInput = document.getElementById('input-cleanup-runtime-id');

    const runtimeId = runtimeIdInput.value.trim();

    if (!runtimeId) {
        showError('请输入 Runtime ID');
        return;
    }

    // 确认删除
    if (!confirm(`确定要删除 Runtime: ${runtimeId}？\n\n此操作不可逆！`)) {
        return;
    }

    showLoading(button, true);

    try {
        const result = await callRuntimeAPI('step8-cleanup', {
            runtime_id: runtimeId
        });

        const resultText = `✓ Runtime 已删除成功！

Runtime ID: ${runtimeId}
状态: ${result.message}

S3 部署包也已清理（如果存在）。`;

        displayCodeResult(8, resultText, "清理结果");

        // 清除状态
        RuntimeState.clear();
        clearAllInputs();
    } catch (error) {
        displayCodeResult(8, `清理失败: ${error.message}`, "错误");
    } finally {
        showLoading(button, false);
    }
}

// ==================== 辅助函数 ====================

function getStatusClass(status) {
    const statusMap = {
        'READY': 'bg-success',
        'CREATING': 'bg-warning',
        'UPDATING': 'bg-warning',
        'CREATE_FAILED': 'bg-danger',
        'UPDATE_FAILED': 'bg-danger',
        'DELETING': 'bg-secondary'
    };
    return statusMap[status] || 'bg-secondary';
}

// 更新 demo 代码中的变量
async function updateDemoCodeVariables() {
    try {
        // 获取环境配置
        const config = await getEnvironmentConfig();

        // 更新所有 demo 代码中的占位符
        updateCodeSnippets(config);
    } catch (error) {
        console.error('更新代码变量失败:', error);
    }
}

// 获取环境配置（从后端 API 获取）
async function getEnvironmentConfig() {
    try {
        const response = await fetch('/api/runtime/demo/config');
        const data = await response.json();

        if (data.status === 'success') {
            return {
                ACCOUNT_ID: data.config.ACCOUNT_ID,
                REGION: data.config.REGION,
                S3_BUCKET: data.config.S3_BUCKET,
                EXECUTION_ROLE_ARN: data.config.EXECUTION_ROLE_ARN,
                runtime_id: RuntimeState.runtime_id || 'YOUR_RUNTIME_ID',
                runtime_arn: RuntimeState.runtime_arn || 'YOUR_RUNTIME_ARN',
                agent_name: RuntimeState.agent_name || 'runtime_demo_xxx'
            };
        }
    } catch (error) {
        console.error('获取环境配置失败:', error);
    }

    // 降级到默认值
    return {
        ACCOUNT_ID: 'YOUR_ACCOUNT_ID',
        REGION: 'us-west-2',
        S3_BUCKET: 'YOUR_S3_BUCKET',
        EXECUTION_ROLE_ARN: 'YOUR_EXECUTION_ROLE_ARN',
        runtime_id: RuntimeState.runtime_id || 'YOUR_RUNTIME_ID',
        runtime_arn: RuntimeState.runtime_arn || 'YOUR_RUNTIME_ARN',
        agent_name: RuntimeState.agent_name || 'runtime_demo_xxx'
    };
}

// 更新所有代码片段中的占位符
function updateCodeSnippets(config) {
    // 获取所有包含 code-snippet 类的元素
    const codeSnippets = document.querySelectorAll('.runtime-part .code-snippet pre');

    codeSnippets.forEach(snippet => {
        let code = snippet.textContent;

        // 替换所有占位符
        code = code.replace(/\{ACCOUNT_ID\}/g, config.ACCOUNT_ID);
        code = code.replace(/\{REGION\}/g, config.REGION);
        code = code.replace(/\{S3_BUCKET\}/g, config.S3_BUCKET);
        code = code.replace(/\{EXECUTION_ROLE_ARN\}/g, config.EXECUTION_ROLE_ARN);
        code = code.replace(/\{runtime_id\}/g, config.runtime_id);
        code = code.replace(/\{runtime_arn\}/g, config.runtime_arn);
        code = code.replace(/\{agent_name\}/g, config.agent_name);

        // 更新显示
        snippet.textContent = code;
    });
}

function autoFillRuntimeInfo() {
    // 自动填充 Step 6
    const step6RuntimeId = document.getElementById('input-runtime-id');
    if (step6RuntimeId && RuntimeState.runtime_id) {
        step6RuntimeId.value = RuntimeState.runtime_id;
    }

    // 自动填充 Step 7
    const step7RuntimeArn = document.getElementById('input-runtime-arn');
    if (step7RuntimeArn && RuntimeState.runtime_arn) {
        step7RuntimeArn.value = RuntimeState.runtime_arn;
    }

    // 自动填充 Step 8
    const step8RuntimeId = document.getElementById('input-cleanup-runtime-id');
    if (step8RuntimeId && RuntimeState.runtime_id) {
        step8RuntimeId.value = RuntimeState.runtime_id;
    }
}

function clearAllInputs() {
    document.getElementById('input-runtime-id').value = '';
    document.getElementById('input-runtime-arn').value = '';
    document.getElementById('input-cleanup-runtime-id').value = '';
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('已复制到剪贴板');
    }).catch(err => {
        console.error('复制失败:', err);
    });
}

// ==================== 工作空间操作函数 ====================

async function initWorkspace() {
    const btn = document.getElementById('btn-init-workspace');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 初始化中...';

    try {
        const response = await fetch('/api/runtime/demo/workspace/init', {
            method: 'POST',
            credentials: 'include'
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
        btn.innerHTML = '<i class="fas fa-folder-plus me-1"></i> 初始化工作环境';
        WorkspaceState.updateUI();
    }
}

async function cleanupWorkspace() {
    // 确认对话框
    if (!confirm('确定要清理工作环境吗？这将删除所有文件。')) {
        return;
    }

    const btn = document.getElementById('btn-cleanup-workspace');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 清理中...';

    try {
        const response = await fetch('/api/runtime/demo/workspace/cleanup', {
            method: 'POST',
            credentials: 'include'
        });
        const data = await response.json();

        if (data.success) {
            WorkspaceState.initialized = false;
            WorkspaceState.workspace_id = null;
            WorkspaceState.workspace_path = null;
            WorkspaceState.deployment_package_path = null;
            WorkspaceState.updateUI();
            clearWorkspaceOutputs();
            resetCodeTemplates();  // 重置代码编辑器为原始模板
            showToast('成功', '工作环境已清理', 'success');
        } else {
            showToast('失败', data.message, 'error');
        }
    } catch (error) {
        showToast('错误', '清理失败: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-trash me-1"></i> 清理工作环境';
        WorkspaceState.updateUI();
    }
}

function clearWorkspaceOutputs() {
    // 清空所有步骤的输出
    ['part2', 'part3', 'part5-1'].forEach(partId => {
        const outputSection = document.getElementById(`${partId}-output-section`);
        const filesSection = document.getElementById(`${partId}-files-section`);
        if (outputSection) outputSection.style.display = 'none';
        if (filesSection) filesSection.style.display = 'none';
    });
}

// ==================== 命令执行函数（真实执行）====================

function executeStep2Real() {
    const command = document.getElementById('part2-command').value;
    executeCommandReal('part2', command);
}

function executeStep5PackageReal() {
    const command = document.getElementById('part5-1-command').value;
    executeCommandReal('part5-1', command);
}

function executeCommandReal(partId, command) {
    const outputSection = document.getElementById(`${partId}-output-section`);
    const outputLog = document.getElementById(`${partId}-output`);
    const filesSection = document.getElementById(`${partId}-files-section`);
    const filesTree = document.getElementById(`${partId}-files`);
    const statusSpan = document.getElementById(`${partId}-status`);
    const btn = document.getElementById(`btn-step${partId === 'part2' ? '2' : partId === 'part5-1' ? '5-package' : partId}`);

    // 显示输出区，清空旧内容
    outputSection.style.display = 'block';
    outputLog.innerHTML = '';
    filesSection.style.display = 'none';

    // 禁用按钮
    btn.disabled = true;
    const spinner = btn.querySelector('.spinner-border');
    if (spinner) spinner.style.display = 'inline-block';
    statusSpan.innerHTML = '<span class="running">执行中...</span>';
    statusSpan.className = 'execution-status running';

    // 建立 SSE 连接
    const encodedCommand = encodeURIComponent(command);
    const eventSource = new EventSource(`/api/runtime/demo/workspace/execute?command=${encodedCommand}`);

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'stdout':
                appendLogLineReal(outputLog, data.line, 'stdout');
                break;

            case 'stderr':
                appendLogLineReal(outputLog, data.line, 'stderr');
                break;

            case 'heartbeat':
                // 心跳，可以更新状态显示
                statusSpan.innerHTML = '<span class="running">执行中...</span>';
                break;

            case 'done':
                eventSource.close();
                btn.disabled = false;
                if (spinner) spinner.style.display = 'none';

                if (data.success) {
                    statusSpan.innerHTML = `<span class="text-success"><i class="fas fa-check-circle me-1"></i>完成 (${data.duration.toFixed(2)}s)</span>`;
                    statusSpan.className = 'execution-status success';

                    // Part 5-1 打包完成后，启用 Part 5-2 部署按钮
                    if (partId === 'part5-1') {
                        // 设置部署包路径
                        WorkspaceState.deployment_package_path = `${WorkspaceState.workspace_path}/agentcore_runtime_direct_deploy/deployment_package.zip`;

                        // 启用 Part 5-2 按钮
                        const deployBtn = document.getElementById('btn-step5-deploy');
                        if (deployBtn) {
                            deployBtn.disabled = false;
                        }

                        // 替换 Part 5-2 代码中的变量
                        updatePart52Variables();

                        showToast('打包完成', '可以执行部署', 'success');
                    }
                } else {
                    statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>失败 (返回码: ${data.return_code})</span>`;
                    statusSpan.className = 'execution-status error';
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
                if (spinner) spinner.style.display = 'none';
                statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>错误: ${data.message}</span>`;
                statusSpan.className = 'execution-status error';
                break;
        }
    };

    eventSource.onerror = function(event) {
        eventSource.close();
        btn.disabled = false;
        if (spinner) spinner.style.display = 'none';
        statusSpan.innerHTML = '<span class="text-danger"><i class="fas fa-times-circle me-1"></i>连接断开</span>';
        statusSpan.className = 'execution-status error';
    };
}

// 追加日志行
function appendLogLineReal(container, line, type) {
    const lineDiv = document.createElement('div');
    lineDiv.className = type;
    lineDiv.textContent = line;
    container.appendChild(lineDiv);
    // 自动滚动到底部
    container.scrollTop = container.scrollHeight;
}

// ==================== 文件写入函数 ====================

async function writeFileStep3() {
    const filepath = document.getElementById('part3-filepath').value;
    const content = document.getElementById('part3-code').value;
    const filesSection = document.getElementById('part3-files-section');
    const filesTree = document.getElementById('part3-files');
    const statusSpan = document.getElementById('part3-status');
    const btn = document.getElementById('btn-step3');

    btn.disabled = true;
    const spinner = btn.querySelector('.spinner-border');
    if (spinner) spinner.style.display = 'inline-block';
    statusSpan.textContent = '';

    try {
        const response = await fetch('/api/runtime/demo/workspace/write-file', {
            method: 'POST',
            credentials: 'include',
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
            statusSpan.innerHTML = `<span class="text-success"><i class="fas fa-check-circle me-1"></i>文件写入成功 (${formatSize(data.size)})</span>`;
            statusSpan.className = 'execution-status success';

            // 显示文件树
            if (data.files && data.files.length > 0) {
                filesSection.style.display = 'block';
                renderFileTree(filesTree, data.files);
            }
        } else {
            statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>${data.message}</span>`;
            statusSpan.className = 'execution-status error';
        }
    } catch (error) {
        statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>写入失败: ${error.message}</span>`;
        statusSpan.className = 'execution-status error';
    } finally {
        btn.disabled = false;
        if (spinner) spinner.style.display = 'none';
    }
}

// ==================== 文件树渲染 ====================

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
        icon.textContent = file.type === 'directory' ? '📁' : '📄';

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

// ==================== Toast 通知 ====================

function showToast(title, message, type = 'info') {
    // 简单实现：使用 alert，可以后续改成 Bootstrap Toast
    const typeEmoji = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    console.log(`${typeEmoji} ${title}: ${message}`);

    // 可选：使用 Bootstrap Toast
    const toastContainer = document.getElementById('toast-container');
    if (toastContainer && typeof bootstrap !== 'undefined') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'}`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong>: ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    } else {
        // 降级到简单提示
        if (type === 'error') {
            alert(`${title}: ${message}`);
        }
    }
}

// ==================== Part 5-2 部署函数 ====================

/**
 * 更新 Part 5-2 代码中的变量
 */
async function updatePart52Variables() {
    const codeTextarea = document.getElementById('part5-2-code');
    if (!codeTextarea) return;

    let code = codeTextarea.value;

    // 获取环境配置
    const config = await getEnvironmentConfig();

    // 替换变量
    code = code.replace(/\$\{REGION\}/g, config.REGION || 'us-west-2');
    code = code.replace(/\$\{S3_BUCKET\}/g, config.S3_BUCKET || '');
    code = code.replace(/\$\{EXECUTION_ROLE_ARN\}/g, config.EXECUTION_ROLE_ARN || '');
    code = code.replace(/\$\{ACCOUNT_ID\}/g, config.ACCOUNT_ID || '');
    code = code.replace(/\$\{DEPLOYMENT_PACKAGE_PATH\}/g, WorkspaceState.deployment_package_path || '');

    codeTextarea.value = code;
    console.log('Part 5-2 variables updated');
}

/**
 * 执行 Part 5-2 部署 (真实 Python 执行)
 */
async function executeStep5DeployReal() {
    const codeTextarea = document.getElementById('part5-2-code');
    const outputLog = document.getElementById('part5-2-output');
    const filesSection = document.getElementById('part5-2-files-section');
    const filesTree = document.getElementById('part5-2-files');
    const statusSpan = document.getElementById('part5-2-status');
    const btn = document.getElementById('btn-step5-deploy');

    if (!codeTextarea || !outputLog) {
        console.error('Part 5-2 elements not found');
        return;
    }

    const code = codeTextarea.value;

    // 清空输出，禁用按钮
    outputLog.innerHTML = '';
    filesSection.style.display = 'none';
    btn.disabled = true;
    const spinner = btn.querySelector('.spinner-border');
    if (spinner) spinner.style.display = 'inline-block';
    statusSpan.innerHTML = '<span class="running">执行中...</span>';
    statusSpan.className = 'execution-status running';

    try {
        // 使用 fetch POST 发送代码，接收 SSE 响应
        const response = await fetch('/api/runtime/demo/workspace/execute-python', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                session_id: RuntimeState.session_id
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // 读取 SSE 流
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // 处理 SSE 数据
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // 保留不完整的行

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    if (jsonStr.trim()) {
                        try {
                            const data = JSON.parse(jsonStr);
                            handlePart52SSEData(data, outputLog, filesSection, filesTree, statusSpan, btn, spinner);
                        } catch (e) {
                            console.error('JSON parse error:', e, jsonStr);
                        }
                    }
                }
            }
        }
    } catch (error) {
        console.error('Execute Python error:', error);
        btn.disabled = false;
        if (spinner) spinner.style.display = 'none';
        statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>错误: ${error.message}</span>`;
        statusSpan.className = 'execution-status error';
    }
}

/**
 * 处理 Part 5-2 SSE 数据
 */
function handlePart52SSEData(data, outputLog, filesSection, filesTree, statusSpan, btn, spinner) {
    switch (data.type) {
        case 'start':
            appendLogLineReal(outputLog, data.message, 'stdout');
            break;

        case 'stdout':
            appendLogLineReal(outputLog, data.line, 'stdout');
            break;

        case 'stderr':
            appendLogLineReal(outputLog, data.line, 'stderr');
            break;

        case 'done':
            btn.disabled = false;
            if (spinner) spinner.style.display = 'none';

            if (data.success) {
                statusSpan.innerHTML = `<span class="text-success"><i class="fas fa-check-circle me-1"></i>完成 (${data.duration.toFixed(2)}s)</span>`;
                statusSpan.className = 'execution-status success';

                // 如果成功获取到 runtime 信息，更新状态
                if (data.runtime_arn && data.runtime_id) {
                    RuntimeState.runtime_arn = data.runtime_arn;
                    RuntimeState.runtime_id = data.runtime_id;
                    RuntimeState.runtime_version = "1";
                    RuntimeState.agent_name = data.agent_name || '';
                    RuntimeState.save();

                    // 更新 Part 6, 7 的代码变量
                    updatePart67Variables();

                    // 启用 Part 6, 7, 8 按钮
                    const btn6 = document.getElementById('btn-step6');
                    const btn7 = document.getElementById('btn-step7');
                    const btn8 = document.getElementById('btn-step8');
                    if (btn6) btn6.disabled = false;
                    if (btn7) btn7.disabled = false;
                    if (btn8) btn8.disabled = false;

                    showToast('部署成功', `Runtime ID: ${data.runtime_id}`, 'success');
                }
            } else {
                statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>失败 (返回码: ${data.return_code})</span>`;
                statusSpan.className = 'execution-status error';
            }

            // 显示文件树
            if (data.files && data.files.length > 0) {
                filesSection.style.display = 'block';
                renderFileTree(filesTree, data.files);
            }
            break;

        case 'error':
            btn.disabled = false;
            if (spinner) spinner.style.display = 'none';
            statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>错误: ${data.message}</span>`;
            statusSpan.className = 'execution-status error';
            break;
    }
}

// ==================== Part 6/7 执行函数 ====================

/**
 * 更新 Part 6, 7, 8 代码中的变量
 */
async function updatePart67Variables() {
    const config = await getEnvironmentConfig();

    // Part 6
    const code6 = document.getElementById('part6-code');
    if (code6) {
        let c = code6.value;
        c = c.replace(/\$\{REGION\}/g, config.REGION || 'us-west-2');
        c = c.replace(/\$\{RUNTIME_ID\}/g, RuntimeState.runtime_id || '');
        code6.value = c;
    }

    // Part 7
    const code7 = document.getElementById('part7-code');
    if (code7) {
        let c = code7.value;
        c = c.replace(/\$\{REGION\}/g, config.REGION || 'us-west-2');
        c = c.replace(/\$\{RUNTIME_ARN\}/g, RuntimeState.runtime_arn || '');
        code7.value = c;
    }

    // Part 8
    const code8 = document.getElementById('part8-code');
    if (code8) {
        let c = code8.value;
        c = c.replace(/\$\{REGION\}/g, config.REGION || 'us-west-2');
        c = c.replace(/\$\{RUNTIME_ID\}/g, RuntimeState.runtime_id || '');
        c = c.replace(/\$\{S3_BUCKET\}/g, config.S3_BUCKET || '');
        c = c.replace(/\$\{AGENT_NAME\}/g, RuntimeState.agent_name || '');
        code8.value = c;
    }

    console.log('Part 6/7/8 variables updated');
}

/**
 * 执行 Part 6 检查状态 (真实 Python 执行)
 */
async function executeStep6Real() {
    await executePythonCode('part6');
}

/**
 * 执行 Part 7 调用 Agent (真实 Python 执行)
 */
async function executeStep7Real() {
    await executePythonCode('part7');
}

/**
 * 执行 Part 8 清理 Runtime (真实 Python 执行)
 */
async function executeStep8Real() {
    await executePythonCode('part8');
}

/**
 * 通用 Python 代码执行函数
 */
async function executePythonCode(partId) {
    const codeTextarea = document.getElementById(`${partId}-code`);
    const outputLog = document.getElementById(`${partId}-output`);
    const statusSpan = document.getElementById(`${partId}-status`);
    // 根据 partId 获取按钮 ID
    const btnId = partId === 'part6' ? '6' : partId === 'part7' ? '7' : '8';
    const btn = document.getElementById(`btn-step${btnId}`);

    if (!codeTextarea || !outputLog) {
        console.error(`${partId} elements not found`);
        return;
    }

    const code = codeTextarea.value;

    // 清空输出，禁用按钮
    outputLog.innerHTML = '';
    btn.disabled = true;
    const spinner = btn.querySelector('.spinner-border');
    if (spinner) spinner.style.display = 'inline-block';
    statusSpan.innerHTML = '<span class="running">执行中...</span>';
    statusSpan.className = 'execution-status running';

    try {
        const response = await fetch('/api/runtime/demo/workspace/execute-python', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                session_id: RuntimeState.session_id
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // 读取 SSE 流
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    if (jsonStr.trim()) {
                        try {
                            const data = JSON.parse(jsonStr);
                            handleGenericPythonSSE(data, outputLog, statusSpan, btn, spinner, partId);
                        } catch (e) {
                            console.error('JSON parse error:', e, jsonStr);
                        }
                    }
                }
            }
        }
    } catch (error) {
        console.error(`Execute ${partId} error:`, error);
        btn.disabled = false;
        if (spinner) spinner.style.display = 'none';
        statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>错误: ${error.message}</span>`;
        statusSpan.className = 'execution-status error';
    }
}

/**
 * 处理通用 Python 执行 SSE 数据
 * @param {string} partId - 可选，用于特殊处理（如 part8）
 */
function handleGenericPythonSSE(data, outputLog, statusSpan, btn, spinner, partId = null) {
    switch (data.type) {
        case 'start':
            appendLogLineReal(outputLog, data.message, 'stdout');
            break;

        case 'stdout':
            appendLogLineReal(outputLog, data.line, 'stdout');
            break;

        case 'stderr':
            appendLogLineReal(outputLog, data.line, 'stderr');
            break;

        case 'done':
            btn.disabled = false;
            if (spinner) spinner.style.display = 'none';

            if (data.success) {
                statusSpan.innerHTML = `<span class="text-success"><i class="fas fa-check-circle me-1"></i>完成 (${data.duration.toFixed(2)}s)</span>`;
                statusSpan.className = 'execution-status success';

                // Part 8 成功后清除 Runtime 关联
                if (partId === 'part8') {
                    clearWorkspaceRuntime();
                }
            } else {
                statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>失败 (返回码: ${data.return_code})</span>`;
                statusSpan.className = 'execution-status error';
            }
            break;

        case 'error':
            btn.disabled = false;
            if (spinner) spinner.style.display = 'none';
            statusSpan.innerHTML = `<span class="text-danger"><i class="fas fa-times-circle me-1"></i>错误: ${data.message}</span>`;
            statusSpan.className = 'execution-status error';
            break;
    }
}

/**
 * 清除工作空间的 Runtime 关联
 */
async function clearWorkspaceRuntime() {
    try {
        const response = await fetch('/api/runtime/demo/workspace/clear-runtime', {
            method: 'POST',
            credentials: 'include'
        });
        const data = await response.json();

        if (data.success) {
            console.log('Workspace runtime association cleared:', data.cleared_runtime_id);

            // 清除前端状态
            RuntimeState.runtime_arn = null;
            RuntimeState.runtime_id = null;
            RuntimeState.agent_name = null;
            RuntimeState.save();

            // 更新工作空间状态
            WorkspaceState.runtime_id = null;

            // 禁用 Part 6, 7, 8 按钮
            const btn6 = document.getElementById('btn-step6');
            const btn7 = document.getElementById('btn-step7');
            const btn8 = document.getElementById('btn-step8');
            if (btn6) btn6.disabled = true;
            if (btn7) btn7.disabled = true;
            if (btn8) btn8.disabled = true;

            showToast('清理完成', 'Runtime 已删除，可以清理工作环境', 'success');
        } else {
            console.error('Failed to clear workspace runtime:', data.message);
        }
    } catch (error) {
        console.error('Error clearing workspace runtime:', error);
    }
}

// ==================== 代码模板管理 ====================

/**
 * 保存所有代码编辑器的原始模板
 */
function saveCodeTemplates() {
    const codeEditors = ['part5-2-code', 'part6-code', 'part7-code', 'part8-code'];
    codeEditors.forEach(id => {
        const editor = document.getElementById(id);
        if (editor) {
            CODE_TEMPLATES[id] = editor.value;
        }
    });
    console.log('Code templates saved:', Object.keys(CODE_TEMPLATES));
}

/**
 * 重置代码编辑器为原始模板
 */
function resetCodeTemplates() {
    Object.keys(CODE_TEMPLATES).forEach(id => {
        const editor = document.getElementById(id);
        if (editor && CODE_TEMPLATES[id]) {
            editor.value = CODE_TEMPLATES[id];
        }
    });
    console.log('Code templates reset');
}

// ==================== 页面初始化 ====================

document.addEventListener('DOMContentLoaded', async function() {
    console.log('Runtime Demo page loaded');

    // 保存原始代码模板（必须在任何变量替换之前）
    saveCodeTemplates();

    // 加载工作空间状态
    await WorkspaceState.load();

    // 加载 Runtime 状态
    RuntimeState.load();

    // 自动填充已保存的信息
    autoFillRuntimeInfo();

    // 更新 demo 代码中的环境变量
    updateDemoCodeVariables();

    // 如果已有 Runtime 信息，更新 Part 6/7/8 的代码变量并启用按钮
    if (RuntimeState.runtime_id && RuntimeState.runtime_arn) {
        await updatePart67Variables();
        // 启用 Part 6, 7, 8 按钮
        const btn6 = document.getElementById('btn-step6');
        const btn7 = document.getElementById('btn-step7');
        const btn8 = document.getElementById('btn-step8');
        if (btn6) btn6.disabled = false;
        if (btn7) btn7.disabled = false;
        if (btn8) btn8.disabled = false;
    }

    // 绑定按钮事件（通过全局函数，HTML 中 onclick 调用）
    console.log('Session ID:', RuntimeState.session_id);
});
