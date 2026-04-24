import os
import sys
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# 全局扩展对象
db = SQLAlchemy()
login_manager = LoginManager()


def get_base_dir():
    """获取项目根目录"""
    if getattr(sys, 'frozen', False):
        # 打包后的 exe 环境
        return Path(os.environ.get('LUMINA_BASE_PATH', sys._MEIPASS))
    else:
        # 开发环境
        return Path(__file__).parent.parent


def get_data_dir():
    """获取数据目录"""
    if getattr(sys, 'frozen', False):
        # 打包后的 exe 环境 - 使用 exe 所在目录的 data 文件夹
        exe_dir = Path(sys.executable).parent
        data_dir = exe_dir / 'data'
    else:
        # 开发环境 - 使用项目目录
        data_dir = get_base_dir() / 'data'

    # 确保目录存在
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_uri():
    """获取数据库 URI"""
    db_path = get_data_dir() / 'lumina_cloud.db'
    # Windows 路径需要转换为正斜杠
    db_path_str = str(db_path).replace('\\', '/')
    return os.environ.get('DATABASE_URL') or f'sqlite:///{db_path_str}'


def create_app():
    # 1. 路径配置
    base_dir = get_base_dir()
    template_dir = base_dir / 'templates'
    static_dir = base_dir / 'static'

    app = Flask(__name__,
                template_folder=str(template_dir),
                static_folder=str(static_dir))

    # 2. 加载配置
    # 确保数据目录存在
    data_dir = get_data_dir()
    print(f"[Config] Data directory: {data_dir}")
    
    # 设置所有配置项
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-please-change')
    app.config['SQLALCHEMY_DATABASE_URI'] = get_db_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEFAULT_THEME'] = os.environ.get('DEFAULT_THEME', 'hfa_sim')

    # 3. 初始化核心扩展
    db.init_app(app)
    login_manager.init_app(app)
    
    # 设置未登录时的跳转页面
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "请先登录以访问此页面。"

    # 数据库迁移工具
    migrate = Migrate(app, db)

    # 4. 注册蓝图
    from .routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from .routes.views import bp as views_bp
    app.register_blueprint(views_bp)
    
    from .routes.api import bp as api_bp
    app.register_blueprint(api_bp)

    # 5. 数据库初始化
    with app.app_context():
        from . import models 
        db.create_all()

    return app


# 用户加载回调
@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))
