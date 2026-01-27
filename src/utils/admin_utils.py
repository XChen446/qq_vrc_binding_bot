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

async def is_group_admin_or_owner(user_id: int, group_id: Optional[int], qq_client) -> bool:
    """检查用户是否为群管理员或群主，通过 NapCat API 获取真实角色信息
    
    Args:
        user_id: 用户QQ号
        group_id: 群号
        qq_client: QQ客户端实例，用于调用API
        
    Returns:
        bool: 是否为群管理员或群主
    """
    # 超级管理员直接通过
    from src.core.global_config import load_all_config
    config_data = load_all_config("config/config.json")
    if config_data:
        admin_qq_list = config_data.get("bot", {}).get("admin_qq", [])
    else:
        admin_qq_list = []
        
    if is_super_admin(user_id, admin_qq_list):
        return True
        
    if not group_id:
        return False
    
    try:
        # 通过 NapCat API 获取真实的群成员信息
        member_info = await qq_client.get_group_member_info(group_id, user_id)
        if not member_info:
            return False
        
        # 检查 NapCat 返回的角色信息
        role = member_info.get('role', 'member').lower()
        return role in ['owner', 'admin']
        
    except Exception as e:
        logger.error(f"获取群成员角色信息失败: {e}")
        return False