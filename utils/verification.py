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

async def assign_vrc_role(bot, vrc_id: str) -> bool:
    """尝试在 VRChat 群组中分配角色"""
    try:
        if not bot.vrc_config.verification.get("auto_assign_role"):
            return False

        vrc_group_id = bot.vrc_config.verification.get("group_id")
        target_role_id = bot.vrc_config.verification.get("target_role_id")
        
        if vrc_group_id and target_role_id:
            await bot.vrc_client.add_group_role(vrc_group_id, vrc_id, target_role_id)
            logger.info(f"已为用户 {vrc_id} 分配角色 {target_role_id}")
            return True
    except Exception as e:
        logger.warning(f"自动分配角色失败 ({vrc_id}): {e}")
        return False
    return False
