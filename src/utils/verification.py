import time
import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger("Utils.Verification")

def calculate_verification_elapsed(verification: Dict[str, Any]) -> float:
    """计算验证请求经过的时间（秒）"""
    # 优先使用数据库计算的 elapsed 时间，避免时区问题
    if "elapsed" in verification and verification["elapsed"] is not None:
        return float(verification["elapsed"])
        
    created_val = verification.get("created_at")
    if isinstance(created_val, datetime.datetime):
        created_ts = created_val.timestamp()
    else:
        try:
            created_ts = float(created_val)
        except (ValueError, TypeError):
            created_ts = time.time()
            
    return time.time() - created_ts

async def assign_vrc_role(bot, vrc_id: str, group_id: int = None) -> bool:
    """尝试在 VRChat 群组中分配角色"""
    try:
        # 只使用群组特定配置，因为全局配置中不再包含群组ID和角色ID
        if group_id is None:
            # 没有提供群组ID，无法分配角色
            return False
            
        # 使用群组配置
        from src.core.database.utils import safe_db_operation
        auto_assign_role_setting = await safe_db_operation(bot.db.get_group_setting, group_id, "auto_assign_role", str(bot.vrc_config.verification.get("auto_assign_role", "False")))
        auto_assign_role = auto_assign_role_setting.lower() == "true"
        
        if not auto_assign_role:
            return False
        
        vrc_group_id = await safe_db_operation(bot.db.get_group_setting, group_id, "vrc_group_id", "")
        target_role_id = await safe_db_operation(bot.db.get_group_setting, group_id, "target_role_id", "")
        
        if not vrc_group_id:
            logger.warning(f"群组 {group_id} 未设置 VRChat 群组 ID，无法分配角色")
            return False
        
        if not target_role_id:
            logger.warning(f"群组 {group_id} 未设置目标角色 ID，无法分配角色")
            return False
        
        # 检查机器人账号是否拥有分配角色的权限
        # 这里可以添加更详细的权限检查逻辑，但现在只是输出提醒日志
        logger.info(f"准备为用户 {vrc_id} 在群组 {group_id} 中分配角色 {target_role_id} (VRChat群组: {vrc_group_id})")
        logger.info(f"⚠️ 请确保机器人账号在 VRChat 群组 {vrc_group_id} 中拥有分配角色 {target_role_id} 的权限")
        
        if auto_assign_role and vrc_group_id and target_role_id:
            await bot.vrc_client.add_group_role(vrc_group_id, vrc_id, target_role_id)
            logger.info(f"已为用户 {vrc_id} 分配角色 {target_role_id} (群组: {group_id})")
            return True
    except Exception as e:
        logger.warning(f"自动分配角色失败 ({vrc_id}): {e}")
        return False
    return False
