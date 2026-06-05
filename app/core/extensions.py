"""
Core Extensions Initialization

将 Flask 扩展的初始化逻辑从 app/__init__.py 中提取出来，
形成独立的核心层，供 create_app() 调用。

职责:
- SQLAlchemy (db)
- Flask Login (login_manager)  
- Flask Migrate (Migrate)

设计原则:
- 扩展对象在此创建但不绑定 app
- 绑定操作通过 init_extensions(app) 完成
- 全局单例，各模块通过 from app import db 引用
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_babel import Babel

db = SQLAlchemy()
login_manager = LoginManager()
babel = Babel()


def init_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = "请先登录以访问此页面。"

    migrate = Migrate(app, db)


@login_manager.user_loader
def load_user(user_id):
    from ..models import User
    return User.query.get(int(user_id))