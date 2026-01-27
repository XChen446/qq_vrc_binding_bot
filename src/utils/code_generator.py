import random
import string

def generate_verification_code(length: int = 6) -> str:
    """生成指定长度的数字验证码
    
    Args:
        length: 验证码长度，默认为6位
        
    Returns:
        str: 生成的数字验证码
    """
    return ''.join(random.choices(string.digits, k=length))

def generate_random_string(length: int = 8, charset: str = string.ascii_letters + string.digits) -> str:
    """生成指定长度的随机字符串
    
    Args:
        length: 字符串长度，默认为8
        charset: 字符集，默认为字母+数字
        
    Returns:
        str: 生成的随机字符串
    """
    return ''.join(random.choices(charset, k=length))