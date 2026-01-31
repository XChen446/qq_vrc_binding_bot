import asyncio
import json
import logging
import os
import time
from typing import Optional

import pyotp
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode
from vrchatapi.rest import ApiException

logger = logging.getLogger("VRChatAPI.Auth")


class VRCAuth:
    def __init__(self, client, configuration):
        """
        VRChat 认证管理器
        
        Args:
            client: VRCApiClient 实例
            configuration: VRChat API 配置
        """
        self.client = client
        self.configuration = configuration
        
        # 从client实例获取API客户端，确保所有API实例共享同一个ApiClient
        # 这样可以确保认证信息在所有API实例之间共享
        self.authentication_api = client.authentication_api
        self.users_api = client.users_api  # 添加users_api引用，以便后续可能需要使用
        self._last_auth_time = 0
        self._auth_lock = asyncio.Lock()

    async def login(self, username=None, password=None, totp_secret=None) -> bool:
        """
        主要登录方法 - 支持会话恢复和双因素认证
        
        Args:
            username: 用户名或邮箱（可选，从配置获取）
            password: 密码（可选，从配置获取）
            totp_secret: TOTP密钥（可选）
            
        Returns:
            bool: 登录是否成功
        """
        async with self._auth_lock:
            try:
                # 1. 尝试恢复现有会话
                if await self._try_restore_session():
                    logger.info("VRChat 会话恢复成功")
                    return True
                
                # 2. 获取登录凭据
                username = username or getattr(self.configuration, 'username', '') or (
                    getattr(self.client.config, 'get', lambda x, y: y)('username', ''))
                password = password or getattr(self.configuration, 'password', '') or (
                    getattr(self.client.config, 'get', lambda x, y: y)('password', ''))
                
                if not username or not password:
                    logger.error("缺少用户名或密码")
                    return False

                # 3. 执行登录流程
                login_success = await self._execute_login_flow(username, password, totp_secret)
                
                if login_success:
                    self._last_auth_time = time.time()
                    logger.info("VRChat 登录成功")
                    # 登录成功后立即保存认证信息
                    self.save_credentials()
                else:
                    logger.error("VRChat 登录失败")
                    
                return login_success
                
            except Exception as e:
                logger.error(f"登录过程发生异常: {e}", exc_info=True)
                return False

    async def _try_restore_session(self) -> bool:
        """
        尝试恢复现有会话
        
        Returns:
            bool: 会话是否有效
        """
        try:
            # 尝试获取当前用户信息来验证会话
            loop = asyncio.get_event_loop()
            current_user = await loop.run_in_executor(
                None, 
                lambda: self.authentication_api.get_current_user()
            )
            
            # 检查是否是有效的用户对象（包含display_name等用户信息）
            if hasattr(current_user, 'display_name') and current_user.display_name:
                logger.info(f"会话有效 - 当前用户: {current_user.display_name}")
                return True
                
        except ApiException as e:
            if e.status == 401:
                logger.debug("现有会话已过期 (401)")
            else:
                logger.debug(f"验证现有会话时发生API错误: {e}")
        except Exception as e:
            logger.debug(f"验证现有会话时发生网络错误: {e}")
        
        return False

    async def _execute_login_flow(self, username: str, password: str, totp_secret: Optional[str]) -> bool:
        """
        执行登录流程 - 严格按照temp_vrchat_test.py的实现方式
        """
        try:
            # 更新配置中的用户名和密码
            self.configuration.username = username
            self.configuration.password = password

            loop = asyncio.get_event_loop()
            
            try:
                # 直接调用get_current_user来触发登录
                current_user = await loop.run_in_executor(
                    None,
                    lambda: self.authentication_api.get_current_user()
                )
                
                # 检查是否需要两步验证
                if hasattr(current_user, 'requires_two_factor_auth') and current_user.requires_two_factor_auth:
                    logger.info("检测到需要两步验证...")
                    
                    # 确定验证类型
                    verification_type = "totp"  # 默认为TOTP
                    if isinstance(current_user.requires_two_factor_auth, list):
                        if 'emailOtp' in current_user.requires_two_factor_auth:
                            verification_type = 'emailOtp'
                        elif 'totp' in current_user.requires_two_factor_auth:
                            verification_type = 'totp'
                        elif 'phoneOtp' in current_user.requires_two_factor_auth:
                            verification_type = 'phoneOtp'
                    
                    auth_success = await self._handle_two_factor_auth(totp_secret, verification_type)
                    if auth_success:
                        # 双因素认证成功后保存认证信息
                        self.save_credentials()
                    return auth_success
                else:
                    # 如果没有需要双因素认证，登录成功
                    logger.info("无需双因素认证，登录成功")
                    return True

            except ApiException as e:
                # 检查错误是否包含双因素认证信息
                error_body_lower = str(e.body).lower()
                
                # 检查是否需要双因素认证
                if "2fa" in error_body_lower or "twofactorauth" in error_body_lower or "emailotp" in error_body_lower:
                    logger.info("检测到需要双因素认证...")
                    
                    # 确定验证类型
                    if "emailotp" in error_body_lower:
                        verification_type = "emailOtp"
                    elif "totp" in error_body_lower:
                        verification_type = "totp"
                    else:
                        verification_type = "totp"  # 默认
                        
                    auth_success = await self._handle_two_factor_auth(totp_secret, verification_type)
                    if auth_success:
                        # 双因素认证成功后保存认证信息
                        self.save_credentials()
                    return auth_success
                elif e.status == 401:
                    # 其他401错误
                    logger.error(f"认证失败 (401): {e.body}")
                    return False
                elif e.status == 429:
                    # 根据规则，429状态码可能是提醒用户查看邮箱的情况
                    if "email" in error_body_lower or "hold your horses" in error_body_lower or "something to that email" in error_body_lower:
                        logger.info("服务器提示检查邮箱，需要邮箱验证码")
                        auth_success = await self._handle_two_factor_auth(totp_secret, "emailOtp")
                        if auth_success:
                            self.save_credentials()
                        return auth_success
                    else:
                        logger.error(f"请求频率过高 (429): {e.body}")
                        return False
                else:
                    logger.error(f"API错误 ({e.status}): {e.body}")
                    return False
                    
        except Exception as e:
            logger.error(f"登录时发生未知错误: {e}", exc_info=True)
            return False

    async def _handle_two_factor_auth(self, totp_secret: Optional[str] = None, verification_type: str = 'emailOtp') -> bool:
        """
        处理双因素认证流程
        
        Args:
            totp_secret: TOTP密钥（可选）
            verification_type: 验证类型 ('emailOtp', 'totp', 'phoneOtp')
            
        Returns:
            bool: 双因素认证是否成功
        """
        try:
            # 优先检查环境变量中是否有预设验证码
            otp_code = None
            if verification_type == 'emailOtp':
                otp_code = os.getenv('VRCHAT_EMAIL_OTP_CODE') or os.getenv('VRCHAT_OTP_CODE')
            elif verification_type == 'phoneOtp':
                otp_code = os.getenv('VRCHAT_PHONE_OTP_CODE') or os.getenv('VRCHAT_OTP_CODE')
            elif verification_type == 'totp':
                otp_code = os.getenv('VRCHAT_TOTP_CODE') or os.getenv('VRCHAT_OTP_CODE')
            
            actual_verification_type = verification_type
            if otp_code:
                logger.info(f"使用环境变量中的{verification_type}验证码")
            else:
                # 从配置中获取TOTP密钥
                secret = totp_secret or getattr(self.client.config, 'totp_secret', '')
                
                if secret and verification_type == 'totp':
                    # 自动计算TOTP验证码
                    try:
                        totp = pyotp.TOTP(secret)
                        otp_code = totp.now()
                        actual_verification_type = 'totp'
                        logger.info("使用自动TOTP验证码")
                    except Exception as e:
                        logger.warning(f"生成TOTP失败: {e}")
                
                if not otp_code:
                    # 进入交互式输入模式
                    otp_code = await self._get_interactive_otp_input(verification_type)
                    if not otp_code:
                        logger.error("未能获取验证码")
                        return False
            
            # 验证验证码
            return await self._verify_two_factor_code(otp_code, actual_verification_type)
            
        except Exception as e:
            logger.error(f"处理双因素认证时发生错误: {e}", exc_info=True)
            return False

    async def _get_interactive_otp_input(self, verification_type: str) -> Optional[str]:
        """
        交互式获取OTP验证码
        
        Args:
            verification_type: 验证类型
            
        Returns:
            str: 验证码，如果取消或出错则返回None
        """
        try:
            if verification_type == "emailOtp":
                print(f"\n[EMAIL OTP] 请检查您的邮箱，输入VRChat验证码: ", end="", flush=True)
            elif verification_type == "totp":
                print(f"\n[TOTP] 请输入VRChat验证码 (来自身份验证器): ", end="", flush=True)
            elif verification_type == "phoneOtp":
                print(f"\n[PHONE OTP] 请输入手机收到的VRChat验证码: ", end="", flush=True)
            else:
                print(f"\n[2FA] 请输入VRChat验证码: ", end="", flush=True)
            
            # 使用线程池执行器来安全地获取用户输入，避免阻塞事件循环
            loop = asyncio.get_running_loop()
            otp_code = await loop.run_in_executor(None, input)
            otp_code = otp_code.strip()
            
            if not otp_code:
                logger.warning("未输入验证码")
                return None
                
            logger.info(f"收到验证码输入，长度: {len(otp_code)}")
            return otp_code
            
        except KeyboardInterrupt:
            logger.warning("用户取消了验证码输入")
            return None
        except Exception as e:
            logger.error(f"获取验证码输入失败: {e}", exc_info=True)
            return None

    async def _verify_two_factor_code(self, code: str, verification_type: str) -> bool:
        """
        验证双因素认证码
        
        Args:
            code: 验证码
            verification_type: 验证类型 ('totp', 'email', 'phone')
            
        Returns:
            bool: 验证是否成功
        """
        try:
            loop = asyncio.get_event_loop()
            
            if verification_type.lower() in ['totp', 'totp']:
                # TOTP 验证
                two_factor_request = TwoFactorAuthCode(code=code)
                await loop.run_in_executor(
                    None,
                    lambda: self.authentication_api.verify2_fa(two_factor_auth_code=two_factor_request)
                )
            elif verification_type.lower() in ['email', 'emailotp']:
                # 邮箱验证码验证
                email_code_request = TwoFactorEmailCode(code=code)
                await loop.run_in_executor(
                    None,
                    lambda: self.authentication_api.verify2_fa_email_code(two_factor_email_code=email_code_request)
                )
            elif verification_type.lower() in ['phone', 'phoneotp']:
                # 手机验证码验证 (如果支持)
                email_code_request = TwoFactorEmailCode(code=code)
                await loop.run_in_executor(
                    None,
                    lambda: self.authentication_api.verify2_fa_email_code(two_factor_email_code=email_code_request)
                )
            else:
                logger.error(f"不支持的验证类型: {verification_type}")
                return False
            
            logger.info(f"{verification_type.upper()} 验证成功")
            return True
            
        except ApiException as e:
            if e.status == 401:
                logger.error(f"双因素认证失败 (401 - 验证码错误): {e.body}")
            elif e.status == 429:
                logger.error(f"双因素认证失败 (429 - 请求频率过高): {e.body}")
            else:
                logger.error(f"双因素认证失败 ({e.status}): {e.body}")
            return False
        except Exception as e:
            logger.error(f"双因素认证校验异常: {e}", exc_info=True)
            return False

    async def verify_auth(self) -> bool:
        """
        验证当前认证状态
        
        Returns:
            bool: 认证是否有效
        """
        try:
            loop = asyncio.get_event_loop()
            current_user = await loop.run_in_executor(
                None,
                lambda: self.authentication_api.get_current_user()
            )
            
            if current_user and hasattr(current_user, 'display_name'):
                logger.debug(f"认证有效 - 用户: {current_user.display_name}")
                return True
        except ApiException as e:
            if e.status == 401:
                logger.debug("认证已过期 (401)")
            else:
                logger.error(f"API错误: {e}")
        except Exception as e:
            logger.error(f"验证认证状态失败: {e}", exc_info=True)
        return False

    def save_credentials(self, config_path: str = "data/cookies.txt"):
        """
        保存认证凭据到文件
        
        Args:
            config_path: 配置文件路径
        """
        try:
            # 获取当前API客户端的cookie信息
            cookies_dict = {}
            
            # 从ApiClient中提取认证相关的cookie
            if hasattr(self.authentication_api.api_client, 'cookie'):
                cookie_str = self.authentication_api.api_client.cookie
                if cookie_str:
                    # 解析cookie字符串
                    for cookie_part in cookie_str.split(';'):
                        cookie_part = cookie_part.strip()
                        if '=' in cookie_part:
                            key, value = cookie_part.split('=', 1)
                            cookies_dict[key] = value
            
            # 获取用户名等信息
            credentials = {
                'username': getattr(self.configuration, 'username', ''),
                'auth': cookies_dict.get('auth'),
                'twoFactorAuth': cookies_dict.get('twoFactorAuth'),
                'last_updated': time.time()
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # 保存到JSON文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2, ensure_ascii=False)
                
            logger.info(f"认证信息已保存到 {config_path}")
        except Exception as e:
            logger.error(f"保存认证凭据失败: {e}", exc_info=True)

    def load_credentials(self, config_path: str = "data/cookies.txt"):
        """
        从文件加载认证凭据
        
        Args:
            config_path: 配置文件路径
        """
        try:
            if not os.path.exists(config_path):
                logger.debug(f"认证凭据文件不存在: {config_path}")
                return False

            with open(config_path, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
            
            # 恢复认证cookie
            auth_cookie = credentials.get('auth')
            two_fa_cookie = credentials.get('twoFactorAuth')
            
            if auth_cookie or two_fa_cookie:
                cookie_parts = []
                if auth_cookie:
                    cookie_parts.append(f"auth={auth_cookie}")
                if two_fa_cookie:
                    cookie_parts.append(f"twoFactorAuth={two_fa_cookie}")
                
                cookie_str = "; ".join(cookie_parts)
                
                # 重要：确保所有API实例都能使用相同的cookie
                # 更新client实例中所有API的cookie
                self.client.authentication_api.api_client.cookie = cookie_str
                self.client.users_api.api_client.cookie = cookie_str
                self.client.groups_api.api_client.cookie = cookie_str
                
                logger.info(f"从 {config_path} 恢复认证信息")
                return True
            else:
                logger.debug("认证文件中没有有效的认证信息")
                return False
                
        except FileNotFoundError:
            logger.debug(f"认证凭据文件不存在: {config_path}")
        except json.JSONDecodeError as e:
            logger.error(f"认证凭据文件格式错误: {e}")
        except Exception as e:
            logger.error(f"加载认证凭据失败: {e}", exc_info=True)
        
        return False