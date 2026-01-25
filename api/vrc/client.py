import os
import json
import logging
import aiohttp
import asyncio
from http.cookiejar import LWPCookieJar, Cookie
from urllib.parse import urljoin
from .auth import VRCAuth

logger = logging.getLogger("VRChatAPI")

class VRCApiClient:
    BASE_URL = "https://api.vrchat.cloud/api/1/"

    def __init__(self, config, cookie_path="data/cookies.txt"):
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
            except:
                pass
        
        self.proxy = config.proxy
        self._session = None
        self._semaphore = asyncio.Semaphore(5)
        self.auth = VRCAuth(self)

    async def get_session(self):
        if self._session is None or self._session.closed:
            cookie_dict = {cookie.name: cookie.value for cookie in self.cookies}
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                cookies=cookie_dict,
                connector=aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def save_cookies(self):
        if self._session:
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
        try:
            os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
            self.cookies.save(ignore_discard=True, ignore_expires=True)
        except Exception as e:
            logger.error(f"保存 Cookies 失败: {e}")

    async def _request(self, method, endpoint, retry_on_auth=True, **kwargs):
        url = urljoin(self.BASE_URL, endpoint)
        session = await self.get_session()
        
        async with self._semaphore:
            try:
                if self.proxy:
                    kwargs["proxy"] = self.proxy
                async with session.request(method, url, **kwargs) as response:
                    status = response.status
                    if 200 <= status < 300:
                        if status == 204 or response.content_length == 0:
                            return True
                        return await response.json()
                    
                    if status == 401 and retry_on_auth:
                        if await self.auth.login():
                            return await self._request(method, endpoint, retry_on_auth=False, **kwargs)
                    
                    logger.error(f"VRC API 错误: {method} {url} (HTTP {status})")
                    return None
            except Exception as e:
                logger.error(f"VRC API 请求异常: {e}")
                return None

    async def search_user(self, query):
        if query.startswith("usr_"):
            return [await self.get_user(query)]
        return await self._request("GET", "users", params={"search": query, "n": 10}) or []

    async def get_user(self, user_id):
        return await self._request("GET", f"users/{user_id}")

    async def get_group_member(self, group_id, user_id):
        return await self._request("GET", f"groups/{group_id}/members/{user_id}")

    async def add_group_role(self, group_id: str, user_id: str, role_id: str):
        return await self._request("PUT", f"groups/{group_id}/members/{user_id}/roles/{role_id}")

    async def get_group_instances(self, group_id: str):
        return await self._request("GET", f"groups/{group_id}/instances")
