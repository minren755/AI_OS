"""
PIL生成公司宣传页设计图（无需API）
"""
from PIL import Image, ImageDraw, ImageFont
import sys
from pathlib import Path


def generate_company_page_image(output_path: str, company_name: str = "AI创世者"):
    """用PIL生成公司宣传页设计图"""
    
    # 画布尺寸
    width, height = 800, 450
    
    # 创建渐变背景
    img = Image.new('RGB', (width, height), '#0a0a1a')
    draw = ImageDraw.Draw(img)
    
    # 渐变背景（深蓝到深紫）
    for y in range(height):
        r = int(10 + y * 0.02)
        g = int(10 + y * 0.05)
        b = int(26 + y * 0.3)
        draw.line([(0, y), (width, y)], fill=(r, g, min(b, 80)))
    
    # 装饰圆形
    draw.ellipse([600, 50, 750, 200], fill=(76, 201, 240, 50))  # 青色圆
    draw.ellipse([650, 280, 780, 400], fill=(247, 37, 133, 30))  # 粉色圆
    
    # Logo区域（左上角）
    draw.rectangle([40, 30, 180, 80], outline=(76, 201, 240), width=2)
    draw.rectangle([45, 35, 175, 75], fill=(26, 26, 46))
    
    # Logo文字
    try:
        logo_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except:
        logo_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    draw.text((60, 42), "AI", fill=(76, 201, 240), font=logo_font)
    draw.ellipse([140, 40, 155, 55], fill=(247, 37, 133))  # 粉色圆点
    
    # 公司名称
    draw.text((40, 120), company_name, fill=(255, 255, 255), font=title_font)
    
    # 核心业务区域
    draw.rectangle([40, 180, 360, 350], fill=(26, 26, 46, 200), outline=(76, 201, 240, 100), width=1)
    draw.text((50, 190), "核心业务", fill=(76, 201, 240), font=subtitle_font)
    
    # 业务列表
    business_items = [
        "• AI解决方案",
        "• 企业智能化",
        "• 数字员工",
        "• 数据分析"
    ]
    
    y_offset = 220
    for item in business_items:
        draw.text((50, y_offset), item, fill=(200, 200, 200), font=subtitle_font)
        y_offset += 30
    
    # 联系方式区域
    draw.rectangle([380, 180, 550, 350], fill=(26, 26, 46, 200), outline=(247, 37, 133, 100), width=1)
    draw.text((390, 190), "联系我们", fill=(247, 37, 133), font=subtitle_font)
    draw.text((390, 230), "Email:", fill=(150, 150, 150), font=subtitle_font)
    draw.text((390, 255), "contact@company.com", fill=(200, 200, 200), font=subtitle_font)
    draw.text((390, 290), "Web:", fill=(150, 150, 150), font=subtitle_font)
    draw.text((390, 315), "aicreator.ren", fill=(200, 200, 200), font=subtitle_font)
    
    # 底部
    draw.text((40, 410), "© 2026 AI创世者 - 让AI为企业赋能", fill=(100, 100, 100), font=subtitle_font)
    
    # 保存
    img.save(output_path, 'PNG', quality=95)
    return output_path


if __name__ == "__main__":
    output = generate_company_page_image("/Users/agent/ai_os/output/company_page_design.png")
    print(f"生成图片: {output}")