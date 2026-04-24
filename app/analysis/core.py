import pandas as pd
import matplotlib
matplotlib.use('Agg') # 非交互后端
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

# alg core
from . import vision_core_cpp

class VisionAnalyticsEngine:
    def __init__(self, db_conn):
        self.conn = db_conn
        self.cpp_analyzer = vision_core_cpp.CoreAnalyzer()

    def _fetch_data(self, session_id: str) -> pd.DataFrame:
        """私有方法：从数据库加载原始数据"""
        query = "SELECT * FROM test_records WHERE session_id = ?"
        return pd.read_sql_query(query, self.conn, params=(session_id,))

    def calculate_metrics(self, session_id: str) -> dict:
            df = self._fetch_data(session_id)
            if df.empty: return None

            # 1. 将 DataFrame 数据转换为 C++ 能接受的格式
            points = []
            for _, row in df.iterrows():
                # 确保这里传入的参数顺序与 C++ 构造函数一致 (x, y, reaction_time)
                p = vision_core_cpp.DataPoint(
                    float(row['pos_x']), 
                    float(row['pos_y']), 
                    int(row['reaction_time'])
                )
                points.append(p)

            # 2. 调用 C++ 算法进行计算
            results = self.cpp_analyzer.analyze(points)

            # 3. 组装返回结果
            stats = {
                "meta": { 
                    "session_id": session_id,
                    "test_date": df.iloc[0]['created_at'],
                    # 兼容性处理：防止旧数据库没有这些字段导致报错
                    "user_name": df.iloc[0]['user_name'] if 'user_name' in df.columns else "Unknown",
                    "eye": df.iloc[0]['eye'] if 'eye' in df.columns else "L"
                },
                "performance": {
                    "total_stimuli": len(df),
                    "miss_rate": round(results["miss_rate"], 1),        # 来自 C++
                    "avg_reaction_time": int(results["avg_reaction_time"]), # 来自 C++
                    "std_dev": int(results["std_dev"]),                 # 来自 C++
                    "health_score": int(results["health_score"])        # 来自 C++
                }
            }
            return stats

    def generate_visual_field_map(self, session_id: str) -> str:
        """生成专业的视野热力图 (返回 Base64 字符串)"""
        df = self._fetch_data(session_id)
        if df.empty:
            return None

        w = df.iloc[0]['window_width']
        h = df.iloc[0]['window_height']

        # 初始化绘图
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_facecolor('#f8f9fa') # 医疗灰背景
        
        # 1. 绘制中心十字 (固视点)
        ax.axhline(h/2, color='gray', linestyle='--', alpha=0.3)
        ax.axvline(w/2, color='gray', linestyle='--', alpha=0.3)

        # 2. 绘制漏看点 (黑色 X)
        misses = df[df['reaction_time'] == -1]
        if not misses.empty:
            ax.scatter(misses['pos_x'], misses['pos_y'], 
                      c='black', marker='x', s=100, label='漏看区域 (Blind Spot)')

        # 3. 绘制命中点 (热力图)
        hits = df[df['reaction_time'] > 0]
        if not hits.empty:
            # 使用 Hexbin (六边形分箱) 来模拟视野图，比单纯的散点看起来更专业
            hb = ax.hexbin(
                hits['pos_x'], hits['pos_y'], 
                C=hits['reaction_time'], 
                gridsize=20, 
                cmap='jet_r', # 蓝色代表快(好)，红色代表慢(差)
                edgecolors='gray',
                mincnt=1 # 只有至少有1个点的格子才绘制
            )
            cb = plt.colorbar(hb, ax=ax)
            cb.set_label('反应时间 (ms)')

        # 设置坐标轴 (Y轴反转)
        ax.set_xlim(0, w)
        ax.set_ylim(h, 0)
        ax.set_title("视野反应灵敏度分布")
        ax.legend(loc='upper right')

        # 导出图片
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', bbox_inches='tight', dpi=100)
        plt.close(fig)
        img_buf.seek(0)
        return base64.b64encode(img_buf.getvalue()).decode('utf-8')