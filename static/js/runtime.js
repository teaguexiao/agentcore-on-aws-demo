/**
 * AgentCore Runtime Demo - Frontend Logic
 *
 * 管理 Runtime 演示页面的所有交互逻辑
 */

// ==================== 状态管理 ====================

const RuntimeState = {
    session_id: generateSessionId(),
    runtime_arn: null,
    runtime_id: null,
    runtime_version: "1",
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

// ==================== 页面初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Runtime Demo page loaded');

    // 加载状态
    RuntimeState.load();

    // 自动填充已保存的信息
    autoFillRuntimeInfo();

    // 更新 demo 代码中的环境变量
    updateDemoCodeVariables();

    // 绑定按钮事件（通过全局函数，HTML 中 onclick 调用）
    console.log('Session ID:', RuntimeState.session_id);
});
