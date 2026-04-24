# app/database.py

import sqlite3
from flask import g, current_app

def get_db():
    """
    获取数据库连接 (Singleton per Request)。
    """
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DB_PATH'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """清理资源"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db_tables():
    """
    初始化数据库表结构。
    每次删除 .sqlite 文件后，重启应用时会执行这里。
    所以这里必须包含【最新】的字段定义。
    """
    db = get_db()
    
    # 1. 用户表 (Users)
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            age INTEGER,
            gender TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. 测试记录表 (Test Records)
    db.execute('''
        CREATE TABLE IF NOT EXISTS test_records (
            session_id TEXT PRIMARY KEY,
            user_id INTEGER,
            user_name TEXT,
            age INTEGER,
            gender TEXT,
            eye TEXT,
            test_mode TEXT,
            
            -- 可靠性指标 (新增)
            fixation_losses INTEGER DEFAULT 0,  -- 固视丢失次数 (盲点按键次数)
            false_positives INTEGER DEFAULT 0,  -- 假阳性 (没人也没光时按键)
            total_catch_trials INTEGER DEFAULT 0, -- 总共进行的盲点测试次数
            
            pos_x REAL,
            pos_y REAL,
            reaction_time INTEGER,
            window_width INTEGER,
            window_height INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # 3. 详细结果表 (Test Results Detail)
    db.execute('''
        CREATE TABLE IF NOT EXISTS test_results_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            point_id INTEGER,
            pos_x REAL,
            pos_y REAL,
            sensitivity_db REAL,  -- 最终确定的视力阈值
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    db.commit()

# 提供给外部手动初始化的函数 (可选)
def init_db():
    init_db_tables()