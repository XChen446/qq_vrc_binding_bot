import logging
import pyotp
import asyncio
import time
from typing import Optional
import vrchatapi
from vrchatapi.api import authentication_api
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode
from vrchatapi.rest import UnauthorizedException
from vrchatapi.configuration import Configuration
from vrchatapi import ApiClient

logger = logging.getLogger("VRChatAPI.Auth")

class VRCAuth:
    def __init__(self, client, configuration):
        self.client = client
        self.configuration = configuration
        # 使用ApiClient包装configuration以支持异步调用
        api_client = ApiClient(configuration)
        self.authentication_api = authentication_api.AuthenticationApi(api_client)
        self._last_auth_time = 0
        self._auth_lock = asyncio.Lock()

    async def login(self, username=None, password=None, totp_secret=None) -> bool:
        """异步登录流程"""
        async with self._auth_lock:
            try:
                # 尝试验证现有会话
                if await self._verify_existing_session():
                    logger.info("VRChat 会话仍然有效")
                    return True
            except Exception as e:
                logger.debug(f"验证现有会话失败: {e}")

            username = username or getattr(self.configuration, 'username', '') or (getattr(self.client.config, 'get', lambda x, y: y)('username', ''))
            password = password or getattr(self.configuration, 'password', '') or (getattr(self.client.config, 'get', lambda x, y: y)('password', ''))
            
            if not username or not password:
                logger.error("未找到用户名或密码")
                return False

            try:
                # 更新配置中的用户名和密码
                self.configuration.username = username
                self.configuration.password = password

                # 尝试获取当前用户信息来触发登录
                login_success = await self._perform_login(username, password, totp_secret)
                if login_success:
                    self._last_auth_time = time.time()
                return login_success
            except Exception as e:
                logger.error(f"登录过程发生异常: {e}")
                return False

    async def _verify_existing_session(self) -> bool:
        """检查现有会话是否有效"""
        try:
            # 尝试获取当前用户信息来验证会话
            current_user = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.authentication_api.get_current_user(async_req=True)
            )
            if current_user and hasattr(current_user, 'display_name'):
                logger.info(f"当前用户: {current_user.display_name}")
                return True
        except UnauthorizedException:
            logger.debug("现有会话已过期")
        except vrchatapi.ApiException as e:
            if e.status == 401:
                logger.debug("现有会话认证失败 (401)")
            else:
                logger.debug(f"验证现有会话时发生API错误: {e}")
        except Exception as e:
            logger.debug(f"验证现有会话时发生网络错误: {e}")
        return False

    async def _perform_login(self, username: str, password: str, totp_secret: Optional[str]) -> bool:
        try:
            # 直接尝试获取当前用户信息来触发登录
            current_user = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.authentication_api.get_current_user(async_req=True)
            )
            
            # 检查是否需要2FA
            if hasattr(current_user, 'requires_two_factor_auth') and current_user.requires_two_factor_auth:
                return await self._handle_2fa(totp_secret)
            
            logger.info("VRChat 登录成功")
            return True
        except vrchatapi.ApiException as e:
            if e.status == 401:
                if "twoFactorAuth" in str(e.body) or "2fa" in str(e.body).lower():
                    return await self._handle_2fa(totp_secret)
                else:
                    logger.error(f"登录失败 (401): {e.body}")
                    return False
            elif e.status == 429:
                logger.error(f"登录失败 (429 - 请求频率过高): {e.body}")
                return False
            else:
                logger.error(f"登录失败 ({e.status}): {e.body}")
                return False
        except asyncio.TimeoutError:
            logger.error("登录超时")
            return False
        except ConnectionError:
            logger.error("连接错误，无法连接到VRChat服务器")
            return False
        except Exception as e:
            logger.error(f"登录时发生未知错误: {e}")
            return False

    async def _handle_2fa(self, totp_secret: Optional[str] = None) -> bool:
        verification_type = "totp"  # 默认为TOTP
        code = None
        
        if verification_type == "totp":
            secret = totp_secret or getattr(self.client.config, 'totp_secret', '')
            if secret:
                try:
                    totp = pyotp.TOTP(secret)
                    code = totp.now()
                    logger.info("使用自动TOTP验证码")
                except Exception as e:
                    logger.error(f"生成 TOTP 失败: {e}")
            
            if not code:
                logger.info("需要手动输入验证码")
                try:
                    # 在单独的线程中获取输入，避免阻塞事件循环
                    print(f"\n[TOTP] 请输入 VRChat 验证码: ", end="", flush=True)
                    loop = asyncio.get_running_loop()
                    code = await loop.run_in_executor(None, input)
                    code = code.strip()
                except Exception as e:
                    logger.error(f"获取验证码输入失败: {e}")
                    return False
        
        elif verification_type == "emailOtp":
            logger.info("需要邮箱验证码，请查收邮件")
            try:
                print(f"\n[EMAIL] 请输入 VRChat 邮箱验证码: ", end="", flush=True)
                loop = asyncio.get_running_loop()
                code = await loop.run_in_executor(None, input)
                code = code.strip()
            except Exception as e:
                logger.error(f"获取邮箱验证码输入失败: {e}")
                return False
        
        if code:
            return await self._verify_2fa(code, verification_type)
        return False

    async def _verify_2fa(self, code, method="totp") -> bool:
        try:
            if method == "totp":
                two_factor_request = TwoFactorAuthCode(code=code)
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.authentication_api.verify2_fa(two_factor_auth_code=two_factor_request, async_req=True)
                )
            elif method == "email":
                email_code_request = TwoFactorEmailCode(code=code)
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.authentication_api.verify2_fa_email_code(two_factor_email_code=email_code_request, async_req=True)
                )
            
            logger.info("2FA 验证通过")
            return True
        except vrchatapi.ApiException as e:
            if e.status == 401:
                logger.error(f"2FA 验证失败 (401 - 验证码错误): {e.body}")
            elif e.status == 429:
                logger.error(f"2FA 验证失败 (429 - 请求频率过高): {e.body}")
            else:
                logger.error(f"2FA 验证失败 ({e.status}): {e.body}")
            return False
        except Exception as e:
            logger.error(f"2FA 校验异常: {e}")
            return False

    async def verify_auth(self) -> bool:
        """异步验证会话有效性"""
        try:
            current_user = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.authentication_api.get_current_user(async_req=True)
            )
            if current_user and hasattr(current_user, 'display_name'):
                logger.info(f"当前用户: {current_user.display_name}")
                return True
        except UnauthorizedException:
            logger.warning("认证已过期")
        except vrchatapi.ApiException as e:
            if e.status == 401:
                logger.warning("认证已过期 (401)")
            else:
                logger.error(f"API错误: {e}")
        except Exception as e:
            logger.error(f"验证认证状态失败: {e}")
        return False

    def save_credentials(self, config_path: str = "data/cookies.txt"):
        """保存认证凭据到文件"""
        try:
            # 保存当前配置中的认证信息
            # 注意：vrchatapi库通常会自动管理cookies，我们这里只是提供接口
            if hasattr(self.configuration, '_cookies'):
                import pickle
                with open(config_path, 'wb') as f:
                    pickle.dump(self.configuration._cookies, f)
        except Exception as e:
            logger.error(f"保存认证凭据失败: {e}")

    def load_credentials(self, config_path: str = "data/cookies.txt"):
        """从文件加载认证凭据"""
        try:
            if hasattr(self.configuration, '_cookies'):
                import pickle
                with open(config_path, 'rb') as f:
                    cookies = pickle.load(f)
                    self.configuration._cookies = cookies
        except FileNotFoundError:
            logger.debug("认证凭据文件不存在")
        except Exception as e:
            logger.error(f"加载认证凭据失败: {e}")