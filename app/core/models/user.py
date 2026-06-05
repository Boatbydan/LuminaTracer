"""
Core Models — User

全局模型（非模块特定）。
User 是系统中唯一的全局模型，属于核心框架。

模块特定的模型（如 TestRecord）应放在各自 modules/{name}/models.py 中。
"""

from ... import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.orm.attributes import flag_modified


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    preferences = db.Column(db.JSON, default=dict)

    records = db.relationship('TestRecord', backref='owner', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_preference(self, key: str, default: Any = None) -> Any:
        if not self.preferences:
            return default
        keys = key.split('.')
        value = self.preferences
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set_preference(self, key: str, value: Any) -> None:
        if self.preferences is None:
            self.preferences = {}
        keys = key.split('.')
        target = self.preferences
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        flag_modified(self, 'preferences')

    @property
    def theme(self) -> str:
        return self.get_preference('theme', 'light')

    @theme.setter
    def theme(self, value: str) -> None:
        self.set_preference('theme', value)

    @property
    def vision_default_eye(self) -> str:
        return self.get_preference('vision_defaults.preferred_eye', 'both')

    @property
    def language(self) -> str:
        return self.get_preference('language', 'zh')

    @language.setter
    def language(self, value: str) -> None:
        self.set_preference('language', value)

    @property
    def navbar_fixed(self) -> bool:
        return self.get_preference('navbar_fixed', True)

    @navbar_fixed.setter
    def navbar_fixed(self, value: bool) -> None:
        self.set_preference('navbar_fixed', value)