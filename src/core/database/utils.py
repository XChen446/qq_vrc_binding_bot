import asyncio
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger("Database.Utils")

async def safe_db_operation(db_func: Callable, *args, **kwargs) -> Optional[Any]:
    """安全的数据库操作包装器，带重试机制
    
    Args:
        db_func: 数据库操作函数
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        操作结果，失败时返回None
    """
    max_retries = 3
    base_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            return await asyncio.to_thread(db_func, *args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                if any(keyword in error_msg.lower() for keyword in ["read of closed file", "connection", "cursor", "closed"]):
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"数据库操作失败，正在重试 (attempt {attempt + 1}/{max_retries}): {e}")
                    await asyncio.sleep(delay)
                    continue
            
            logger.error(f"数据库操作最终失败: {e}")
            return None
    
    return None