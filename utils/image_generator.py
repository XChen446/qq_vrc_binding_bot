import os
import logging
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops
from datetime import datetime
from io import BytesIO

logger = logging.getLogger("ImageGenerator")

def draw_rounded_rectangle(draw, coords, radius, fill=None, outline=None, width=1):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = coords
    w = x2 - x1
    h = y2 - y1
    
    # 尺寸过小，退化为普通矩形
    if w < 2 * radius or h < 2 * radius:
        draw.rectangle(coords, fill=fill, outline=outline, width=width)
        return

    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=width)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=width)
    draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill, outline=outline, width=width)
    draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill, outline=outline, width=width)
    draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill, outline=outline, width=width)
    draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill, outline=outline, width=width)

def get_image_from_url(url, proxy=None):
    """从 URL 获取图片并转换为 PIL 对象"""
    if not url: return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        proxies = {"http": proxy, "https": proxy} if proxy else None
        response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except:
        pass
    return None

def create_gradient_background(width, height, start_color, end_color):
    """创建垂直渐变背景"""
    base = Image.new('RGB', (width, height), start_color)
    top = Image.new('RGB', (width, height), end_color)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def generate_instance_image(instances, output_path, proxy=None):
    """生成 VRChat 群组实例列表图片"""
    width = 1000
    card_margin = 30
    card_height = 200
    header_height = 180
    footer_height = 40
    
    if not instances:
        instances = [{"worldName": "当前无活跃实例", "n_users": 0, "capacity": 0, "region": "-"}]
    
    height = header_height + len(instances) * (card_height + 25) + footer_height
    color_bg_top = (25, 30, 40)
    color_bg_bottom = (15, 18, 22)
    color_card = (40, 44, 52)
    color_text = (255, 255, 255)
    color_subtext = (180, 185, 195)
    color_bar_bg = (60, 65, 75)
    color_green = (80, 220, 100)
    color_yellow = (255, 200, 50)
    color_red = (255, 80, 80)

    image = create_gradient_background(width, height, color_bg_top, color_bg_bottom)
    draw = ImageDraw.Draw(image)
    
    font_path = "C:/Windows/Fonts/msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/simhei.ttf"
        
    try:
        font_title = ImageFont.truetype(font_path, 56)
        font_world = ImageFont.truetype(font_path, 36)
        font_stats = ImageFont.truetype(font_path, 28)
        font_region = ImageFont.truetype(font_path, 22)
    except:
        font_title = font_world = font_stats = font_region = ImageFont.load_default()

    draw.text((card_margin + 10, 50), "活跃实例列表", font=font_title, fill=color_text)
    
    for i, inst in enumerate(instances):
        y_start = header_height + i * (card_height + 25)
        card_coords = [card_margin, y_start, width - card_margin, y_start + card_height]
        draw_rounded_rectangle(draw, card_coords, 15, fill=color_card)
        
        world_data = inst.get("world") or {}
        world_name = inst.get("worldName") or world_data.get("name") or "未知世界"
        thumbnail_url = inst.get("imageUrl") or world_data.get("imageUrl") or inst.get("thumbnailUrl") or world_data.get("thumbnailImageUrl")
        
        users = inst.get("n_users") or inst.get("memberCount") or 0
        capacity = inst.get("capacity") or inst.get("maxCapacity") or world_data.get("capacity") or world_data.get("maxCapacity") or 0
        display_capacity = capacity if capacity > 0 else "0"
        region = inst.get("region", "us").upper()
        
        img_padding = 15
        img_height = card_height - (img_padding * 2)
        img_width = int(img_height * 1.5)
        img_x = card_margin + img_padding
        img_y = y_start + img_padding
        
        # 绘制缩略图占位符
        draw_rounded_rectangle(draw, [img_x, img_y, img_x + img_width, img_y + img_height], 8, fill=(30, 30, 30))
        
        # 尝试下载并绘制缩略图
        if thumbnail_url:
            try:
                thumb = get_image_from_url(thumbnail_url, proxy)
                if thumb:
                    thumb = thumb.resize((img_width, img_height), Image.Resampling.LANCZOS)
                    # 创建圆角遮罩
                    mask = Image.new("L", (img_width, img_height), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.rounded_rectangle([0, 0, img_width, img_height], radius=8, fill=255)
                    image.paste(thumb, (img_x, img_y), mask)
            except:
                pass

        # 文本信息
        text_x = img_x + img_width + 20
        draw.text((text_x, y_start + 25), world_name, font=font_world, fill=color_text)
        
        # 进度条背景
        bar_width = 300
        bar_height = 10
        bar_x = text_x
        bar_y = y_start + 85
        draw_rounded_rectangle(draw, [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 5, fill=color_bar_bg)
        
        # 进度条前景
        if capacity > 0:
            fill_pct = min(users / capacity, 1.0)
            fill_width = int(bar_width * fill_pct)
            bar_color = color_green
            if fill_pct > 0.8: bar_color = color_red
            elif fill_pct > 0.5: bar_color = color_yellow
            
            if fill_width > 0:
                draw_rounded_rectangle(draw, [bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], 5, fill=bar_color)
        
        draw.text((bar_x + bar_width + 15, bar_y - 12), f"{users} / {display_capacity}", font=font_stats, fill=color_subtext)
        draw.text((width - card_margin - 80, y_start + 20), region, font=font_region, fill=color_subtext)

    image.save(output_path)
    return output_path

def generate_binding_list_image(bindings, output_path):
    """生成绑定列表图片"""
    width = 1100  # 增加宽度
    row_height = 80  # 增加行高
    header_height = 100
    margin = 30
    
    if not bindings:
        height = header_height + 100
    else:
        height = header_height + len(bindings) * row_height + margin
        
    color_bg_top = (25, 30, 40)
    color_bg_bottom = (15, 18, 22)
    color_row_odd = (40, 44, 52)
    color_row_even = (35, 38, 45)
    color_text = (255, 255, 255)
    color_subtext = (150, 155, 165)
    
    image = create_gradient_background(width, height, color_bg_top, color_bg_bottom)
    draw = ImageDraw.Draw(image)
    
    font_path = "C:/Windows/Fonts/msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/simhei.ttf"
        
    try:
        font_title = ImageFont.truetype(font_path, 40)
        font_text = ImageFont.truetype(font_path, 24)
        font_sub = ImageFont.truetype(font_path, 20)
        font_small = ImageFont.truetype(font_path, 16) # 用于长ID
    except:
        font_title = font_text = font_sub = font_small = ImageFont.load_default()
        
    draw.text((margin, 20), "VRChat 绑定列表", font=font_title, fill=color_text)
    
    # 表头
    headers_y = 75
    col_qq_x = margin + 20
    col_vrc_x = 500  # VRChat 列起始位置
    
    draw.text((col_qq_x, headers_y), "QQ 账号", font=font_sub, fill=color_subtext)
    draw.text((col_vrc_x, headers_y), "VRChat 账号", font=font_sub, fill=color_subtext)
    
    if not bindings:
        draw.text((width//2 - 50, header_height + 30), "暂无绑定记录", font=font_text, fill=color_text)
    
    for i, b in enumerate(bindings):
        y = header_height + i * row_height + 10
        bg_color = color_row_odd if i % 2 == 0 else color_row_even
        
        draw.rectangle([margin, y, width - margin, y + row_height - 5], fill=bg_color)
        
        # QQ Info (两行显示)
        qq_name = b['qq_name']
        qq_id = str(b['qq_id'])
        draw.text((col_qq_x, y + 12), qq_name, font=font_text, fill=color_text)
        draw.text((col_qq_x, y + 45), qq_id, font=font_sub, fill=color_subtext)
        
        # VRC Info (两行显示)
        vrc_name = b['vrc_name']
        vrc_id = b['vrc_id']
        
        # 如果 VRC 昵称太长，进行截断
        if len(vrc_name) > 25:
            vrc_name = vrc_name[:24] + "..."
            
        draw.text((col_vrc_x, y + 12), vrc_name, font=font_text, fill=color_text)
        # ID 使用小号字体，防止溢出
        draw.text((col_vrc_x, y + 48), vrc_id, font=font_small, fill=color_subtext)

    image.save(output_path)
    return output_path

def generate_user_info_image(qq_id, qq_name, vrc_name, vrc_id, bio, output_path, avatar_url=None, proxy=None):
    """生成用户信息图片"""
    width = 600
    padding = 20
    section_gap = 25
    
    # 预估高度
    bio_lines = wrap_text(bio, width - padding * 2, 16)
    height = 80 + 140 + 60 + 30 + len(bio_lines) * 25 + padding * 2
    
    color_bg_top = (25, 30, 40)
    color_bg_bottom = (15, 18, 22)
    color_card = (40, 44, 52)
    color_text = (255, 255, 255)
    color_subtext = (180, 185, 195)
    color_accent = (100, 150, 255)
    
    image = create_gradient_background(width, height, color_bg_top, color_bg_bottom)
    draw = ImageDraw.Draw(image)
    
    font_path = "C:/Windows/Fonts/msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/simhei.ttf"
        
    try:
        font_title = ImageFont.truetype(font_path, 32)
        font_label = ImageFont.truetype(font_path, 20)
        font_value = ImageFont.truetype(font_path, 22)
        font_bio = ImageFont.truetype(font_path, 16)
    except:
        font_title = font_label = font_value = font_bio = ImageFont.load_default()
    
    # 标题
    draw.text((padding, 35), "我的绑定信息", font=font_title, fill=color_text)
    
    # 头像和基本信息卡片
    card_y = 90
    avatar_size = 80
    avatar_x = padding + 10
    
    # 绘制头像占位符
    draw_rounded_rectangle(draw, [avatar_x, card_y, avatar_x + avatar_size, card_y + avatar_size], 12, fill=(30, 30, 30))
    
    # 尝试下载头像
    if avatar_url:
        try:
            avatar = get_image_from_url(avatar_url, proxy)
            if avatar:
                avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, avatar_size, avatar_size], radius=12, fill=255)
                image.paste(avatar, (avatar_x, card_y), mask)
        except:
            pass
    
    # VRChat 名字
    draw.text((avatar_x + avatar_size + 20, card_y + 10), vrc_name, font=font_value, fill=color_text)
    draw.text((avatar_x + avatar_size + 20, card_y + 40), vrc_id, font=font_label, fill=color_subtext)
    
    # 信息区域
    info_y = card_y + avatar_size + section_gap
    
    def draw_info_row(label, value, y):
        draw.text((padding, y), label, font=font_label, fill=color_subtext)
        draw.text((padding + 120, y), value, font=font_value, fill=color_text)
        return y + 35
    
    info_y = draw_info_row("QQ 昵称:", qq_name, info_y)
    info_y = draw_info_row("QQ 号码:", str(qq_id), info_y)
    
    # 分隔线
    separator_y = info_y + 15
    draw.line([padding, separator_y, width - padding, separator_y], fill=color_card, width=1)
    
    # 简介区域
    draw.text((padding, separator_y + 15), "VRChat 简介:", font=font_label, fill=color_subtext)
    
    bio_y = separator_y + 50
    for line in bio_lines:
        draw.text((padding, bio_y), line, font=font_bio, fill=color_text)
        bio_y += 25
        
    image.save(output_path)
    return output_path

def generate_query_result_image(results, output_path):
    """生成查询结果图片，包含详细信息"""
    width = 1300  # 增加宽度
    row_height = 90  # 行高
    header_height = 100
    margin = 30
    
    if not results:
        height = header_height + 100
    else:
        height = header_height + len(results) * row_height + margin
        
    color_bg_top = (25, 30, 40)
    color_bg_bottom = (15, 18, 22)
    color_row_odd = (40, 44, 52)
    color_row_even = (35, 38, 45)
    color_text = (255, 255, 255)
    color_subtext = (150, 155, 165)
    
    image = create_gradient_background(width, height, color_bg_top, color_bg_bottom)
    draw = ImageDraw.Draw(image)
    
    font_path = "C:/Windows/Fonts/msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/simhei.ttf"
        
    try:
        font_title = ImageFont.truetype(font_path, 40)
        font_text = ImageFont.truetype(font_path, 24)
        font_sub = ImageFont.truetype(font_path, 20)
        font_small = ImageFont.truetype(font_path, 16)
    except:
        font_title = font_text = font_sub = font_small = ImageFont.load_default()
        
    draw.text((margin, 20), "绑定查询结果", font=font_title, fill=color_text)
    
    # 表头
    headers_y = 75
    col_qq_x = margin + 20
    col_vrc_x = 400
    col_time_x = 850
    col_type_x = 1100
    
    draw.text((col_qq_x, headers_y), "QQ 账号", font=font_sub, fill=color_subtext)
    draw.text((col_vrc_x, headers_y), "VRChat 账号", font=font_sub, fill=color_subtext)
    draw.text((col_time_x, headers_y), "绑定时间", font=font_sub, fill=color_subtext)
    draw.text((col_type_x, headers_y), "方式", font=font_sub, fill=color_subtext)
    
    if not results:
        draw.text((width//2 - 100, header_height + 30), "未找到匹配记录", font=font_text, fill=color_text)
    
    for i, b in enumerate(results):
        y = header_height + i * row_height + 10
        bg_color = color_row_odd if i % 2 == 0 else color_row_even
        
        draw.rectangle([margin, y, width - margin, y + row_height - 5], fill=bg_color)
        
        # QQ Info
        qq_name = b.get('qq_name', '未知')
        qq_id = str(b['qq_id'])
        draw.text((col_qq_x, y + 12), qq_name, font=font_text, fill=color_text)
        draw.text((col_qq_x, y + 45), qq_id, font=font_sub, fill=color_subtext)
        
        # VRC Info
        vrc_name = b.get('vrc_display_name', '未知')
        vrc_id = b['vrc_user_id']
        
        if len(vrc_name) > 20:
            vrc_name = vrc_name[:19] + "..."
            
        draw.text((col_vrc_x, y + 12), vrc_name, font=font_text, fill=color_text)
        draw.text((col_vrc_x, y + 48), vrc_id, font=font_small, fill=color_subtext)
        
        # Time
        bind_time = str(b.get('bind_time', '未知'))
        draw.text((col_time_x, y + 30), bind_time, font=font_sub, fill=color_text)
        
        # Type
        bind_type = b.get('bind_type', 'manual')
        display_type = "手动绑定" if bind_type == "manual" else "自动绑定" if bind_type == "auto" else "未知"
        draw.text((col_type_x, y + 30), display_type, font=font_sub, fill=color_text)

    image.save(output_path)
    return output_path

def wrap_text(text, max_width, font_size):
    """文本自动换行"""
    if not text or text == "暂无简介":
        return ["暂无简介"]
    
    text = str(text)
    font_path = "C:/Windows/Fonts/msyh.ttc"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/simhei.ttf"
    
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()
    
    lines = []
    current_line = ""
    
    for char in text:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    
    if current_line:
        lines.append(current_line)
    
    return lines if lines else ["暂无简介"]
