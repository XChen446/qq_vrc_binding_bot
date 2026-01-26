import os
import logging
import aiohttp
import asyncio
from http.cookiejar import LWPCookieJar, Cookie
from urllib.parse import urljoin
from typing import Optional, Dict, Any, List
from .auth import VRCAuth

logger = logging.getLogger("VRChatAPI")

class VRCApiClient:
    BASE_URL = "https://api.vrchat.cloud/api/1/"

    def __init__(self, config, cookie_path: str = "data/cookies.txt"):
        self.config = config
        self.cookie_path = cookie_path
        
        # 构造 User-Agent
        contact_email = config.username if "@" in config.username else "2748376556@qq.com"
        user_agent = config.user_agent or f"QQVRCBindingBot/1.0 ({contact_email})"
            
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        self.cookies = LWPCookieJar(filename=cookie_path)
        if os.path.exists(cookie_path):
            try:
                self.cookies.load(ignore_discard=True, ignore_expires=True)
            except Exception as e:
                logger.warning(f"加载 Cookies 失败: {e}")
        
        self.proxy = config.proxy
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(5)
        self.auth = VRCAuth(self)

    async def get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp session"""
        if self._session is None or self._session.closed:
            await self._create_session()
        if self._session is None:
            raise RuntimeError("无法创建会话")
        return self._session

    async def _create_session(self) -> None:
        cookie_dict = {cookie.name: cookie.value for cookie in self.cookies}
        self._session = aiohttp.ClientSession(
            headers=self.headers,
            cookies=cookie_dict,
            connector=aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
        )

    async def close(self) -> None:
        """关闭 session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def save_cookies(self) -> None:
        """保存 Cookies 到文件"""
        if self._session:
            self._update_cookies_from_jar()
        try:
            os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
            self.cookies.save(ignore_discard=True, ignore_expires=True)
        except Exception as e:
            logger.error(f"保存 Cookies 失败: {e}")

    def _update_cookies_from_jar(self) -> None:
        if not self._session:
            return
        simple_cookie = self._session.cookie_jar.filter_cookies(self.BASE_URL)
        for name, morsel in simple_cookie.items():
            domain = morsel['domain'] or ".vrchat.cloud"
            path = morsel['path'] or "/"
            c = Cookie(
                version=0, name=name, value=morsel.value, port=None, port_specified=False,
                domain=domain, domain_specified=bool(domain), domain_initial_dot=domain.startswith('.'),
                path=path, path_specified=bool(path), secure=bool(morsel['secure']), expires=None,
                discard=False, comment=None, comment_url=None, rest={'HttpOnly': morsel['httponly']}, rfc2109=False,
            )
            self.cookies.set_cookie(c)

    async def _request(self, method: str, endpoint: str, retry_on_auth: bool = True, **kwargs) -> Optional[Any]:
        """统一请求封装，支持自动重试"""
        url = urljoin(self.BASE_URL, endpoint)
        session = await self.get_session()
        
        async with self._semaphore:
            try:
                if self.proxy:
                    kwargs["proxy"] = self.proxy
                
                logger.debug(f"API 请求: {method} {url} | Params: {kwargs.get('params')} | Data: {bool(kwargs.get('json') or kwargs.get('data'))}")
                async with session.request(method, url, **kwargs) as response:
                    return await self._handle_response(response, method, endpoint, retry_on_auth, **kwargs)
            except Exception as e:
                logger.error(f"VRC API 请求异常: {e}")
                return None

    async def _handle_response(self, response: aiohttp.ClientResponse, method: str, endpoint: str, retry_on_auth: bool, **kwargs) -> Optional[Any]:
        status = response.status
        if 200 <= status < 300:
            logger.debug(f"API 响应成功: {method} {endpoint} (HTTP {status})")
            if status == 204 or response.content_length == 0:
                return True
            try:
                return await response.json()
            except Exception:
                return await response.text()
        
        if status == 401 and retry_on_auth:
            logger.warning("Token 失效，尝试重新登录...")
            if await self.auth.login():
                return await self._request(method, endpoint, retry_on_auth=False, **kwargs)
        
        logger.error(f"VRC API 错误: {method} {endpoint} (HTTP {status})")
        return None

    # ==================== 用户相关接口 ====================

    async def search_user(self, query: str) -> List[Dict[str, Any]]:
        """搜索用户"""
        if query.startswith("usr_"):
            user = await self.get_user(query)
            return [user] if user else []
        result = await self._request("GET", "users", params={"search": query, "n": 10})
        return result if isinstance(result, list) else []

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        return await self._request("GET", f"users/{user_id}")

    # ==================== 群组相关接口 ====================

    async def get_group_member(self, group_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取群组成员信息"""
        return await self._request("GET", f"groups/{group_id}/members/{user_id}")

    async def add_group_role(self, group_id: str, user_id: str, role_id: str) -> Optional[Any]:
        """添加群组角色"""
        return await self._request("PUT", f"groups/{group_id}/members/{user_id}/roles/{role_id}")

    async def get_group_instances(self, group_id: str) -> Optional[Any]:
        """获取群组实例"""
        return await self._request("GET", f"groups/{group_id}/instances")
