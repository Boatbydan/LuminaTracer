from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    # 如果用户已经登录，直接跳到仪表盘
    if current_user.is_authenticated:
        # 【修正】函数名是 user_dashboard
        return redirect(url_for('views.user_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # 验证密码哈希
        if user and user.check_password(password):
            login_user(user)
            # 【修正】登录成功后，跳转到 user_dashboard
            return redirect(url_for('views.user_dashboard'))
        else:
            flash('邮箱或密码错误')
            
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    # 如果已登录，也跳到仪表盘
    if current_user.is_authenticated:
        return redirect(url_for('views.user_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        age = request.form.get('age')
        gender = request.form.get('gender')
        
        if User.query.filter_by(email=email).first():
            flash('该邮箱已被注册')
            return redirect(url_for('auth.register'))
            
        new_user = User(email=email, name=name, age=age, gender=gender)
        new_user.set_password(password) # 加密保存
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('注册成功，请登录')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) # 登出后跳回登录页