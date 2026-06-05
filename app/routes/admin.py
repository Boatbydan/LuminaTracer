# app/routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, session, abort
from app.database import get_db
from functools import wraps  # <--- 1. 必须引入这个

bp = Blueprint('admin', __name__, url_prefix='/admin')

# 简单的权限验证装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_info = session.get('user_info')
        
        # 1. 检查是否登录
        if not user_info:
            return redirect(url_for('auth.login'))
            
        # 2. 检查权限 (假设只有 ID=1 是管理员)
        # 注意：user_info['id'] 可能是 int 也可能是 str，建议转 int 比较
        if int(user_info.get('id', 0)) != 1:
            return "403 Forbidden: 您没有管理员权限", 403
            
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/')
@admin_required  # 现在 dashboard 还是叫 dashboard，不会变成 decorated_function
def dashboard():
    """管理员首页：列出所有表"""
    db = get_db()
    # 查询数据库里有哪些表 (SQLite 系统表)
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return render_template('admin/dashboard.html', tables=tables)

@bp.route('/view/<table>')
@admin_required
def view_table(table):
    """【核心】万能表查看器"""
    db = get_db()
    
    # 1. 安全检查
    allowed_tables = [row['name'] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if table not in allowed_tables:
        abort(404)

    # 2. 获取数据
    cur = db.execute(f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT 100")
    rows = cur.fetchall()
    
    # 3. 动态获取列名
    columns = []
    if rows:
        columns = rows[0].keys()
    else:
        cur = db.execute(f"PRAGMA table_info({table})")
        columns = [col['name'] for col in cur.fetchall()]

    return render_template('admin/table_view.html', table_name=table, columns=columns, rows=rows)

@bp.route('/sql', methods=['GET', 'POST'])
@admin_required
def execute_sql():
    """高级功能：直接执行 SQL 语句"""
    result = None
    error = None
    columns = []
    query = request.form.get('query', '')

    if request.method == 'POST':
        try:
            db = get_db()
            cur = db.execute(query)
            
            if query.strip().upper().startswith("SELECT"):
                rows = cur.fetchall()
                if rows:
                    columns = rows[0].keys()
                result = rows
            else:
                db.commit()
                result = f"执行成功，影响行数: {cur.rowcount}"
                
        except Exception as e:
            error = str(e)

    return render_template('admin/sql_console.html', query=query, result=result, columns=columns, error=error)