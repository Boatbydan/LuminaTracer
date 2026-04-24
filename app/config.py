import os
import sys
from pathlib import Path


class Config:
    """应用配置类"""
    
    @staticmethod
    def _get_base_dir():
        """获取项目根目录"""
        if getattr(sys, 'frozen', False):
            # 打包后的 exe 环境
            return Path(os.environ.get('LUMINA_BASE_PATH', sys._MEIPASS))
        else:
            # 开发环境
            return Path(__file__).parent.parent
    
    @staticmethod
    def _get_data_dir():
        """获取数据目录"""
        if getattr(sys, 'frozen', False):
            # 打包后的 exe 环境 - 使用用户目录
            data_dir = Path.home() / '.lumina_tracer' / 'data'
        else:
            # 开发环境 - 使用项目目录
            data_dir = Config._get_base_dir() / 'data'
        
        # 确保目录存在
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    @classmethod
    def get_db_path(cls):
        """获取数据库路径"""
        return cls._get_data_dir() / 'lumina_cloud.db'
    
    @classmethod
    def get_db_uri(cls):
        """获取数据库 URI"""
        db_path = cls.get_db_path()
        # Windows 路径需要转换为正斜杠
        # SQLAlchemy SQLite URI 格式: sqlite:///path/to/db
        # 对于 Windows 绝对路径: sqlite:///C:/path/to/db
        db_path_str = str(db_path).replace('\\', '/')
        return os.environ.get('DATABASE_URL') or f'sqlite:///{db_path_str}'
    
    # --- 1. 路径配置 ---
    DB_NAME = 'lumina_cloud.db'
    
    # --- 2. SQLAlchemy 核心配置 ---
    # 使用类方法动态获取
    @classmethod
    def init_app(cls, app=None):
        """初始化配置"""
        # 确保数据目录存在
        data_dir = cls._get_data_dir()
        print(f"[Config] Data directory: {data_dir}")
        
        # 如果传入 app，设置数据库 URI
        if app:
            app.config['SQLALCHEMY_DATABASE_URI'] = cls.get_db_uri()
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 这些属性会在首次访问时计算
    @property
    def DB_FOLDER(self):
        return str(self._get_data_dir())
    
    @property
    def DB_PATH(self):
        return str(self.get_db_path())
    
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return self.get_db_uri()
    
    # 关闭对象修改追踪 (节省内存)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- 3. 安全密钥 ---
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change')
    
    # --- 4. 测试配置 ---
    DEFAULT_THEME = os.environ.get('DEFAULT_THEME', 'hfa_sim')


# 为了兼容旧代码，创建实例
config = Config()

# 将属性暴露为类属性（用于 from config import Config）
Config.DB_FOLDER = property(lambda self: self._get_data_dir())
Config.DB_PATH = property(lambda self: self.get_db_path())
Config.SQLALCHEMY_DATABASE_URI = property(lambda self: self.get_db_uri())
