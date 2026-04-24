from flask import Blueprint, render_template, abort
from app.database import get_db
# 引入新的生成函数
from .report_generator import generate_report_image 

bp = Blueprint('analysis', __name__, url_prefix='/analysis')

from app.analysis.pdf_generator import create_pdf_report

@bp.route('/report/<session_id>')
def view_report(session_id):
    db = get_db()
    
    # 获取元数据 (屏幕宽高等)
    meta = db.execute('''
        SELECT r.created_at, u.name, r.eye, r.window_width, r.window_height 
        FROM test_records r
        JOIN users u ON r.user_id = u.id
        WHERE r.session_id = ?
    ''', (session_id,)).fetchone()

    if not meta:
        abort(404)

    # 获取详细点位数据
    details = db.execute('''
        SELECT pos_x, pos_y, sensitivity_db 
        FROM test_results_detail 
        WHERE session_id = ?
    ''', (session_id,)).fetchall()

    # # 生成图片
    # # 注意：如果数据库里存的 window_width 是空的，给个默认值 1920x1080 防止报错
    w = meta['window_width'] if meta['window_width'] else 1920
    h = meta['window_height'] if meta['window_height'] else 1080
    
    # report_img = generate_report_image(details, w, h)

    # return render_template('analysis/report.html', meta=meta, report_img=report_img)

    # 1. 生成图片 (Matplotlib)
    plot_img = generate_report_image(results_data, 1920, 1080, record.eye)
    
    # 2. 生成 PDF (ReportLab)
    # 【注意】一定要把 plot_img 传进去！
    pdf_data = create_pdf_report(record, plot_img) 
    
    return render_template('analysis/report.html', 
                           record=record, 
                           plot_img=plot_img,   # 用于网页展示
                           pdf_data=pdf_data)   # 用于下载/打开