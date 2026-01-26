import os
import logging
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Tuple, List, Dict, Any, Optional

logger = logging.getLogger("ImageGenerator")

# ==================== 配置常量 ====================

class Fonts:
    MSYH = "C:/Windows/Fonts/msyh.ttc"
    SIMHEI = "C:/Windows/Fonts/simhei.ttf"
    
    @classmethod
    def get_path(cls):
        return cls.MSYH if os.path.exists(cls.MSYH) else cls.SIMHEI

class Colors:
    BG_TOP = (25, 30, 40)
    BG_BOTTOM = (15, 18, 22)
    CARD_BG = (40, 44, 52)
    ROW_ODD = (40, 44, 52)
    ROW_EVEN = (35, 38, 45)
    TEXT_MAIN = (255, 255, 255)
    TEXT_SUB = (180, 185, 195)
    BAR_BG = (60, 65, 75)
    GREEN = (80, 220, 100)
    YELLOW = (255, 200, 50)
    RED = (255, 80, 80)
    ACCENT = (100, 150, 255)

# ==================== 基础绘图工具 ====================

def draw_rounded_rectangle(draw: ImageDraw.ImageDraw, coords: List[float], radius: int, fill=None, outline=None, width=1):
    """绘制圆角矩形"""
    x1, y1, x2, y2 = coords
    w = x2 - x1
    h = y2 - y1
    
    if w < 2 * radius or h < 2 * radius:
        draw.rectangle(coords, fill=fill, outline=outline, width=width)
        return

    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill, outline=outline, width=width)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill, outline=outline, width=width)
    draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill, outline=outline, width=width)
    draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill, outline=outline, width=width)
    draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill, outline=outline, width=width)
    draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill, outline=outline, width=width)

def get_image_from_url(url: str, proxy: Optional[str] = None) -> Optional[Image.Image]:
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
    except Exception as e:
        logger.warning(f"下载图片失败: {url}, error: {e}")
    return None

def create_gradient_background(width: int, height: int, start_color: Tuple[int, int, int], end_color: Tuple[int, int, int]) -> Image.Image:
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

def load_font(size: int) -> ImageFont.FreeTypeFont:
    """加载字体，失败则回退到默认"""
    try:
        return ImageFont.truetype(Fonts.get_path(), size)
    except:
        return ImageFont.load_default()

def wrap_text(text: str, max_width: int, font: ImageFont.FreeTypeFont) -> List[str]:
    """文本自动换行"""
    if not text or text == "暂无简介":
        return ["暂无简介"]
    
    text = str(text)
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

# ==================== vrchat绘图函数 ====================

def generate_instance_image(instances: List[Dict[str, Any]], output_path: str, proxy: Optional[str] = None) -> str:
    """生成 VRChat 群组实例列表图片"""
    width = 1000
    card_margin = 30
    card_height = 200
    header_height = 180
    footer_height = 40
    
    if not instances:
        instances = [{"worldName": "当前无活跃实例", "n_users": 0, "capacity": 0, "region": "-"}]
    
    height = header_height + len(instances) * (card_height + 25) + footer_height
    image = create_gradient_background(width, height, Colors.BG_TOP, Colors.BG_BOTTOM)
    draw = ImageDraw.Draw(image)
    
    font_title = load_font(56)
    font_world = load_font(36)
    font_stats = load_font(28)
    font_region = load_font(22)

    draw.text((card_margin + 10, 50), "活跃实例列表", font=font_title, fill=Colors.TEXT_MAIN)
    
    for i, inst in enumerate(instances):
        y_start = header_height + i * (card_height + 25)
        card_coords = [card_margin, y_start, width - card_margin, y_start + card_height]
        draw_rounded_rectangle(draw, card_coords, 15, fill=Colors.CARD_BG)
        
        world_data = inst.get("world") or {}
        world_name = inst.get("worldName") or world_data.get("name") or "未知世界"
        thumbnail_url = inst.get("imageUrl") or world_data.get("imageUrl") or inst.get("thumbnailUrl") or world_data.get("thumbnailImageUrl")
        
        users = inst.get("n_users") or inst.get("memberCount") or 0
        capacity = inst.get("capacity") or inst.get("maxCapacity") or world_data.get("capacity") or world_data.get("maxCapacity") or 0
        display_capacity = capacity if capacity > 0 else "0"
        region = inst.get("region", "us").upper()
        
        # 绘制缩略图
        img_padding = 15
        img_height = card_height - (img_padding * 2)
        img_width = int(img_height * 1.5)
        img_x = card_margin + img_padding
        img_y = y_start + img_padding
        
        draw_rounded_rectangle(draw, [img_x, img_y, img_x + img_width, img_y + img_height], 8, fill=(30, 30, 30))
        
        if thumbnail_url:
            try:
                thumb = get_image_from_url(thumbnail_url, proxy)
                if thumb:
                    thumb = thumb.resize((img_width, img_height), Image.Resampling.LANCZOS)
                    mask = Image.new("L", (img_width, img_height), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.rounded_rectangle([0, 0, img_width, img_height], radius=8, fill=255)
                    image.paste(thumb, (img_x, img_y), mask)
            except Exception:
                pass

        # 文本信息
        text_x = img_x + img_width + 20
        draw.text((text_x, y_start + 25), world_name, font=font_world, fill=Colors.TEXT_MAIN)
        
        # 进度条
        bar_width = 300
        bar_height = 10
        bar_x = text_x
        bar_y = y_start + 85
        draw_rounded_rectangle(draw, [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 5, fill=Colors.BAR_BG)
        
        if capacity > 0:
            fill_pct = min(users / capacity, 1.0)
            fill_width = int(bar_width * fill_pct)
            bar_color = Colors.GREEN
            if fill_pct > 0.8: bar_color = Colors.RED
            elif fill_pct > 0.5: bar_color = Colors.YELLOW
            
            if fill_width > 0:
                draw_rounded_rectangle(draw, [bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], 5, fill=bar_color)
        
        draw.text((bar_x + bar_width + 15, bar_y - 12), f"{users} / {display_capacity}", font=font_stats, fill=Colors.TEXT_SUB)
        draw.text((width - card_margin - 80, y_start + 20), region, font=font_region, fill=Colors.TEXT_SUB)

    image.save(output_path)
    return output_path

def _init_list_image(width: int, row_height: int, count: int) -> Tuple[Image.Image, ImageDraw.ImageDraw, Dict[str, Any], int, int]:
    """初始化列表类图片的基础画布与字体"""
    header_height = 100
    margin = 30
    
    height = header_height + count * row_height + margin if count else header_height + 100
    image = create_gradient_background(width, height, Colors.BG_TOP, Colors.BG_BOTTOM)
    draw = ImageDraw.Draw(image)
    
    fonts = {
        "title": load_font(40),
        "text": load_font(24),
        "sub": load_font(20),
        "small": load_font(16)
    }
    
    return image, draw, fonts, header_height, margin

def generate_binding_list_image(bindings: List[Dict[str, Any]], output_path: str) -> str:
    """生成绑定列表图片"""
    show_group = any('origin_group_id' in b for b in bindings)
    width = 1300 if show_group else 1100
    row_height = 80
    
    image, draw, fonts, header_height, margin = _init_list_image(width, row_height, len(bindings))
    
    font_title = fonts["title"]
    font_text = fonts["text"]
    font_sub = fonts["sub"]
    font_small = fonts["small"]
        
    draw.text((margin, 20), "VRChat 绑定列表", font=font_title, fill=Colors.TEXT_MAIN)
    
    # 表头
    headers_y = 75
    col_qq_x = margin + 20
    col_vrc_x = 400 if show_group else 500
    col_group_x = 950
    
    draw.text((col_qq_x, headers_y), "QQ 账号", font=font_sub, fill=Colors.TEXT_SUB)
    draw.text((col_vrc_x, headers_y), "VRChat 账号", font=font_sub, fill=Colors.TEXT_SUB)
    if show_group:
        draw.text((col_group_x, headers_y), "来源群组", font=font_sub, fill=Colors.TEXT_SUB)
    
    if not bindings:
        draw.text((width//2 - 50, header_height + 30), "暂无绑定记录", font=font_text, fill=Colors.TEXT_MAIN)
    
    for i, b in enumerate(bindings):
        y = header_height + i * row_height + 10
        bg_color = Colors.ROW_ODD if i % 2 == 0 else Colors.ROW_EVEN
        draw.rectangle([margin, y, width - margin, y + row_height - 5], fill=bg_color)
        
        # QQ Info
        draw.text((col_qq_x, y + 12), b['qq_name'], font=font_text, fill=Colors.TEXT_MAIN)
        draw.text((col_qq_x, y + 45), str(b['qq_id']), font=font_sub, fill=Colors.TEXT_SUB)
        
        # VRC Info
        vrc_name = b['vrc_name']
        max_len = 30 if show_group else 25
        if len(vrc_name) > max_len:
            vrc_name = vrc_name[:max_len-1] + "..."
            
        draw.text((col_vrc_x, y + 12), vrc_name, font=font_text, fill=Colors.TEXT_MAIN)
        draw.text((col_vrc_x, y + 48), b['vrc_id'], font=font_small, fill=Colors.TEXT_SUB)

        if show_group:
            group_id = b.get('origin_group_id')
            group_text = str(group_id) if group_id else "全局/未知"
            draw.text((col_group_x, y + 30), group_text, font=font_text, fill=Colors.TEXT_MAIN)

    image.save(output_path)
    return output_path

def generate_user_info_image(qq_id: int, qq_name: str, vrc_name: str, vrc_id: str, bio: str, output_path: str, avatar_url: Optional[str] = None, proxy: Optional[str] = None, status: Optional[str] = None) -> str:
    """生成用户信息图片"""
    width = 600
    padding = 20
    section_gap = 25
    
    font_bio = load_font(16)
    bio_lines = wrap_text(bio, width - padding * 2, font_bio)
    
    # 动态计算高度: 基础高度 + 简介高度 + (如果有状态则增加的高度)
    base_height = 80 + 140 + 60 + 30 + padding * 2
    if status:
        base_height += 35
    height = base_height + len(bio_lines) * 25
    
    image = create_gradient_background(width, height, Colors.BG_TOP, Colors.BG_BOTTOM)
    draw = ImageDraw.Draw(image)
    
    font_title = load_font(32)
    font_label = load_font(20)
    font_value = load_font(22)
    
    draw.text((padding, 35), "我的绑定信息", font=font_title, fill=Colors.TEXT_MAIN)
    
    # 头像
    card_y = 90
    avatar_size = 80
    avatar_x = padding + 10
    draw_rounded_rectangle(draw, [avatar_x, card_y, avatar_x + avatar_size, card_y + avatar_size], 12, fill=(30, 30, 30))
    
    if avatar_url:
        try:
            avatar = get_image_from_url(avatar_url, proxy)
            if avatar:
                avatar = avatar.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.rounded_rectangle([0, 0, avatar_size, avatar_size], radius=12, fill=255)
                image.paste(avatar, (avatar_x, card_y), mask)
        except Exception:
            pass
    
    draw.text((avatar_x + avatar_size + 20, card_y + 10), vrc_name, font=font_value, fill=Colors.TEXT_MAIN)
    draw.text((avatar_x + avatar_size + 20, card_y + 40), vrc_id, font=font_label, fill=Colors.TEXT_SUB)
    
    info_y = card_y + avatar_size + section_gap
    
    info_rows = [
        row for row in [
            ("QQ 昵称:", qq_name),
            ("QQ 号码:", str(qq_id)),
            ("在线状态:", status) if status else None
        ]
        if row is not None
    ]
    
    for label, value in info_rows:
        draw.text((padding, info_y), label, font=font_label, fill=Colors.TEXT_SUB)
        draw.text((padding + 120, info_y), value, font=font_value, fill=Colors.TEXT_MAIN)
        info_y += 35
    
    separator_y = info_y + 15
    draw.line([padding, separator_y, width - padding, separator_y], fill=Colors.CARD_BG, width=1)
    
    draw.text((padding, separator_y + 15), "VRChat 简介:", font=font_label, fill=Colors.TEXT_SUB)
    
    bio_y = separator_y + 50
    for line in bio_lines:
        draw.text((padding, bio_y), line, font=font_bio, fill=Colors.TEXT_MAIN)
        bio_y += 25
        
    image.save(output_path)
    return output_path

def generate_query_result_image(results: List[Dict[str, Any]], output_path: str) -> str:
    """生成查询结果图片"""
    width = 1300
    row_height = 90
    
    image, draw, fonts, header_height, margin = _init_list_image(width, row_height, len(results))
    
    font_title = fonts["title"]
    font_text = fonts["text"]
    font_sub = fonts["sub"]
    font_small = fonts["small"]
        
    draw.text((margin, 20), "绑定查询结果", font=font_title, fill=Colors.TEXT_MAIN)
    
    headers_y = 75
    col_qq_x = margin + 20
    col_vrc_x = 400
    col_time_x = 850
    col_type_x = 1100
    
    draw.text((col_qq_x, headers_y), "QQ 账号", font=font_sub, fill=Colors.TEXT_SUB)
    draw.text((col_vrc_x, headers_y), "VRChat 账号", font=font_sub, fill=Colors.TEXT_SUB)
    draw.text((col_time_x, headers_y), "绑定时间", font=font_sub, fill=Colors.TEXT_SUB)
    draw.text((col_type_x, headers_y), "方式", font=font_sub, fill=Colors.TEXT_SUB)
    
    if not results:
        draw.text((width//2 - 100, header_height + 30), "未找到匹配记录", font=font_text, fill=Colors.TEXT_MAIN)
    
    for i, b in enumerate(results):
        y = header_height + i * row_height + 10
        bg_color = Colors.ROW_ODD if i % 2 == 0 else Colors.ROW_EVEN
        draw.rectangle([margin, y, width - margin, y + row_height - 5], fill=bg_color)
        
        # QQ Info
        draw.text((col_qq_x, y + 12), b.get('qq_name', '未知'), font=font_text, fill=Colors.TEXT_MAIN)
        draw.text((col_qq_x, y + 45), str(b['qq_id']), font=font_sub, fill=Colors.TEXT_SUB)
        
        # VRC Info
        vrc_name = b.get('vrc_display_name', '未知')
        if len(vrc_name) > 20:
            vrc_name = vrc_name[:19] + "..."
        draw.text((col_vrc_x, y + 12), vrc_name, font=font_text, fill=Colors.TEXT_MAIN)
        draw.text((col_vrc_x, y + 48), b['vrc_user_id'], font=font_small, fill=Colors.TEXT_SUB)
        
        # Time
        draw.text((col_time_x, y + 30), str(b.get('bind_time', '未知')), font=font_sub, fill=Colors.TEXT_MAIN)
        
        # Type
        bind_type = b.get('bind_type', 'manual')
        display_type = "手动绑定" if bind_type == "manual" else "自动绑定" if bind_type == "auto" else "未知"
        draw.text((col_type_x, y + 30), display_type, font=font_sub, fill=Colors.TEXT_MAIN)

    image.save(output_path)
    return output_path