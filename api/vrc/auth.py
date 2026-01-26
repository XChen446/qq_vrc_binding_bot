import aiohttp
import logging
import pyotp
import asyncio
from urllib.parse import urljoin
from typing import Optional

logger = logging.getLogger("VRChatAPI.Auth")

class VRCAuth:
    def __init__(self, client):
        self.client = client
        self.base_url = client.BASE_URL

    async def login(self, username=None, password=None, totp_secret=None) -> bool:
        """异步登录流程"""
        username = username or self.client.config.username
        password = password or self.client.config.password
        
        if not username or not password:
            logger.error("未找到用户名或密码")
            return False

        auth = aiohttp.BasicAuth(username, password)
        try:
            return await self._perform_login(auth, totp_secret)
        except Exception as e:
            logger.error(f"登录过程发生异常: {e}")
            return False

    async def _perform_login(self, auth: aiohttp.BasicAuth, totp_secret: Optional[str]) -> bool:
        session = await self.client.get_session()
        url = urljoin(self.base_url, "auth/user")
        
        async with session.get(url, auth=auth) as response:
            data = await response.json()
            
            if "requiresTwoFactorAuth" in data:
                return await self._handle_2fa(data, totp_secret)
            
            if response.status == 200:
                logger.info("VRChat 登录成功")
                self.client.save_cookies()
                return True
            else:
                logger.error(f"登录失败 ({response.status}): {data}")
                return False

    async def _handle_2fa(self, data, totp_secret=None) -> bool:
        verification_type = data["requiresTwoFactorAuth"][0]
        code = None
        
        if verification_type == "totp":
            secret = totp_secret or self.client.config.totp_secret
            if secret:
                try:
                    totp = pyotp.TOTP(secret)
                    code = totp.now()
                except Exception as e:
                    logger.error(f"生成 TOTP 失败: {e}")
            
            if not code:
                logger.warning("未配置 TOTP 密钥或生成失败，尝试手动输入")
        
        elif verification_type == "emailOtp":
            logger.info("需要邮箱验证码，请查收邮件")
        
        if not code:
            try:
                # 在单独的线程中获取输入，避免阻塞事件循环
                print(f"\n[{verification_type}] 请输入 VRChat 验证码: ", end="", flush=True)
                loop = asyncio.get_running_loop()
                code = await loop.run_in_executor(None, input)
                code = code.strip()
            except Exception as e:
                logger.error(f"获取验证码输入失败: {e}")
                return False
            
        if code:
            return await self._verify_2fa(code, verification_type)
        return False

    async def _verify_2fa(self, code, method="totp") -> bool:
        endpoint = f"auth/twofactorauth/{method}/verify"
        url = urljoin(self.base_url, endpoint)
        try:
            session = await self.client.get_session()
            async with session.post(url, json={"code": code}) as response:
                if response.status == 200:
                    logger.info("2FA 验证通过")
                    self.client.save_cookies()
                    return True
                else:
                    logger.error(f"2FA 验证失败 ({response.status})")
                    return False
        except Exception as e:
            logger.error(f"2FA 校验异常: {e}")
            return False

    async def verify_auth(self) -> bool:
        """异步验证会话有效性"""
        try:
            data = await self.client._request("GET", "auth/user", retry_on_auth=False)
            if data and "id" in data:
                logger.info(f"当前用户: {data['displayName']}")
                return True
        except Exception:
            pass
        return False
