import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from scipy.interpolate import Rbf
import io
import base64

def calculate_geometry_from_data(results_data, width, height):
    """
    【核心算法：自动几何校准】
    不依赖传入的 width/height，而是根据点的分布反推中心。
    解决浏览器窗口变化导致的坐标偏移问题。
    """
    # 默认回退值
    default_res = (width / 2.0, height / 2.0, 45.0)
    
    if not results_data or len(results_data) < 4:
        return default_res

    # 1. 提取所有点的像素坐标
    px_coords = np.array([[r['pos_x'], r['pos_y']] for r in results_data])
    
    # 2. 计算几何重心
    mean_center = np.mean(px_coords, axis=0)
    
    # 3. 寻找离重心最近的 4 个点
    # 在 24-2 标准网格中，离中心最近的是 (±3, ±3)，这4个点的几何中心绝对是 (0,0)
    dists = np.sqrt(np.sum((px_coords - mean_center)**2, axis=1))
    
    # 取最近的 k 个点 (防止数据过少报错)
    k = min(4, len(results_data))
    closest_indices = np.argsort(dists)[:k]
    closest_points = px_coords[closest_indices]
    
    # 4. 计算真正的中心坐标
    real_center_x = np.mean(closest_points[:, 0])
    real_center_y = np.mean(closest_points[:, 1])
    
    # 5. 动态反推比例尺 (px_per_deg)
    # 24-2 模式最远点距离中心约 29-30 度 (含鼻侧阶梯)
    # 我们取所有点中距离中心最远的距离
    recalc_dists = np.sqrt((px_coords[:,0] - real_center_x)**2 + (px_coords[:,1] - real_center_y)**2)
    max_dist_px = np.max(recalc_dists)
    
    estimated_scale = max_dist_px / 28.5 # 28.5 是一个经验值，覆盖 24-2 的范围
    
    # 保护机制：如果算出来的比例太离谱，说明数据有问题，回退到默认
    if estimated_scale < 10 or estimated_scale > 200:
        return default_res

    return real_center_x, real_center_y, estimated_scale

def generate_report_image(results_data, width, height, eye):
    """
    生成综合视野报告图 (Auto-Centering + 固定布局 + 强制白底)
    """
    if not results_data:
        return None

    # --- 1. 坐标计算 (使用自动校准) ---
    center_x, center_y, px_per_deg = calculate_geometry_from_data(results_data, width, height)

    x_raw = []
    y_raw = []
    z_raw = [] 

    for r in results_data:
        # 使用校准后的中心和比例进行转换
        deg_x = (r['pos_x'] - center_x) / px_per_deg
        deg_y = (center_y - r['pos_y']) / px_per_deg # Y轴反转
        
        val = r['sensitivity_db']
        if val is None: val = 0 
            
        x_raw.append(deg_x)
        y_raw.append(deg_y)
        z_raw.append(val)

    x = np.array(x_raw)
    y = np.array(y_raw)
    z = np.array(z_raw)

    # --- 2. 准备画布 (关键修复：白底 + 不透明) ---
    # facecolor='white': 保证 PDF 转换时有实体背景，不会被裁剪
    # dpi=100, figsize=(12, 6) -> 生成 1200x600 像素的图片
    fig = plt.figure(figsize=(12, 6), dpi=100, facecolor='white')
    
    # 使用 add_axes 手动绝对布局，不依赖自动布局
    # [left, bottom, width, height] (0.0 ~ 1.0)
    
    # 左图：数值图 (留出边距)
    ax1 = fig.add_axes([0.02, 0.05, 0.46, 0.9]) 
    
    # 右图：灰度图 (中间留 4% 的缝隙)
    ax2 = fig.add_axes([0.52, 0.05, 0.46, 0.9])
    
    # 视野显示范围 +/- 32度
    LIMIT = 32
    extent_range = [-LIMIT, LIMIT, -LIMIT, LIMIT]

    # ==========================
    #  左图：数值图 (Value Plot)
    # ==========================
    ax1.set_title(f"Sensitivity (dB) - {eye}", fontsize=14, pad=10)
    ax1.set_aspect('equal')
    
    # 绘制十字中心
    ax1.axhline(0, color='#ddd', linestyle='-', linewidth=1)
    ax1.axvline(0, color='#ddd', linestyle='-', linewidth=1)

    for i in range(len(x)):
        val = int(z[i])
        
        # 样式逻辑：低分标红加粗
        if val < 10:
            color = 'black'; weight = 'bold'
        elif val < 20:
            color = '#d9534f'; weight = 'normal'
        else:
            color = '#333'; weight = 'normal'
            
        # 绘制文字 (clip_on=False 保证边缘文字不被切掉)
        ax1.text(x[i], y[i], str(val), 
                 fontsize=11, ha='center', va='center', 
                 color=color, fontweight=weight, clip_on=False)
        
        # 绘制小定位点
        ax1.scatter(x[i], y[i], s=10, c='#eee', marker='+', clip_on=False)

    ax1.set_xlim(extent_range[0], extent_range[1])
    ax1.set_ylim(extent_range[2], extent_range[3])
    ax1.axis('off') # 隐藏边框

    # ==============================
    #  右图：灰度地形图 (Grayscale)
    # ==============================
    ax2.set_title("Grayscale Map", fontsize=14, pad=10)
    ax2.set_aspect('equal')

    # 插值网格
    ti = np.linspace(-LIMIT, LIMIT, 150)
    XI, YI = np.meshgrid(ti, ti)

    try:
        if len(x) > 3:
            # 线性插值 (linear) 比 thin_plate 更稳定，不会产生伪影
            rbf = Rbf(x, y, z, function='linear')
            ZI = rbf(XI, YI)
            ZI = np.clip(ZI, 0, 40) # 限制在 0-40dB

            # Mask 遮罩：只显示测试点周围 6.5 度范围内的数据
            mask = np.ones_like(ZI, dtype=bool)
            threshold_sq = 6.5**2 
            
            # 矢量化计算 Mask (比循环快)
            valid_mask = np.zeros_like(ZI, dtype=bool)
            for dx, dy in zip(x, y):
                dist_sq = (XI - dx)**2 + (YI - dy)**2
                valid_mask |= (dist_sq < threshold_sq)
            
            # 应用遮罩
            ZI_masked = np.ma.array(ZI, mask=~valid_mask)

            # 绘制地形图 (Gouraud平滑, 增强对比度)
            # 调整灰度范围：10-35dB，使异常区域(低于10dB)更黑，正常区域更白
            ax2.pcolormesh(XI, YI, ZI_masked, cmap='gray', shading='gouraud', vmin=10, vmax=35)
        else:
            ax2.text(0, 0, "Insufficient Data", ha='center')

        # 绘制理论盲点参考框
        # 左眼在左(-15)，右眼在右(+15)
        bs_x = 15.5 if eye == 'R' else -15.5
        bs_y = -1.5
        ellipse = patches.Ellipse((bs_x, bs_y), width=5.5, height=7.5,
            linewidth=1.5, edgecolor='#00ffff', facecolor='none', linestyle='--')
        ax2.add_patch(ellipse)
        # ax2.text(bs_x, bs_y - 5, 'BS', color='#00ffff', fontsize=8, ha='center')

    except Exception as e:
        print(f"Plot Error: {e}")

    ax2.set_xlim(extent_range[0], extent_range[1])
    ax2.set_ylim(extent_range[2], extent_range[3])
    ax2.axis('off')

    # --- 3. 输出 ---
    buf = io.BytesIO()
    
    # 【关键修复】
    # transparent=False: 关闭透明，强制使用 facecolor='white'
    # bbox_inches=None: 禁用自动裁剪，保证输出尺寸严格等于 1200x600
    fig.savefig(buf, format='png', transparent=False, facecolor='white', dpi=100)
    
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)

    return img_base64