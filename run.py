import sys
import threading
import time
import os
import socket
from app import create_app

# --- 1. 创建应用实例 ---
app = create_app()

# --- 2. 配置端口 ---
# 建议固定端口，方便 GUI 连接
DEFAULT_PORT = 5000
HOST = "127.0.0.1"


def find_available_port(start_port):
    """查找可用的端口"""
    port = start_port
    while port < start_port + 100:  # 最多尝试100个端口
        try:
            # 尝试绑定端口
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, port))
            return port
        except OSError:
            port += 1
    raise Exception(f"No available port found starting from {start_port}")

# 查找可用端口
PORT = find_available_port(DEFAULT_PORT)
BASE_URL = f"http://{HOST}:{PORT}"
print(f"[Config] Server will start on {BASE_URL}")

def start_server():
    """在子线程中启动 Flask 服务器"""
    # 注意：在 GUI 模式下，必须禁用 reloader (use_reloader=False)
    # 否则 Flask 会启动两个进程，导致 GUI 线程混乱或无法关闭
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)

def start_gui():
    """启动 PyWebview 窗口"""
    import webview
    import ctypes

    # Windows 高分屏适配 (防止模糊)
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    # 等待一小会儿，确保 Flask 线程已经启动并开始监听
    time.sleep(1)

    webview.create_window(
        title='Lumina Tracer - Professional Client',
        url=BASE_URL,
        width=1280,
        height=850,
        min_size=(1024, 768),
        resizable=True,
        confirm_close=True,
        text_select=False
    )
    
    # 启动 GUI 循环 (必须在主线程)
    webview.start(debug=False) # 开发时开启 debug，发布时可关掉

if __name__ == '__main__':
    # 检测是否在打包环境中运行 (frozen)
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe，强制 GUI 模式
        is_gui = True
    else:
        # 开发环境看参数
        # is_gui = '--gui' in sys.argv
        is_gui = True

    if is_gui:
        # ... 启动 GUI 逻辑 ...
        server_thread = threading.Thread(target=start_server)
        server_thread.daemon = True 
        server_thread.start()
        start_gui()
    else:
        # ... 启动 Web 逻辑 ...
        app.run(host='0.0.0.0', port=PORT, debug=True)