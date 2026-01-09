"""
主应用类
协调各个组件，处理启动、配置和事件循环
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from loguru import logger
import os
from dotenv import load_dotenv

from ..api.async_vrchat_api import AsyncVRChatAPIClient
from ..api.async_vrchat_api_v2 import ImprovedAsyncVRChatAPIClient
from ..core.async_qq_bot import AsyncQQBotManager
from ..core.data_manager import DataManager
from ..utils.message_template import MessageTemplate, DEFAULT_TEMPLATES
from ..utils.logger import AppLogger
from ..handlers.group_handler import GroupHandler
from ..core.cli_handler import CLIHandler


class QQVRCBindingApp:
    """QQ到VRChat双向绑定应用主类"""
    
    def __init__(self, config_file: str = "config/config.yaml"):
        """
        初始化应用
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = None
        self.running = False
        
        # 组件
        self.logger_manager = None
        self.vrc_api = None
        self.qq_bot = None
        self.data_manager = None
        self.message_template = None
        self.group_handler = None
        
        # 事件循环
        self.loop = None
        
        # 加载环境变量
        load_dotenv()
        
        logger.info("QQ-VRC双向绑定应用初始化中...")
    
    async def initialize(self):
        """初始化应用组件"""
        try:
            # 1. 加载配置
            await self._load_config()
            
            # 2. 初始化日志系统
            await self._init_logger()
            
            # 3. 初始化VRChat API客户端
            await self._init_vrc_api()
            
            # 4. 初始化QQ Bot
            await self._init_qq_bot()
            
            # 5. 初始化数据管理器
            await self._init_data_manager()
            
            # 6. 初始化消息模板
            await self._init_message_template()
            
            # 7. 初始化群组处理器
            await self._init_group_handler()
            
            logger.success("应用初始化完成！")
            
        except Exception as e:
            logger.exception(f"应用初始化失败: {e}")
            raise
    
    async def _load_config(self):
        """加载配置文件"""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            # 从环境变量覆盖配置
            self._override_config_from_env()
            
            logger.info(f"配置文件加载成功: {self.config_file}")
            
        except Exception as e:
            logger.exception(f"加载配置文件失败: {e}")
            raise
    
    def _override_config_from_env(self):
        """从环境变量覆盖配置"""
        try:
            # VRChat配置
            if os.getenv('VRCHAT_USERNAME'):
                self.config['vrchat']['username'] = os.getenv('VRCHAT_USERNAME')
            if os.getenv('VRCHAT_PASSWORD'):
                self.config['vrchat']['password'] = os.getenv('VRCHAT_PASSWORD')
            if os.getenv('TOTP_SECRET'):
                self.config['vrchat']['two_factor']['totp_secret'] = os.getenv('TOTP_SECRET')
            
            # 代理配置
            if os.getenv('HTTP_PROXY'):
                self.config['vrchat']['proxy']['http_proxy'] = os.getenv('HTTP_PROXY')
                self.config['vrchat']['proxy']['enabled'] = True
            if os.getenv('HTTPS_PROXY'):
                self.config['vrchat']['proxy']['https_proxy'] = os.getenv('HTTPS_PROXY')
                self.config['vrchat']['proxy']['enabled'] = True
            
            # Napcat配置
            if os.getenv('NAPCAT_ACCESS_TOKEN'):
                self.config['napcat']['access_token'] = os.getenv('NAPCAT_ACCESS_TOKEN')
            
        except Exception as e:
            logger.warning(f"从环境变量覆盖配置时出错: {e}")
    
    async def _init_logger(self):
        """初始化日志系统"""
        try:
            app_config = self.config.get('app', {})
            log_level = app_config.get('log_level', 'INFO')
            log_dir = app_config.get('log_dir', './logs')
            
            self.logger_manager = AppLogger(
                log_dir=log_dir,
                log_level=log_level
            )
            
            # 设置全局日志级别
            self.logger_manager.set_log_level(log_level)
            
            logger.success("日志系统初始化完成")
            
        except Exception as e:
            logger.exception(f"初始化日志系统失败: {e}")
            raise
    
    async def _init_vrc_api(self):
        """初始化VRChat API客户端"""
        try:
            vrc_config = self.config.get('vrchat', {})
            
            # 检查必要配置
            username = vrc_config.get('username')
            password = vrc_config.get('password')
            
            if not username or not password:
                raise ValueError("VRChat用户名或密码未配置")
            
            # 代理配置
            proxy_config = None
            if vrc_config.get('proxy', {}).get('enabled', False):
                proxy_config = {
                    'http': vrc_config['proxy'].get('http_proxy'),
                    'https': vrc_config['proxy'].get('https_proxy')
                }
            
            # TOTP密钥
            totp_secret = vrc_config.get('two_factor', {}).get('totp_secret')
            
            # 数据目录配置
            data_dir = self.config.get('app', {}).get('data_dir', './data')
            cookie_file = Path(data_dir) / 'vrchat_cookie.json'
            
            # TOTP配置
            totp_config = vrc_config.get('two_factor', {})
            totp_secret = totp_config.get('totp_secret')
            auto_generate_totp = totp_config.get('auto_generate', False)
            
            # 创建改进版API客户端
            self.vrc_api = ImprovedAsyncVRChatAPIClient(
                username=username,
                password=password,
                cookie_file=str(cookie_file),
                proxy_config=proxy_config,
                totp_secret=totp_secret,
                auto_generate_totp=auto_generate_totp
            )
            
            logger.success("VRChat API客户端初始化完成")
            
        except Exception as e:
            logger.exception(f"初始化VRChat API客户端失败: {e}")
            raise
    
    async def _init_qq_bot(self):
        """初始化QQ Bot"""
        try:
            napcat_config = self.config.get('napcat', {})
            
            host = napcat_config.get('host', '127.0.0.1')
            port = napcat_config.get('port', 3000)
            access_token = napcat_config.get('access_token', '')
            webhook_url = napcat_config.get('webhook_url', '')
            
            self.qq_bot = AsyncQQBotManager(
                host=host,
                port=port,
                access_token=access_token,
                webhook_url=webhook_url
            )
            
            logger.success(f"QQ Bot初始化完成: {host}:{port}")
            
        except Exception as e:
            logger.exception(f"初始化QQ Bot失败: {e}")
            raise
    
    async def _init_data_manager(self):
        """初始化数据管理器"""
        try:
            db_config = self.config.get('database', {})
            app_config = self.config.get('app', {})
            
            data_file = db_config.get('file_path', './data/user_bindings.json')
            backup_enabled = db_config.get('backup_enabled', True)
            backup_interval = db_config.get('backup_interval', 86400)
            config_dir = app_config.get('config_dir', './data/config')
            
            self.data_manager = DataManager(
                data_file=data_file,
                backup_enabled=backup_enabled,
                backup_interval=backup_interval,
                config_dir=config_dir
            )
            
            logger.success("数据管理器初始化完成")
            
        except Exception as e:
            logger.exception(f"初始化数据管理器失败: {e}")
            raise
    
    async def _init_message_template(self):
        """初始化消息模板"""
        try:
            messages_config = self.config.get('messages', {})
            
            # 合并默认模板和用户配置
            templates = DEFAULT_TEMPLATES.copy()
            templates.update(messages_config)
            
            self.message_template = MessageTemplate(templates)
            
            logger.success("消息模板系统初始化完成")
            
        except Exception as e:
            logger.exception(f"初始化消息模板系统失败: {e}")
            raise
    
    async def _init_group_handler(self):
        """初始化群组处理器"""
        try:
            groups_config = self.config.get('groups', {}).get('managed_groups', [])
            
            self.group_handler = GroupHandler(
                qq_bot=self.qq_bot,
                vrc_api=self.vrc_api,
                data_manager=self.data_manager,
                message_template=self.message_template,
                groups_config=groups_config
            )
            
            # 注册事件处理器
            self.qq_bot.register_event_handler('request', self.group_handler.handle_group_request)
            self.qq_bot.register_event_handler('notice', self._handle_notice_event)
            self.qq_bot.register_event_handler('message', self.group_handler.handle_admin_command)
            
            logger.success("群组处理器初始化完成")
            
        except Exception as e:
            logger.exception(f"初始化群组处理器失败: {e}")
            raise
    
    async def _handle_notice_event(self, event_data: Dict):
        """处理通知事件"""
        try:
            sub_type = event_data.get('sub_type')
            
            if sub_type == 'group_increase':
                # 成员入群
                await self.group_handler.handle_group_increase(event_data)
            elif sub_type == 'group_decrease':
                # 成员退群
                await self.group_handler.handle_group_decrease(event_data)
                
        except Exception as e:
            logger.exception(f"处理通知事件时发生错误: {e}")
    
    async def authenticate_vrc(self):
        """认证VRChat API"""
        try:
            logger.info("开始VRChat API认证...")
            
            # 尝试认证
            success = await self.vrc_api.authenticate()
            
            if success:
                logger.success("VRChat API认证成功！")
            else:
                logger.warning("VRChat API认证失败，等待二步验证码...")
                
                # 检查是否需要二步验证
                vrc_config = self.config.get('vrchat', {})
                two_factor_config = vrc_config.get('two_factor', {})
                
                if two_factor_config.get('enabled', False):
                    # 尝试使用TOTP自动生成验证码
                    totp_secret = two_factor_config.get('totp_secret')
                    if totp_secret:
                        logger.info("尝试使用TOTP自动生成验证码...")
                        success = await self.vrc_api.authenticate()
                    else:
                        # 提示用户输入验证码
                        logger.info("请手动提供二步验证码")
                        # 这里可以实现等待用户输入的逻辑
                
                if not success:
                    raise RuntimeError("VRChat API认证失败，请检查配置或提供二步验证码")
            
        except Exception as e:
            logger.exception(f"VRChat API认证失败: {e}")
            raise
    
    async def start(self):
        """启动应用"""
        try:
            logger.info("应用启动中...")
            self.running = True
            
            # 设置信号处理器
            self._setup_signal_handlers()
            
            # 认证VRChat API
            await self.authenticate_vrc()
            
            # 检查QQ Bot连接
            login_info = await self.qq_bot.get_login_info()
            if login_info:
                logger.success(f"QQ Bot已连接: {login_info.get('nickname')} ({login_info.get('user_id')})")
            else:
                logger.warning("无法获取QQ Bot登录信息")
            
            # 显示统计信息
            stats = self.data_manager.get_statistics()
            logger.info(f"当前绑定数据: {stats.get('total_bindings', 0)} 条记录")
            
            # 启动事件循环
            logger.success("应用启动完成！正在运行...")
            
            # 保持运行
            while self.running:
                try:
                    await asyncio.sleep(1)
                    
                    # 定期任务可以在这里添加
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.exception(f"运行时错误: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            logger.exception(f"应用启动失败: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        try:
            # 注册信号处理器
            for sig in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(sig, self._signal_handler)
            
            logger.info("信号处理器设置完成")
            
        except Exception as e:
            logger.warning(f"设置信号处理器失败: {e}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，开始关闭应用...")
        self.stop()
    
    def stop(self):
        """停止应用"""
        try:
            logger.info("应用关闭中...")
            self.running = False
            
            # 关闭组件
            if self.vrc_api:
                asyncio.create_task(self.vrc_api.close())
                logger.info("VRChat API客户端已关闭")
            
            if self.qq_bot:
                asyncio.create_task(self.qq_bot.close())
                logger.info("QQ Bot已关闭")
            
            if self.data_manager:
                self.data_manager.close()
                logger.info("数据管理器已关闭")
            
            logger.success("应用已安全关闭")
            
        except Exception as e:
            logger.exception(f"关闭应用时发生错误: {e}")
    
    async def run_cli(self):
        """运行CLI版本（用于测试和调试）"""
        try:
            logger.info("启动CLI模式...")
            
            # 初始化
            await self.initialize()
            
            # 认证VRChat
            await self.authenticate_vrc()
            
            # 显示菜单
            await self._show_cli_menu()
            
        except Exception as e:
            logger.exception(f"CLI模式运行失败: {e}")
    
    async def _show_cli_menu(self):
        """显示CLI菜单"""
        while self.running:
            try:
                print("\n" + "="*50)
                print("QQ-VRC双向绑定机器人 - CLI模式")
                print("="*50)
                print("1. 查看统计信息")
                print("2. 手动绑定用户")
                print("3. 手动解绑用户")
                print("4. 搜索绑定记录")
                print("5. 测试VRChat API")
                print("6. 测试QQ Bot")
                print("7. 导出数据")
                print("0. 退出")
                print("="*50)
                
                choice = input("\n请选择操作: ").strip()
                
                if choice == '1':
                    await self._cli_show_stats()
                elif choice == '2':
                    await self._cli_bind_user()
                elif choice == '3':
                    await self._cli_unbind_user()
                elif choice == '4':
                    await self._cli_search_bindings()
                elif choice == '5':
                    await self._cli_test_vrc_api()
                elif choice == '6':
                    await self._cli_test_qq_bot()
                elif choice == '7':
                    await self._cli_export_data()
                elif choice == '0':
                    self.stop()
                    break
                else:
                    print("无效的选择")
                    
            except Exception as e:
                logger.exception(f"CLI菜单执行失败: {e}")
                await asyncio.sleep(1)
    
    async def _cli_show_stats(self):
        """CLI - 显示统计信息"""
        try:
            stats = self.data_manager.get_statistics()
            
            print("\n" + "="*30)
            print("统计信息")
            print("="*30)
            print(f"总绑定数: {stats.get('total_bindings', 0)}")
            print(f"创建时间: {stats.get('created_at', 'N/A')}")
            print(f"最后更新: {stats.get('last_updated', 'N/A')}")
            
            time_dist = stats.get('time_distribution', {})
            if time_dist:
                print("\n每日绑定统计:")
                for date, count in sorted(time_dist.items())[-7:]:  # 最近7天
                    print(f"  {date}: {count}")
            
        except Exception as e:
            logger.exception(f"显示统计信息失败: {e}")
    
    async def _cli_bind_user(self):
        """CLI - 手动绑定用户"""
        try:
            qq_id = input("请输入QQ号: ").strip()
            vrc_user_id = input("请输入VRChat用户ID: ").strip()
            
            if not qq_id.isdigit():
                print("QQ号必须是数字")
                return
            
            if not self.vrc_api.validate_user_id(vrc_user_id):
                print("VRChat用户ID格式不正确")
                return
            
            # 获取VRChat用户信息
            user_info = await self.vrc_api.get_user_info(vrc_user_id)
            if not user_info:
                print("未找到该VRChat用户")
                return
            
            vrc_username = user_info.get('displayName', vrc_user_id)
            
            # 绑定用户
            success = self.data_manager.bind_user(int(qq_id), vrc_user_id, vrc_username)
            
            if success:
                print(f"绑定成功: QQ {qq_id} -> VRC {vrc_username}")
            else:
                print("绑定失败")
                
        except Exception as e:
            logger.exception(f"手动绑定用户失败: {e}")
    
    async def _cli_unbind_user(self):
        """CLI - 手动解绑用户"""
        try:
            qq_id = input("请输入要解绑的QQ号: ").strip()
            
            if not qq_id.isdigit():
                print("QQ号必须是数字")
                return
            
            # 获取绑定信息
            binding = self.data_manager.get_binding_by_qq(int(qq_id))
            if not binding:
                print("该用户未绑定")
                return
            
            print(f"当前绑定: QQ {qq_id} -> VRC {binding['vrc_username']}")
            confirm = input("确认解绑吗? (y/n): ").strip().lower()
            
            if confirm == 'y':
                success = self.data_manager.unbind_user(int(qq_id))
                if success:
                    print("解绑成功")
                else:
                    print("解绑失败")
            else:
                print("已取消")
                
        except Exception as e:
            logger.exception(f"手动解绑用户失败: {e}")
    
    async def _cli_search_bindings(self):
        """CLI - 搜索绑定记录"""
        try:
            keyword = input("请输入搜索关键词: ").strip()
            
            results = self.data_manager.search_bindings(keyword)
            
            if not results:
                print("未找到匹配的记录")
                return
            
            print(f"\n找到 {len(results)} 条匹配记录:")
            print("-" * 50)
            
            for binding in results:
                print(f"QQ: {binding['qq_id']}")
                print(f"VRChat: {binding['vrc_username']}")
                print(f"VRChat ID: {binding['vrc_user_id']}")
                print(f"绑定时间: {binding['created_at']}")
                print("-" * 50)
                
        except Exception as e:
            logger.exception(f"搜索绑定记录失败: {e}")
    
    async def _cli_test_vrc_api(self):
        """CLI - 测试VRChat API"""
        try:
            print("\n测试VRChat API连接...")
            
            # 测试获取用户信息（使用示例ID）
            test_user_id = "usr_c1644b5b-3abb-44a8-b366-59f3bae8a1f5"  # VRChat官方账号
            user_info = await self.vrc_api.get_user_info(test_user_id)
            
            if user_info:
                print(f"✓ API连接正常")
                print(f"  测试用户: {user_info.get('displayName', 'Unknown')}")
            else:
                print("✗ API连接失败")
                
        except Exception as e:
            logger.exception(f"测试VRChat API失败: {e}")
    
    async def _cli_test_qq_bot(self):
        """CLI - 测试QQ Bot"""
        try:
            print("\n测试QQ Bot连接...")
            
            login_info = await self.qq_bot.get_login_info()
            
            if login_info:
                print(f"✓ QQ Bot连接正常")
                print(f"  账号: {login_info.get('nickname')} ({login_info.get('user_id')})")
            else:
                print("✗ QQ Bot连接失败")
                
        except Exception as e:
            logger.exception(f"测试QQ Bot失败: {e}")
    
    async def _cli_export_data(self):
        """CLI - 导出数据"""
        try:
            export_file = self.data_manager.export_data()
            
            if export_file:
                print(f"数据导出成功: {export_file}")
            else:
                print("数据导出失败")
                
        except Exception as e:
            logger.exception(f"导出数据失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取应用状态
        
        Returns:
            状态字典
        """
        status = {
            'running': self.running,
            'config_loaded': self.config is not None,
            'components': {
                'logger': self.logger_manager is not None,
                'vrc_api': self.vrc_api is not None,
                'qq_bot': self.qq_bot is not None,
                'data_manager': self.data_manager is not None,
                'message_template': self.message_template is not None,
                'group_handler': self.group_handler is not None
            },
            'statistics': {}
        }
        
        if self.data_manager:
            status['statistics'] = self.data_manager.get_statistics()
        
        return status
    
    async def run_cli_v2(self):
        """运行改进版CLI（交互式）"""
        try:
            logger.info("启动改进版CLI模式...")
            
            # 初始化CLI处理器
            cli_handler = CLIHandler(self)
            
            # 运行交互式模式
            await cli_handler.run_interactive_mode()
            
        except Exception as e:
            logger.exception(f"CLI模式运行失败: {e}")
            raise