from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import _
from app.models import User
from app import db

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('hub.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('hub.dashboard'))
        else:
            flash(_('邮箱或密码错误'))
            
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('hub.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        age = request.form.get('age')
        gender = request.form.get('gender')
        
        if User.query.filter_by(email=email).first():
            flash(_('该邮箱已被注册'))
            return redirect(url_for('auth.register'))
            
        new_user = User(email=email, name=name, age=age, gender=gender)
        new_user.set_password(password) # 加密保存
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(_('注册成功，请登录'))
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/set_language/<lang>')
def set_language(lang):
    if lang not in ('zh', 'en'):
        flash(_('不支持的语言代码'), 'error')
        return redirect(request.referrer or url_for('auth.login'))

    resp = redirect(request.referrer or url_for('auth.login'))
    resp.set_cookie('language', lang, max_age=31536000, path='/')

    if current_user.is_authenticated:
        current_user.set_preference('language', lang)
        db.session.commit()

    return resp
