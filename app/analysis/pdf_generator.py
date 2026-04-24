import io
import base64
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from PIL import Image

def create_pdf_report(record, plot_base64):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 40
    
    # --- 调试信息 ---
    print(f"[PDF Gen] Received image data length: {len(plot_base64) if plot_base64 else 0}")

    # 1. 标题
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 50, "Visual Field Test Report")
    c.line(margin, height - 70, width - margin, height - 70)

    # 2. 文本信息
    c.setFont("Helvetica", 12)
    y = height - 100
    c.drawString(margin, y, f"Patient: {record.user.name if record.user else 'Guest'}")
    c.drawString(margin, y-20, f"Eye: {record.eye} / Age: {record.user.age}")
    c.drawString(margin, y-40, f"Date: {record.created_at.strftime('%Y-%m-%d %H:%M')}")

    # --- 3. 核心修复：图片处理 ---
    if plot_base64:
        try:
            # (A) 去头：如果包含 data:image... 前缀，去掉它
            if ',' in plot_base64:
                plot_base64 = plot_base64.split(',')[1]

            # (B) 解码
            img_bytes = base64.b64decode(plot_base64)
            
            # (C) Pillow 清洗
            # 打开图片
            pil_img = Image.open(io.BytesIO(img_bytes))
            print(f"[PDF Gen] Original Image Mode: {pil_img.mode}") # 调试输出

            # 创建一个纯白背景的新图 (RGB模式)
            # 这一步彻底消除了透明度 (Alpha) 问题
            white_bg = Image.new("RGB", pil_img.size, (255, 255, 255))
            
            # 如果原图有透明通道，使用 mask 粘贴
            if pil_img.mode in ('RGBA', 'LA') or (pil_img.mode == 'P' and 'transparency' in pil_img.info):
                pil_img = pil_img.convert('RGBA')
                white_bg.paste(pil_img, (0, 0), pil_img)
            else:
                white_bg.paste(pil_img, (0, 0))
            
            # (D) 保存为干净的内存流 (模拟 JPG 文件)
            clean_buffer = io.BytesIO()
            white_bg.save(clean_buffer, format='JPEG', quality=95)
            clean_buffer.seek(0)
            
            # (E) 喂给 ReportLab
            img_reader = ImageReader(clean_buffer)
            
            # 计算位置
            img_w, img_h = white_bg.size
            aspect = img_h / float(img_w)
            display_w = width - 2 * margin
            display_h = display_w * aspect
            
            # 绘制
            c.drawImage(img_reader, margin, y - 60 - display_h, width=display_w, height=display_h)
            
            print("[PDF Gen] Image drawn successfully.")

        except Exception as e:
            print(f"[PDF Gen Error] {e}")
            c.setFillColor(colors.red)
            c.drawString(margin, y - 100, f"Error rendering image: {e}")
    else:
        c.drawString(margin, y - 100, "No image data available.")

    c.showPage()
    c.save()
    return base64.b64encode(buffer.getvalue()).decode('utf-8')