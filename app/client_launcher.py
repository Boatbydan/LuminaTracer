import webview
import sys
import ctypes

# --- 配置区域 ---

# 1. 开发阶段：指向本地 Flask 服务器
TARGET_URL = "http://127.0.0.1:5000"

# 2. 部署阶段：指向云服务器域名
# TARGET_URL = "https://www.lumina-tracer.com" 

def on_window_close():
    print("Lumina Client is closing...")

def start_client():
    # Windows 高分屏适配 (防止界面模糊)
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    # 创建窗口
    # confirm_close=True: 用户点击关闭时会弹出确认框
    window = webview.create_window(
        title='Lumina Tracer - Professional Vision Analysis',
        url=TARGET_URL,
        width=1280,
        height=800,
        min_size=(1024, 768),
        resizable=True,
        confirm_close=True,
        text_select=False,  # 禁止像网页一样选中文本，更像原生软件
    )

    # 启动 GUI 循环
    # debug=True: 允许你按 F12 打开控制台调试 (发布时改为 False)
    webview.start(func=None, debug=True)

if __name__ == '__main__':
    start_client()