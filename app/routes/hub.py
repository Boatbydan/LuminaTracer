"""
User Hub Blueprint - 用户中心路由

提供用户主仪表盘、设置管理等功能的路由。
这是应用的核心入口，登录后首先访问的页面。

路由结构:
    /hub              -> 主仪表盘 (dashboard)
    /hub/settings     -> 用户设置 (settings)
"""

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from flask_login import login_required, current_user
from flask_babel import _

from app import db
from app.models import TestRecord, TestResultDetail
from app.modules import TestModuleRegistry


bp = Blueprint('hub', __name__)


@bp.route('/hub')
@login_required
def dashboard():
    """
    用户主仪表盘
    
    展示:
    - 测试模块入口卡片（从 TestModuleRegistry 动态获取）
    - 最近测试活动记录
    - 快速设置入口
    """
    user = current_user
    
    # 获取已启用的测试模块
    test_modules = TestModuleRegistry.get_all_enabled()
    
    # 获取最近的测试记录（最多 5 条）
    recent_records = TestRecord.query.filter_by(user_id=user.id)\
        .order_by(TestRecord.created_at.desc())\
        .limit(5)\
        .all()
    
    # 格式化最近记录用于展示
    recent_activity = []
    for record in recent_records:
        total_pts = len(record.details) if record.details else 0
        recent_activity.append({
            'session_id': record.session_id[-8:],  # 只显示后8位
            'full_session_id': record.session_id,
            'test_mode': record.test_mode,
            'eye': record.eye,
            'created_at': record.created_at,
            'total_pts': total_pts,
            'is_completed': record.is_completed,
            'is_incremental': record.is_incremental
        })
    
    # 统计概览数据
    total_tests = TestRecord.query.filter_by(user_id=user.id).count()
    completed_tests = TestRecord.query.filter_by(
        user_id=user.id, is_completed=True
    ).count()
    
    # 报告统计数据
    total_reports = TestRecord.query.filter_by(user_id=user.id).count()
    recent_reports = TestRecord.query.filter_by(user_id=user.id)\
        .order_by(TestRecord.created_at.desc())\
        .limit(7)\
        .count()
    
    return render_template(
        'hub/dashboard.html',
        user=user,
        active_page='hub',
        user_theme=user.theme,
        test_modules=test_modules,
        recent_activity=recent_activity,
        stats={
            'total_tests': total_tests,
            'completed_tests': completed_tests,
            'total_reports': total_reports,
            'recent_reports': recent_reports
        },
        navbar_fixed=user.navbar_fixed
    )


@bp.route('/hub/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """
    用户设置页面
    
    支持的设置项:
    - theme: 主题切换 (light/dark/auto)
    - vision_defaults: 视野测试默认参数
    
    GET: 显示当前设置
    POST: 保存修改后的设置
    """
    user = current_user
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_theme':
            new_theme = request.form.get('theme', 'light')
            if new_theme in ('light', 'dark', 'auto'):
                user.theme = new_theme
                db.session.commit()
                flash(_('主题已更改: %(theme)s', theme=new_theme), 'success')
                
        elif action == 'update_vision_defaults':
            preferred_eye = request.form.get('preferred_eye', 'both')
            default_mode = request.form.get('default_mode', 'mode_standard_v1')
            
            user.set_preference('vision_defaults.preferred_eye', preferred_eye)
            user.set_preference('vision_defaults.default_mode', default_mode)
            db.session.commit()
            flash(_('视野测试默认参数已保存'), 'success')
        
        else:
            flash(_('未知的操作'), 'error')
        
        return redirect(url_for('hub.settings'))
    
    # 获取可用的测试模式列表（用于设置页面的下拉选项）
    from app.modules.vision.engine.registry import StrategyRegistry
    available_modes = StrategyRegistry.get_all_modes()
    
    return render_template(
        'hub/settings.html',
        user=user,
        active_page='hub',
        user_theme=user.theme,
        available_modes=available_modes,
        current_theme=user.theme,
        current_eye_pref=user.vision_default_eye,
        current_mode_pref=user.get_preference('vision_defaults.default_mode', 'mode_standard_v1'),
        navbar_fixed=user.navbar_fixed
    )


@bp.route('/hub/api/preferences', methods=['POST'])
@login_required
def update_preferences_api():
    """
    API 端点：更新用户偏好（供 AJAX 调用）
    
    Request JSON:
        {"key": "theme", "value": "dark"}
    
    Response:
        {"status": "ok", "message": "..."}
    """
    data = request.get_json()
    
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({'status': 'error', 'message': _('缺少必要参数')}), 400
    
    key = data['key']
    value = data['value']
    
    # 安全检查：只允许特定的顶层键
    allowed_keys = {'theme', 'vision_defaults', 'language'}
    top_level_key = key.split('.')[0]
    
    if top_level_key not in allowed_keys:
        return jsonify({'status': 'error', 'message': '不允许的设置键'}), 403
    
    try:
        current_user.set_preference(key, value)
        db.session.commit()
        return jsonify({'status': 'ok', 'message': _('设置已保存')})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
