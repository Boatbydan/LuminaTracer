import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required, current_user
from app import db
from app.models import User, TestRecord, TestResultDetail
from app.engine.registry import StrategyRegistry
from app.analysis.report_generator import generate_report_image

bp = Blueprint('views', __name__)

# --- 1. 首页路由 ---
@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('views.user_dashboard'))
    return redirect(url_for('auth.login'))

# --- 2. 用户仪表盘 ---
@bp.route('/dashboard')
@login_required
def user_dashboard():
    records = TestRecord.query.filter_by(user_id=current_user.id)\
                              .order_by(TestRecord.created_at.desc())\
                              .all()
    
    history = []
    for r in records:
        # 使用 len() 获取列表长度
        total_pts = len(r.details) if r.details else 0
        
        history.append({
            'session_id': r.session_id,
            'created_at': r.created_at,
            'eye': r.eye,
            'test_mode': r.test_mode,
            'total_pts': total_pts
        })
    
    available_modes = StrategyRegistry.get_all_modes()
    
    return render_template('user_dashboard.html', 
                           user=current_user, 
                           history=history, 
                           modes=available_modes)

# 兼容旧路由
@bp.route('/user/<int:user_id>')
@login_required
def user_profile(user_id):
    return redirect(url_for('views.user_dashboard'))

# --- 3. 准备测试 ---
@bp.route('/prepare_test', methods=['POST'])
@login_required
def prepare_test():
    test_config = {
        'mode': request.form.get('test_mode'),
        'eye': request.form.get('eye')
    }
    session['test_config'] = test_config
    return redirect(url_for('views.instructions'))

# --- 3.1 参考测试选择页面 ---
@bp.route('/prepare_incremental_test')
@login_required
def prepare_incremental_test():
    # 检查URL参数中是否有reference_session_id和eye
    reference_session_id = request.args.get('reference_session_id')
    eye = request.args.get('eye')
    
    # 如果提供了参考测试ID和眼别，直接跳转到确认页面
    if reference_session_id and eye:
        # 验证参考测试记录是否存在且属于当前用户
        reference_record = TestRecord.query.filter_by(session_id=reference_session_id).first()
        if reference_record and reference_record.user_id == current_user.id:
            # 确定参考测试的模式ID
            ref_mode_id = None
            test_mode_name = reference_record.test_mode
            # 移除"(参考测试)"后缀
            if "(参考测试)" in test_mode_name:
                test_mode_name = test_mode_name.replace("(参考测试)", "").strip()
            
            if test_mode_name == "Tracer Standard (标准模式)":
                ref_mode_id = "mode_standard_v1"
            elif test_mode_name == "Tracer Rapid (快速筛查模式)":
                ref_mode_id = "mode_fast_v1"
            else:
                ref_mode_id = "mode_standard_v1"
            
            # 保存参考测试配置
            test_config = {
                'mode': ref_mode_id,  # 继承参考测试的模式
                'eye': eye,
                'is_incremental': True,
                'reference_session_id': reference_session_id
            }
            session['test_config'] = test_config
            return redirect(url_for('views.instructions'))
        else:
            flash('无效的测试记录')
    
    # 获取用户的测试记录，按时间倒序排列
    records = TestRecord.query.filter_by(user_id=current_user.id)\
                              .order_by(TestRecord.created_at.desc())\
                              .all()
    
    # 过滤出完整的测试记录（至少有10个测试点）
    valid_records = [r for r in records if r.details and len(r.details) >= 10]
    
    return render_template('prepare_incremental_test.html', records=valid_records)

# --- 3.2 确认参考测试 ---
@bp.route('/confirm_incremental_test', methods=['POST'])
@login_required
def confirm_incremental_test():
    reference_session_id = request.form.get('reference_session_id')
    eye = request.form.get('eye')
    
    # 验证参考测试记录是否存在且属于当前用户
    reference_record = TestRecord.query.filter_by(session_id=reference_session_id).first()
    if not reference_record or reference_record.user_id != current_user.id:
        flash('无效的测试记录')
        return redirect(url_for('views.prepare_incremental_test'))
    
    # 确定参考测试的模式ID
    ref_mode_id = None
    test_mode_name = reference_record.test_mode
    # 移除"(参考测试)"后缀
    if "(参考测试)" in test_mode_name:
        test_mode_name = test_mode_name.replace("(参考测试)", "").strip()
    
    if test_mode_name == "Tracer Standard (标准模式)":
        ref_mode_id = "mode_standard_v1"
    elif test_mode_name == "Tracer Rapid (快速筛查模式)":
        ref_mode_id = "mode_fast_v1"
    else:
        ref_mode_id = "mode_standard_v1"
    
    # 保存参考测试配置
    test_config = {
        'mode': ref_mode_id,  # 继承参考测试的模式
        'eye': eye,
        'is_incremental': True,
        'reference_session_id': reference_session_id
    }
    session['test_config'] = test_config
    
    return redirect(url_for('views.instructions'))

# --- 4. 须知页 ---
@bp.route('/instructions')
@login_required
def instructions():
    config = session.get('test_config', {})
    return render_template('landing.html', user=current_user, config=config)

# --- 5. 测试页 ---
@bp.route('/test')
@login_required
def test_page():
    session['session_id'] = str(uuid.uuid4())
    return render_template('test.html')

# --- 6. 设备校准页 ---
@bp.route('/calibration')
@login_required
def calibration():
    return render_template('calibration.html')

from app.analysis.pdf_generator import create_pdf_report
# --- 6. 查看分析报告 (核心修复) ---
@bp.route('/analysis/report/<session_id>')
@login_required
def analysis_report(session_id):
    record = TestRecord.query.filter_by(session_id=session_id).first()
    
    if not record:
        return "Record not found", 404
        
    if record.user_id != current_user.id:
        return "Unauthorized Access", 403

    # 构造 Meta 信息
    meta = {
        'session_id': record.session_id,
        'user_id': record.user_id,
        'name': current_user.name,
        'age': current_user.age,
        'gender': current_user.gender,
        'eye': record.eye,
        'test_mode': record.test_mode,
        'created_at': record.created_at,
        'fixation_losses': record.fixation_losses,
        'total_catch_trials': record.total_catch_trials,
        'false_positives': record.false_positives,
        'is_incremental': record.is_incremental,
    }
    
    # 如果是增量测试，添加参考测试信息
    if record.is_incremental and record.reference_session_id:
        reference_record = TestRecord.query.filter_by(session_id=record.reference_session_id).first()
        if reference_record:
            meta['reference_test'] = {
                'session_id': reference_record.session_id,
                'created_at': reference_record.created_at,
                'test_mode': reference_record.test_mode,
                'total_points': len(reference_record.details) if reference_record.details else 0
            }
    
    # 构造打点数据
    results_data = []
    # 增加空值判断，防止提前退出时 details 为空导致报错
    if record.details:
        for d in record.details:
            results_data.append({
                'id': d.id,
                'point_id': d.point_id,
                
                # --- 【关键修复】 ---
                # 同时提供 pos_x 和 x，确保无论报告生成器用哪个名字都不会报错
                'pos_x': d.pos_x,  
                'pos_y': d.pos_y,
                'x': d.pos_x,
                'y': d.pos_y,
                
                'sensitivity_db': d.sensitivity_db,
                'is_seen': d.is_seen
            })

    # 生成图片
    # 优先使用数据库里存的宽高，如果没有则用默认值
    width = record.window_width or 1920
    height = record.window_height or 1080
    
    report_img = generate_report_image(results_data, width, height, record.eye)
    
    return render_template('analysis/report.html', meta=meta, report_img=report_img)
    
    # pdf_data = create_pdf_report(record, plot_img) 
    # return render_template('analysis/report.html', 
    #                        meta=meta,
    #                        record=record, 
    #                        plot_img=plot_img,   # 用于网页展示
    #                        pdf_data=pdf_data)   # 用于下载/打开


# --- 7. 删除记录 ---
@bp.route('/record/delete/<session_id>', methods=['POST'])
@login_required
def delete_record(session_id):
    record = TestRecord.query.filter_by(session_id=session_id, user_id=current_user.id).first()
    
    if record:
        try:
            db.session.delete(record)
            db.session.commit()
            flash("Record deleted successfully", "success")
        except Exception as e:
            db.session.rollback()
            flash("Delete failed", "error")
    else:
        flash("Record not found or unauthorized", "error")
        
    return redirect(url_for('views.user_dashboard'))