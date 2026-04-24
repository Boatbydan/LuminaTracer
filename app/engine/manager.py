# app/engine/manager.py
import traceback

# 尝试导入 C++ 模块，防止开发环境未编译时直接报错崩溃
try:
    from . import vision_strategy_cpp
except ImportError:
    vision_strategy_cpp = None
    print("[WARNING] 'vision_strategy_cpp' module not found. C++ features will fail.")

# 导入配置
from ..config import Config

class TestManager:
    """
    测试会话管理器 (Singleton 单例模式)
    负责管理所有活跃用户的 C++ 策略对象实例。
    """
    _instance = None

    def __new__(cls):
        """确保全局只有一个管理器实例"""
        if cls._instance is None:
            cls._instance = super(TestManager, cls).__new__(cls)
            # 初始化存储字典
            cls._instance.sessions = {}
        return cls._instance

    def get_strategy(self, session_id, width=None, height=None, params=None):
        """
        获取或创建策略实例。
        如果 session_id 已存在，直接返回；
        如果不存在，则根据 params 创建新的 C++ 策略对象。
        """
        # 1. 检查缓存
        if session_id in self.sessions:
            return self.sessions[session_id]

        # 2. 如果是请求创建新会话 (带有参数)
        if width is not None and params is not None:
            if vision_strategy_cpp is None:
                raise RuntimeError("C++ Core Module is missing! Cannot start test.")

            print(f"[Manager] Creating new strategy for {session_id}")
            
            try:
                # --- 调用 C++ 构造函数 ---
                # 传入: 宽, 高, 参数字典
                strategy = vision_strategy_cpp.VisionStrategy(int(width), int(height), params)
                
                # 存入内存字典
                self.sessions[session_id] = strategy
                return strategy
            except Exception as e:
                print(f"[Manager] Critical Error: Failed to instantiate C++ module: {e}")
                traceback.print_exc()
                raise e
        
        # 3. 如果既不在内存里，又没传参数 (比如服务器重启了)
        return None

    def remove_strategy(self, session_id):
        """测试结束或中断后，清理内存"""
        if session_id in self.sessions:
            try:
                del self.sessions[session_id]
                print(f"[Manager] Session {session_id} cleaned up.")
            except Exception as e:
                print(f"[Manager] Error cleaning up session: {e}")

    # 兼容性别名 (如果有些旧代码调用 cleanup)
    def cleanup(self, session_id):
        self.remove_strategy(session_id)