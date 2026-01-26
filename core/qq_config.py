import logging
from typing import Dict, Any

logger = logging.getLogger("QQConfig")

class QQConfig:
    def __init__(self, data: Dict[str, Any]):
        napcat_data = data.get("napcat", {})
        self.ws_url: str = napcat_data.get("ws_url", "")
        self.token: str = napcat_data.get("token", "")
        self.command_prefix: str = "!"
        self.ws_max_retries: int = napcat_data.get("ws_max_retries", 10)
        self.ws_initial_delay: float = napcat_data.get("ws_initial_delay", 5.0)
        self.ws_max_delay: float = napcat_data.get("ws_max_delay", 60.0)
        
        logger.debug(f"已加载 QQ 配置: ws_url={self.ws_url}")

    @property
    def is_valid(self) -> bool:
        """检查配置是否有效"""
        return bool(self.ws_url)
