import logging
from typing import Optional

logger = logging.getLogger("Admin.Utils")

def is_super_admin(user_id: int, admin_qq_list: list) -> bool:
    """检查用户是否为超级管理员
    
    Args:
        user_id: 用户QQ号
        admin_qq_list: 超级管理员QQ号列表
        
    Returns:
        bool: 是否为超级管理员
    """
    # 统一转换为字符串进行比较，防止类型不一致导致的判断失败
    user_id_str = str(user_id)
    return any(str(admin_qq) == user_id_str for admin_qq in admin_qq_list)

def is_group_admin_or_owner(user_id: int, group_id: Optional[int], global_config) -> bool:
    """检查用户是否为群管理员或群主
    
    Args:
        user_id: 用户QQ号
        group_id: 群号
        global_config: 全局配置对象
        
    Returns:
        bool: 是否为群管理员或群主
    """
    # 超级管理员直接通过
    if is_super_admin(user_id, global_config.admin_qq):
        return True
        
    if not group_id:
        return False
        
    # 检查群管理员配置
    group_admins = global_config.group_admins.get(str(group_id), [])
    # 同样进行类型兼容处理
    user_id_str = str(user_id)
    return any(str(admin) == user_id_str for admin in group_admins)