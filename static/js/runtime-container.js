/**
 * AgentCore Runtime Container Deployment - Frontend Logic
 *
 * 管理 Container Deployment 页面的所有交互逻辑
 */

// ==================== 状态管理 ====================

const ContainerRuntimeState = {
    session_id: generateSessionId(),
    deployment_type: "container",
    runtime_arn: null,
    runtime_id: null,
    runtime_version: "1",
    ecr_image_uri: null,
    agent_name: null,
    created_at: null,

    save() {
        localStorage.setItem('container_runtime_state', JSON.stringify(this));
    },

    load() {
        const saved = localStorage.getItem('container_runtime_state');
        if (saved) {
            try {
                const data = JSON.parse(saved);
                Object.assign(this, data);
                console.log('Container Runtime state loaded:', this);
            } catch (e) {
                console.error('Failed to load container state:', e);
            }
        }
    },

    clear() {
        this.runtime_arn = null;
        this.runtime_id = null;
        this.ecr_image_uri = null;
        this.agent_name = null;
        this.created_at = null;
        localStorage.removeItem('container_runtime_state');
        console.log('Container Runtime state cleared');
    }
};

// ==================== Container Step 执行函数 ====================

async function executeContainerStep1() {
    const button = document.getElementById('btn-container-step1');
    showLoading(button, true);
    showLogArea('container-1');

    const url = `/api/runtime/demo/container/step1-stream?session_id=${ContainerRuntimeState.session_id}`;

    connectSSE(url, 'container-1', (result) => {
        showLoading(button, false);
        if (result.success) {
            displayCodeResult('container-1', result.data.output, "执行结果");
        } else {
            displayCodeResult('container-1', `错误: ${result.error}`, "执行失败");
        }
    });
}

async function executeContainerStep2() {
    const button = document.getElementById('btn-container-step2');
    showLoading(button, true);
    showLogArea('container-2');

    const url = `/api/runtime/demo/container/step2-stream?session_id=${ContainerRuntimeState.session_id}`;

    connectSSE(url, 'container-2', (result) => {
        showLoading(button, false);
        if (result.success) {
            displayCodeResult('container-2', result.data.output, "执行结果");
        } else {
            displayCodeResult('container-2', `错误: ${result.error}`, "执行失败");
        }
    });
}

async function executeContainerStep3() {
    const button = document.getElementById('btn-container-step3');
    showLoading(button, true);
    showLogArea('container-3');

    const url = `/api/runtime/demo/container/step3-stream?session_id=${ContainerRuntimeState.session_id}`;

    connectSSE(url, 'container-3', (result) => {
        showLoading(button, false);
        if (result.success) {
            displayCodeResult('container-3', result.data.output, "执行结果");
        } else {
            displayCodeResult('container-3', `错误: ${result.error}`, "执行失败");
        }
    });
}

async function executeContainerStep4() {
    const button = document.getElementById('btn-container-step4');
    showLoading(button, true);
    showLogArea('container-4');

    const url = `/api/runtime/demo/container/step4-stream?session_id=${ContainerRuntimeState.session_id}`;

    connectSSE(url, 'container-4', (result) => {
        showLoading(button, false);
        if (result.success) {
            displayCodeResult('container-4', result.data.output, "执行结果");
        } else {
            displayCodeResult('container-4', `错误: ${result.error}`, "执行失败");
        }
    });
}

async function executeContainerStep5() {
    const button = document.getElementById('btn-container-step5');
    showLoading(button, true);
    showLogArea('container-5');

    const url = `/api/runtime/demo/container/step5-stream?session_id=${ContainerRuntimeState.session_id}`;

    connectSSE(url, 'container-5', (result) => {
        showLoading(button, false);
        if (result.success) {
            const resultText = `✓ 构建推送完成！

ECR Image URI: ${result.data.ecr_image_uri}`;
            displayCodeResult('container-5', resultText, "执行结果");
        } else {
            displayCodeResult('container-5', `错误: ${result.error}`, "执行失败");
        }
    });
}

async function executeContainerStep6() {
    const button = document.getElementById('btn-container-step6');
    showLoading(button, true);
    showLogArea('container-6');

    const url = `/api/runtime/demo/container/step6-stream?session_id=${ContainerRuntimeState.session_id}`;

    connectSSE(url, 'container-6', (result) => {
        showLoading(button, false);

        if (result.success) {
            const data = result.data;

            // 保存 runtime 信息到状态
            ContainerRuntimeState.runtime_arn = data.runtime_arn;
            ContainerRuntimeState.runtime_id = data.runtime_id;
            ContainerRuntimeState.runtime_version = data.runtime_version;
            ContainerRuntimeState.agent_name = data.agent_name;
            ContainerRuntimeState.ecr_image_uri = data.ecr_image_uri;
            ContainerRuntimeState.created_at = Date.now();
            ContainerRuntimeState.save();

            // 自动填充到后续步骤
            autoFillContainerRuntimeInfo();

            // 更新 demo 代码中的变量
            updateContainerDemoCodeVariables();

            const resultText = `✓ Container Runtime 部署成功！

Runtime ARN: ${data.runtime_arn}
Runtime ID: ${data.runtime_id}
Runtime Version: ${data.runtime_version}
Agent Name: ${data.agent_name}
ECR Image URI: ${data.ecr_image_uri}

已自动填充到 Part 8, 9, 10 的输入框和代码示例中。`;

            displayCodeResult('container-6', resultText, "部署结果");
        } else {
            displayCodeResult('container-6', `部署失败: ${result.error}`, "错误");
        }
    });
}

async function executeContainerStep7() {
    const button = document.getElementById('btn-container-step7');
    const runtimeIdInput = document.getElementById('input-container-runtime-id');
    const runtimeVersionInput = document.getElementById('input-container-runtime-version');

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

        displayCodeResult('container-7', statusInfo, "Runtime 状态");
    } catch (error) {
        displayCodeResult('container-7', `错误: ${error.message}`, "查询失败");
    } finally {
        showLoading(button, false);
    }
}

async function executeContainerStep8() {
    const button = document.getElementById('btn-container-step8');
    const runtimeArnInput = document.getElementById('input-container-runtime-arn');
    const sessionIdInput = document.getElementById('input-container-session-id');
    const promptInput = document.getElementById('input-container-prompt');

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
        const requestData = {
            runtime_arn: runtimeArn,
            runtime_session_id: sessionId,
            prompt: prompt,
            deployment_type: "container"  // Container Deployment
        };

        console.log('Container Deployment 调用参数:', requestData);

        const result = await callRuntimeAPI('step7-invoke', requestData);

        const responseText = `调用成功！耗时: ${result.execution_time}

Prompt:
${result.prompt}

Agent 响应:
${JSON.stringify(result.response, null, 2)}`;

        displayCodeResult('container-8', responseText, "Agent 响应");
    } catch (error) {
        displayCodeResult('container-8', `调用失败: ${error.message}`, "错误");
    } finally {
        showLoading(button, false);
    }
}

async function executeContainerStep9() {
    const button = document.getElementById('btn-container-step9');
    const runtimeIdInput = document.getElementById('input-container-cleanup-id');

    const runtimeId = runtimeIdInput.value.trim();

    if (!runtimeId) {
        showError('请输入 Runtime ID');
        return;
    }

    // 确认删除
    if (!confirm(`确定要删除 Container Runtime: ${runtimeId}？\n\n此操作不可逆！\n注意: ECR 镜像不会被删除。`)) {
        return;
    }

    showLoading(button, true);

    try {
        const result = await callRuntimeAPI('step8-cleanup', {
            runtime_id: runtimeId
        });

        const resultText = `✓ Container Runtime 已删除成功！

Runtime ID: ${runtimeId}
状态: ${result.message}

注意: ECR 镜像未删除，需要手动管理。`;

        displayCodeResult('container-9', resultText, "清理结果");

        // 清除状态
        ContainerRuntimeState.clear();
        clearContainerInputs();
    } catch (error) {
        displayCodeResult('container-9', `清理失败: ${error.message}`, "错误");
    } finally {
        showLoading(button, false);
    }
}

// ==================== 辅助函数 ====================

async function updateContainerDemoCodeVariables() {
    try {
        // 获取 Container 配置
        const response = await fetch('/api/runtime/demo/container/config');
        const data = await response.json();

        if (data.status === 'success') {
            const config = {
                ...data.config,
                runtime_id: ContainerRuntimeState.runtime_id || 'YOUR_RUNTIME_ID',
                runtime_arn: ContainerRuntimeState.runtime_arn || 'YOUR_RUNTIME_ARN',
                agent_name: ContainerRuntimeState.agent_name || 'container_demo_xxx'
            };

            // 更新 Container Tab 中的代码片段
            updateContainerCodeSnippets(config);
        }
    } catch (error) {
        console.error('更新 Container 代码变量失败:', error);
    }
}

function updateContainerCodeSnippets(config) {
    // 只更新 Container Tab 中的代码片段
    const containerTab = document.getElementById('container-tab');
    if (!containerTab) return;

    const codeSnippets = containerTab.querySelectorAll('.runtime-part .code-snippet pre');

    codeSnippets.forEach(snippet => {
        let code = snippet.textContent;

        // 替换所有占位符
        code = code.replace(/\{ACCOUNT_ID\}/g, config.ACCOUNT_ID);
        code = code.replace(/\{REGION\}/g, config.REGION);
        code = code.replace(/\{CONTAINER_ECR_REPOSITORY_NAME\}/g, config.CONTAINER_ECR_REPOSITORY_NAME);
        code = code.replace(/\{CONTAINER_IMAGE_TAG\}/g, config.CONTAINER_IMAGE_TAG);
        code = code.replace(/\{CONTAINER_EXECUTION_ROLE_ARN\}/g, config.CONTAINER_EXECUTION_ROLE_ARN);
        code = code.replace(/\{ECR_IMAGE_URI\}/g, config.ECR_IMAGE_URI);
        code = code.replace(/\{runtime_id\}/g, config.runtime_id);
        code = code.replace(/\{runtime_arn\}/g, config.runtime_arn);
        code = code.replace(/\{agent_name\}/g, config.agent_name);

        // 更新显示
        snippet.textContent = code;
    });
}

function autoFillContainerRuntimeInfo() {
    // 自动填充 Step 7 (Part 8)
    const step7RuntimeId = document.getElementById('input-container-runtime-id');
    if (step7RuntimeId && ContainerRuntimeState.runtime_id) {
        step7RuntimeId.value = ContainerRuntimeState.runtime_id;
    }

    // 自动填充 Step 8 (Part 9)
    const step8RuntimeArn = document.getElementById('input-container-runtime-arn');
    if (step8RuntimeArn && ContainerRuntimeState.runtime_arn) {
        step8RuntimeArn.value = ContainerRuntimeState.runtime_arn;
    }

    // 自动填充 Step 9 (Part 10)
    const step9RuntimeId = document.getElementById('input-container-cleanup-id');
    if (step9RuntimeId && ContainerRuntimeState.runtime_id) {
        step9RuntimeId.value = ContainerRuntimeState.runtime_id;
    }
}

function clearContainerInputs() {
    const inputIds = [
        'input-container-runtime-id',
        'input-container-runtime-arn',
        'input-container-cleanup-id'
    ];

    inputIds.forEach(id => {
        const input = document.getElementById(id);
        if (input) input.value = '';
    });
}

// ==================== 页面初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Container Runtime Demo page loaded');

    // 加载状态
    ContainerRuntimeState.load();

    // 自动填充已保存的信息
    autoFillContainerRuntimeInfo();

    // 更新 demo 代码中的环境变量
    updateContainerDemoCodeVariables();

    console.log('Container Session ID:', ContainerRuntimeState.session_id);
});
