"""
Legacy API routes — DEPRECATED

All routes have been migrated to app.modules.vision.api_routes.
This file is kept only for reference and MUST NOT be registered.
"""
import base64
import os
import tempfile
import platform
import subprocess
import traceback
from flask import Blueprint, request, jsonify, session, url_for
from flask_login import current_user, login_required
from app import db
from app.models import TestRecord, TestResultDetail
from app.modules.vision.engine.manager import TestManager
from app.modules.vision.engine.registry import StrategyRegistry

# 导入配置
from app.config import Config

bp = Blueprint('api', __name__, url_prefix='/api')

# 全局单例管理器
manager = TestManager()

def save_final_results(record, final_results):
    """
    辅助函数：将 C++ 引擎计算出的最终结果批量写入数据库
    核心逻辑：包含实测值 + 未测点的预测值
    对于参考测试：C++策略已经处理了正常点位的继承
    """
    try:
        # 1. 保存详细打点数据 (54个点)
        data_list = final_results.get('data', [])
        
        # 先清空该记录下的旧详情（防止重复写入）
        TestResultDetail.query.filter_by(session_id=record.session_id).delete()
            
        for item in data_list:
            # 兼容处理：新的 C++ 代码返回的是 pos_x, 旧的是 x
            p_x = item.get('pos_x', item.get('x'))
            p_y = item.get('pos_y', item.get('y'))
            
            detail = TestResultDetail(
                session_id=record.session_id, # 使用 session_id 关联
                point_id=item['id'],
                pos_x=p_x,
                pos_y=p_y,
                sensitivity_db=item['sensitivity_db'], # 这里包含 C++ 算出的预测值
                is_seen=False, # 结果表中存阈值即可，is_seen 设为默认 False
                reaction_time=0
            )
            db.session.add(detail)

        # 2. 更新主记录的可靠性指标
        record.fixation_losses = final_results.get('fixation_losses', 0)
        record.total_catch_trials = final_results.get('total_catch_trials', 0)
        
        # 如果是中途退出，标记为未完成，但保存数据
        # (调用此函数时状态通常由外部控制，这里只负责存数据)
        
        db.session.commit()
        print(f"[API] Results saved for session {record.session_id} (Points: {len(data_list)})")
        
    except Exception as e:
        db.session.rollback()
        print(f"[API] Save Error: {e}")
        traceback.print_exc()

# --- 新增：初始化接口 ---
@bp.route('/test/init', methods=['POST'])
@login_required
def init_test():
    """
    初始化测试配置：获取初始背景色和主题设置
    """
    try:
        data = request.json
        session_id = data.get('session_id') or session.get('session_id')

        w = data.get('window_width', 1920)
        h = data.get('window_height', 1080)

        if not session_id:
            return jsonify({'error': 'No session active'}), 400

        # 准备测试参数
        params = {}
        params['age'] = current_user.age or 30

        # 添加theme配置
        theme = data.get('theme')
        if not theme:
            theme = Config.DEFAULT_THEME
        params['theme'] = theme

        # 获取当前测试模式和眼睛
        config = session.get('test_config', {})
        current_eye = config.get('eye', 'R')
        params['eye'] = current_eye

        mode_id = config.get('mode', 'mode_standard_v1')
        registry_conf = StrategyRegistry.get_config(mode_id)

        if registry_conf:
            params.update(registry_conf.get('params', {}))
            params['algorithm_type'] = registry_conf.get('core_algo', 'ZEST')

        # --- 处理参考测试（增量测试）---
        if config.get('is_incremental') and config.get('reference_session_id'):
            print(f"[API] Loading reference test configuration...")
            reference_session_id = config['reference_session_id']

            # 获取参考测试记录
            reference_record = TestRecord.query.filter_by(session_id=reference_session_id).first()
            if reference_record:
                # 继承点位策略和测试模式
                params['grid_pattern'] = reference_record.test_mode
                params['test_mode'] = 'standard'
                params['reference_session_id'] = reference_session_id

                # 获取阈值和空间容差
                incremental_config = StrategyRegistry.TEST_CATEGORIES.get('incremental', {})
                threshold_db = incremental_config.get('params', {}).get('threshold', 20)
                spatial_margin_deg = incremental_config.get('params', {}).get('margin', 0.5)

                # 提取所有参考点位数据
                reference_points = []
                for detail in reference_record.details:
                    reference_points.append({
                        'deg_x': (detail.pos_x - reference_record.window_width/2) / (reference_record.window_height/50),
                        'deg_y': (reference_record.window_height/2 - detail.pos_y) / (reference_record.window_height/50),
                        'sensitivity_db': detail.sensitivity_db,
                        'is_seen': detail.is_seen,
                        'reaction_time': detail.reaction_time
                    })

                params['threshold_db'] = threshold_db
                params['spatial_margin_deg'] = spatial_margin_deg
                params['reference_points'] = reference_points

                abnormal_count = sum(1 for p in reference_points if p['sensitivity_db'] < threshold_db)
                print(f"[API] Reference test loaded: session={reference_session_id}, "
                      f"points={len(reference_points)}, abnormal={abnormal_count}")
            else:
                print(f"[API] Warning: Reference record not found: {reference_session_id}")

        # 获取或创建策略对象
        print(f"[API] Creating strategy with params keys: {list(params.keys())}")
        strategy = manager.get_strategy(session_id, w, h, params)

        print(f"[API] Strategy created successfully, checking point status...")
        # 生成一个初始点数据来获取配置信息
        # 注意：这里不会真正开始测试，只是获取配置
        init_data = strategy.get_next_point()

        # 调试：检查点位状态
        debug_status = strategy.debug_point_status()
        print(f"[API] Point status after init: total={debug_status['total']}, "
              f"finished={debug_status['finished']}, unfinished={debug_status['unfinished']}")
        if debug_status['unfinished_points']:
            print(f"[API] Unfinished points: {debug_status['unfinished_points'][:5]}")  # 只打印前5个

        # 提取配置信息
        response_data = {
            'status': 'success',
            'theme': theme,
            'bg_color': init_data.get('bg_color', '#000000'),
            'stim_color': init_data.get('color_hex', '#FFFFFF')
        }

        return jsonify(response_data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# --- 新增：强制终止接口 ---
@bp.route('/test/terminate', methods=['POST'])
@login_required
def terminate_test():
    """
    专门处理中途退出：强制保存当前所有数据（含默认值）
    """
    data = request.json
    session_id = data.get('session_id') or session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No session id'}), 400
        
    try:
        # 1. 获取策略对象
        strategy = manager.get_strategy(session_id)
        if not strategy:
            # 如果内存里没了，说明已经结束了，直接去报告页
            return jsonify({'status': 'finished', 'redirect_url': url_for('vision.analysis_report', session_id=session_id)})

        # 2. 强制提取数据 (这里会包含 ZEST 预测的默认值)
        final_results = strategy.get_final_results()
        
        # 3. 存库
        record = TestRecord.query.filter_by(session_id=session_id).first()
        if record:
            record.is_completed = False # 标记为未正常完成
            save_final_results(record, final_results)
        
        # 4. 清理内存
        manager.remove_strategy(session_id)
        
        return jsonify({'status': 'saved', 'redirect_url': url_for('vision.analysis_report', session_id=session_id)})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/test/next', methods=['POST'])
@login_required
def get_next_stimulus():
    """
    核心接口：获取下一个坐标
    """
    try:
        data = request.json
        session_id = data.get('session_id') or session.get('session_id')
        action = data.get('action') 
        
        w = data.get('window_width', 1920)
        h = data.get('window_height', 1080)

        if not session_id:
            return jsonify({'error': 'No session active'}), 400

        # --- 1. 确保主表记录存在 ---
        record = TestRecord.query.filter_by(session_id=session_id).first()

        config = session.get('test_config', {})
        current_eye = config.get('eye', 'R') # 默认为右眼

        if not record:
            # 创建新记录
            mode_id = config.get('mode', 'mode_standard_v1')
            reg_conf = StrategyRegistry.get_config(mode_id)
            display_name = reg_conf.get('display_name', mode_id) if reg_conf else mode_id

            # 检查是否为参考测试
            is_incremental = config.get('is_incremental', False)
            reference_session_id = config.get('reference_session_id')
            
            # 为参考测试添加标识
            if is_incremental:
                display_name = f"{display_name} (参考测试)"

            record = TestRecord(
                session_id=session_id,
                user_id=current_user.id,
                eye=current_eye,
                test_mode=display_name,
                window_width=w,
                window_height=h,
                is_incremental=is_incremental,
                reference_session_id=reference_session_id
            )
            db.session.add(record)
            db.session.commit()
        else:
            if record.window_width != w:
                record.window_width = w
                record.window_height = h
                db.session.commit()

        # --- 2. 准备算法参数 ---
        params = data.get('params', {})
        params['age'] = current_user.age or 30
        
        # 添加theme配置
        # 优先使用请求中的theme参数
        theme = data.get('theme')
        # 如果没有提供，使用默认配置
        if not theme:
            theme = Config.DEFAULT_THEME
        params['theme'] = theme
        
        mode_id = config.get('mode', 'mode_standard_v1')
        registry_conf = StrategyRegistry.get_config(mode_id)
        params['eye'] = current_eye

        if registry_conf:
            params.update(registry_conf.get('params', {}))
            params['algorithm_type'] = registry_conf.get('core_algo', 'ZEST')
            params['eye'] = current_eye
        
        # 处理参考测试
        if config.get('is_incremental', False) and config.get('reference_session_id'):
            reference_session_id = config['reference_session_id']
            # 获取参考测试记录
            reference_record = TestRecord.query.filter_by(session_id=reference_session_id).first()
            if reference_record:
                # 继承参考测试的点位策略和测试模式
                # 解析参考测试的测试模式
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
                
                # 获取参考测试的配置
                ref_config = StrategyRegistry.get_config(ref_mode_id)

                # 继承点位策略和测试模式
                grid_pattern = ref_config.get('grid_pattern', '24-2')
                test_mode = ref_config.get('test_mode', 'standard')

                # 获取增量测试的阈值和空间容差
                incremental_config = StrategyRegistry.TEST_CATEGORIES.get('incremental', {})
                threshold_db = incremental_config.get('params', {}).get('threshold', 20)
                spatial_margin_deg = incremental_config.get('params', {}).get('margin', 0.5)

                # 提取所有参考点位数据
                reference_points = []
                for detail in reference_record.details:
                    reference_points.append({
                        'deg_x': (detail.pos_x - reference_record.window_width/2) / (reference_record.window_height/50),
                        'deg_y': (reference_record.window_height/2 - detail.pos_y) / (reference_record.window_height/50),
                        'sensitivity_db': detail.sensitivity_db,
                        'is_seen': detail.is_seen,
                        'reaction_time': detail.reaction_time
                    })

                # 检查是否所有点都正常 - 如果是，直接完成测试
                abnormal_count = sum(1 for p in reference_points if p['sensitivity_db'] < threshold_db)
                if abnormal_count == 0:
                    # 所有点都是正常的，直接继承所有数据
                    record.is_completed = True
                    for detail in reference_record.details:
                        new_detail = TestResultDetail(
                            session_id=record.session_id,
                            point_id=detail.point_id,
                            pos_x=detail.pos_x,
                            pos_y=detail.pos_y,
                            sensitivity_db=detail.sensitivity_db,
                            is_seen=detail.is_seen,
                            reaction_time=detail.reaction_time
                        )
                        db.session.add(new_detail)
                    db.session.commit()
                    return jsonify({"status": "finished"})

                # 将配置传递给 C++ 策略
                params['grid_pattern'] = grid_pattern
                params['test_mode'] = test_mode
                params['reference_session_id'] = reference_session_id
                params['threshold_db'] = threshold_db
                params['spatial_margin_deg'] = spatial_margin_deg
                params['reference_points'] = reference_points

                print(f"[API] Reference test with session: {reference_session_id}")
                print(f"[API] Grid pattern: {grid_pattern}, Test mode: {test_mode}")
                print(f"[API] Threshold: {threshold_db}dB, Spatial margin: {spatial_margin_deg}°")
                print(f"[API] Total reference points: {len(reference_points)}, Abnormal: {abnormal_count}")
            else:
                print(f"[API] Reference test not found: {reference_session_id}")

        # --- 3. 获取 C++ 策略对象 ---
        strategy = manager.get_strategy(session_id, w, h, params)

        # === 情况 A: 正常结束检查 ===
        # 注意：这里不再处理 action='stop'，统一走 /terminate 接口
        
        point_data = strategy.get_next_point()

        if point_data.get('finished'):
            final_results = strategy.get_final_results()
            record.is_completed = True # 标记为自然完成
            save_final_results(record, final_results)
            manager.remove_strategy(session_id)
            return jsonify({"status": "finished"})

        return jsonify(point_data)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "msg": str(e)}), 500

@bp.route('/test/submit', methods=['POST'])
@login_required
def submit_point_result():
    """
    提交反馈
    """
    data = request.json
    session_id = data.get('session_id') or session.get('session_id')
    point_id = data.get('point_id')
    seen = data.get('seen')

    if not session_id or point_id is None:
        return jsonify({'error': 'Missing params'}), 400

    try:
        strategy = manager.get_strategy(session_id) 
        if strategy:
            strategy.submit_result(int(point_id), bool(seen))
        else:
            return jsonify({"status": "warning", "msg": "Strategy lost"}), 200
            
    except Exception as e:
        print(f"Update Strategy Failed: {e}")
        return jsonify({"status": "error", "msg": str(e)}), 500

    return jsonify({"status": "ok"})

@bp.route('/system/open_pdf', methods=['POST'])
@login_required
def open_pdf_externally():
    data = request.json
    pdf_base64 = data.get('pdf_data')
    
    if not pdf_base64:
        return jsonify({'status': 'error', 'msg': 'No data'})

    try:
        # 去掉可能的 Data URI 前缀
        if ',' in pdf_base64:
            pdf_base64 = pdf_base64.split(',')[1]
            
        pdf_bytes = base64.b64decode(pdf_base64)
        
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        filename = f"Lumina_Report_{session.get('session_id', 'Preview')}.pdf"
        file_path = os.path.join(temp_dir, filename)
        
        print(f"[PDF] Saving to temp file: {file_path}")
        
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
            
        print(f"[PDF] File saved successfully, size: {len(pdf_bytes)} bytes")
        
        # 根据操作系统调用默认 PDF 阅读器
        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', file_path))
        elif platform.system() == 'Windows':    # Windows
            print(f"[PDF] Opening with os.startfile: {file_path}")
            os.startfile(file_path)
        else:                                   # Linux
            subprocess.call(('xdg-open', file_path))
            
        print("[PDF] PDF opened successfully")
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"[PDF] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'msg': str(e)})

@bp.route('/test/get_reference_data/<session_id>', methods=['GET'])
@login_required
def get_reference_data(session_id):
    """获取参考测试数据"""
    record = TestRecord.query.filter_by(session_id=session_id).first()
    if not record or record.user_id != current_user.id:
        return jsonify({'error': 'Invalid reference test'}), 403
    
    data = []
    for detail in record.details:
        data.append({
            'point_id': detail.point_id,
            'pos_x': detail.pos_x,
            'pos_y': detail.pos_y,
            'sensitivity_db': detail.sensitivity_db,
            'is_seen': detail.is_seen
        })
    
    return jsonify({
        'data': data,
        'window_width': record.window_width,
        'window_height': record.window_height,
        'eye': record.eye
    })