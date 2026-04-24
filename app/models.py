from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    records = db.relationship('TestRecord', backref='owner', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class TestRecord(db.Model):
    __tablename__ = 'test_records'
    
    session_id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    test_mode = db.Column(db.String(50))
    eye = db.Column(db.String(5))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- 新增：屏幕元数据 (解决 Metadata Update Warning) ---
    window_width = db.Column(db.Integer)
    window_height = db.Column(db.Integer)
    
    # 结果统计
    fixation_losses = db.Column(db.Integer, default=0)
    total_catch_trials = db.Column(db.Integer, default=0)
    false_positives = db.Column(db.Integer, default=0) # 补上这个字段防止报错
    is_completed = db.Column(db.Boolean, default=False)  # 测试是否完成
    
    # 增量测试相关字段
    is_incremental = db.Column(db.Boolean, default=False)  # 是否为增量测试
    reference_session_id = db.Column(db.String(36), nullable=True)  # 参考测试的会话ID
    
    details = db.relationship('TestResultDetail', backref='record', cascade="all, delete-orphan")

class TestResultDetail(db.Model):
    __tablename__ = 'test_results_detail'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('test_records.session_id'))
    
    point_id = db.Column(db.Integer)
    pos_x = db.Column(db.Float)
    pos_y = db.Column(db.Float)
    sensitivity_db = db.Column(db.Float)
    is_seen = db.Column(db.Boolean)
    reaction_time = db.Column(db.Integer)
    
    # 记录该点测试时的绝对时间
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)