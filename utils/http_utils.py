import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("HTTPUtils")

async def request(
    method: str,
    url: str,
    session: Optional[aiohttp.ClientSession] = None,
    retries: int = 3,
    backoff: float = 1.0,
    **kwargs
) -> Optional[Any]:
    """
    通用的异步 HTTP 请求封装，支持重试和自定义 Session
    """
    _session = session or aiohttp.ClientSession()
    try:
        for i in range(retries):
            try:
                async with _session.request(method, url, **kwargs) as response:
                    if 200 <= response.status < 300:
                        try:
                            return await response.json()
                        except:
                            return await response.text()
                    else:
                        logger.warning(f"请求失败: {method} {url} (HTTP {response.status})")
                        if response.status >= 500:
                            await asyncio.sleep(backoff * (2 ** i))
                            continue
                        return None
            except Exception as e:
                logger.error(f"请求发生异常 ({i+1}/{retries}): {e}")
                if i < retries - 1:
                    await asyncio.sleep(backoff * (2 ** i))
                else:
                    return None
    finally:
        if session is None:
            await _session.close()
    return None
