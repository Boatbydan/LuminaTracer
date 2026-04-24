/**
 * static/js/main.js
 * VisionChecker 核心测试逻辑 (最终修正版)
 */

const VisionTest = (function() {
    // --- 1. 配置与初始化 ---
    // 从 HTML 读取 Python 注入的配置
    const config = window.TEST_CONFIG || {};
    const sessionId = config.sessionId; // 关键：必须用后端的 Session ID

    // UI 配置 (保留你旧代码中的手感配置)
    const UI_CONFIG = {
        STIMULUS_DURATION: 200,   // 光点闪烁时间
        RESPONSE_WINDOW: 1500,    // 等待反应时间
        DELAY_BASE: 400,          // 最小间隔
        DELAY_RANDOM: 500         // 随机间隔增量
    };

    // DOM 元素获取
    const canvas = document.getElementById('visionCanvas'); // 修正 ID
    const ctx = canvas.getContext('2d');
    const btnStop = document.getElementById('btn-stop');

    // 状态变量
    let isTesting = true;
    let currentPointId = -1;
    let userResponded = false;
    let startTime = 0; // 用于计算反应时间

    // --- 2. 初始化流程 ---
    function init() {
        if (!sessionId) {
            alert("错误：无法获取 Session ID，请重新登录");
            return;
        }

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        bindEvents();

        // 1秒后自动开始，让用户适应黑暗
        setTimeout(() => {
            nextStimulus();
        }, 1000);
    }

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        drawFixation(); // 每次调整大小都要重画注视点
    }

    // --- 3. 绘图函数 ---
    
    // 绘制中心红十字 (替代旧代码的 DOM 元素)
    function drawFixation() {
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const size = 20;

        ctx.beginPath();
        ctx.strokeStyle = '#800000'; // 暗红色
        ctx.lineWidth = 3;
        // 横线
        ctx.moveTo(cx - size, cy); 
        ctx.lineTo(cx + size, cy);
        // 竖线
        ctx.moveTo(cx, cy - size); 
        ctx.lineTo(cx, cy + size);
        ctx.stroke();
    }

    // 绘制光点
    function drawStimulus(x, y, size, alpha) {
        ctx.beginPath();
        ctx.arc(x, y, size, 0, 2 * Math.PI);
        // 使用后端返回的 alpha (0~1)
        ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
        ctx.fill();
    }

    // --- 4. 核心测试循环 ---
    function nextStimulus() {
        if (!isTesting) return;

        // 清理画布，重画注视点
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawFixation();
        userResponded = false;

        // 请求后端获取下一个点
        fetch('/api/test/next', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId, // 传回正确的 Session ID
                window_width: canvas.width,
                window_height: canvas.height,
                // 这里不需要传 params: TEST_CONFIG，因为后端 Session 已保存了配置
            })
        })
        .then(res => res.json())
        .then(data => {
            // 1. 检查是否结束
            if (data.status === 'finished') {
                window.location.href = `/analysis/report/${sessionId}`;
                return;
            }
            if (data.status === 'error') {
                alert("系统错误: " + data.msg);
                return;
            }

            // 2. 准备显示：计算随机延迟
            currentPointId = data.point_id;
            const delay = UI_CONFIG.DELAY_BASE + Math.random() * UI_CONFIG.DELAY_RANDOM;

            setTimeout(() => {
                if (!isTesting) return;

                // 3. 绘制光点
                drawStimulus(data.x, data.y, data.size, data.alpha);
                startTime = Date.now(); // 记录展示时间戳

                // 4. 光点持续时间 (Flash Duration)
                setTimeout(() => {
                    if (!isTesting) return;
                    
                    // 擦除光点 (重画注视点即可覆盖)
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    drawFixation();

                    // 5. 等待用户反应 (Response Window)
                    setTimeout(submitResult, UI_CONFIG.RESPONSE_WINDOW);

                }, UI_CONFIG.STIMULUS_DURATION);

            }, delay);
        })
        .catch(err => console.error("API Error:", err));
    }

    function submitResult() {
        if (!isTesting) return;

        // 计算反应时间 (如果是超时没按，这里没意义，但在后端分析可能有用)
        const rt = userResponded ? (Date.now() - startTime) : -1;

        fetch('/api/test/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                point_id: currentPointId,
                seen: userResponded,
                reaction_time: rt
            })
        })
        .then(() => {
            // 提交成功后，立即进入下一次循环
            nextStimulus();
        })
        .catch(err => console.error("Submit Error:", err));
    }

    // --- 5. 交互控制 ---
    
    // 停止测试 (供 HTML 按钮调用)
    function stopTest() {
        if (!isTesting) return;
        isTesting = false;

        document.body.style.cursor = 'default';
        if(btnStop) {
            btnStop.innerText = "生成报告中...";
            btnStop.style.background = "#666";
        }

        fetch('/api/test/next', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                action: 'stop' // 发送停止信号
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'finished') {
                window.location.href = `/analysis/report/${sessionId}`;
            }
        });
    }

    // 绑定键盘事件
    function bindEvents() {
        document.addEventListener('keydown', (e) => {
            if (!isTesting) return;

            // 空格键：看见了
            if (e.code === 'Space') {
                if (!userResponded) {
                    userResponded = true;
                    // 可选：给个微小的反馈，比如注视点变亮一下
                    console.log("Input: Seen"); 
                }
            } 
            // ESC键：退出
            else if (e.code === 'Escape') {
                stopTest();
            }
        });
    }

    // --- 6. 启动 ---
    init();

    // 暴露给全局的方法
    return {
        stopTest: stopTest
    };

})();