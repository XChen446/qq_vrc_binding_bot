"""
CLI处理器
提供交互式的命令行界面
"""

import asyncio
import sys
from typing import Optional, Dict, Any
from loguru import logger
from datetime import datetime
from pathlib import Path


class CLIHandler:
    """CLI处理器"""
    
    def __init__(self, app):
        """
        初始化CLI处理器
        
        Args:
            app: 主应用实例
        """
        self.app = app
        self.running = True
        
    async def run_interactive_mode(self):
        """运行交互式模式"""
        try:
            logger.info("启动CLI交互式模式...")
            
            while self.running:
                try:
                    print("\n" + "="*60)
                    print("QQ-VRC双向绑定机器人 - 交互式命令模式")
                    print("="*60)
                    print("1. 认证和连接测试")
                    print("2. 查看统计信息")
                    print("3. 手动绑定用户")
                    print("4. 手动解绑用户")
                    print("5. 搜索绑定记录")
                    print("6. 测试VRChat API")
                    print("7. 测试QQ Bot")
                    print("8. 查看日志文件")
                    print("9. 数据管理")
                    print("10. 配置管理")
                    print("0. 退出")
                    print("="*60)
                    
                    choice = input("\n请选择操作: ").strip()
                    
                    if choice == '1':
                        await self._handle_authentication()
                    elif choice == '2':
                        await self._show_statistics()
                    elif choice == '3':
                        await self._handle_bind_user()
                    elif choice == '4':
                        await self._handle_unbind_user()
                    elif choice == '5':
                        await self._handle_search()
                    elif choice == '6':
                        await self._test_vrc_api()
                    elif choice == '7':
                        await self._test_qq_bot()
                    elif choice == '8':
                        await self._view_logs()
                    elif choice == '9':
                        await self._data_management()
                    elif choice == '10':
                        await self._config_management()
                    elif choice == '0':
                        self.running = False
                        break
                    else:
                        print("无效的选择，请重新输入")
                        
                except KeyboardInterrupt:
                    print("\n收到键盘中断")
                    self.running = False
                    break
                except Exception as e:
                    logger.exception(f"CLI菜单执行失败: {e}")
                    print(f"发生错误: {e}")
                    await asyncio.sleep(1)
            
            logger.info("CLI交互式模式已退出")
            
        except Exception as e:
            logger.exception(f"CLI交互式模式运行失败: {e}")
    
    async def _handle_authentication(self):
        """处理认证"""
        try:
            print("\n" + "="*40)
            print("认证和连接测试")
            print("="*40)
            
            # 检查当前认证状态
            if self.app.vrc_api.is_authenticated:
                print("✓ VRChat API已认证")
            else:
                print("✗ VRChat API未认证")
                print("\n认证选项:")
                print("1. 使用密码认证")
                print("2. 使用已保存的Cookie")
                print("3. 测试当前认证状态")
                print("0. 返回上级菜单")
                
                choice = input("\n请选择: ").strip()
                
                if choice == '1':
                    await self._interactive_authentication()
                elif choice == '2':
                    await self._cookie_authentication()
                elif choice == '3':
                    await self._test_current_auth()
            
        except Exception as e:
            logger.exception(f"处理认证失败: {e}")
            print(f"认证处理失败: {e}")
    
    async def _interactive_authentication(self):
        """交互式认证"""
        try:
            print("\n开始交互式认证...")
            
            # 尝试密码认证
            print("\n步骤1: 密码认证")
            success, msg = await self.app.vrc_api.authenticate(cli_mode=True)
            
            if success:
                print(f"✓ {msg}")
                return
            
            # 如果需要二步验证
            if "二步验证" in msg or "需要二步验证码" in msg:
                print(f"! {msg}")
                print("\n步骤2: 二步验证")
                
                # 检查是否有TOTP密钥
                if self.app.vrc_api.totp_secret:
                    print("检测到TOTP密钥配置")
                    if self.app.vrc_api.auto_generate_totp:
                        print("配置为自动生成TOTP验证码")
                        print("正在自动生成验证码...")
                        success, msg = await self.app.vrc_api.authenticate()
                        if success:
                            print(f"✓ {msg}")
                            return
                        else:
                            print(f"✗ TOTP自动生成失败: {msg}")
                    else:
                        print("配置为手动输入TOTP验证码")
                
                # 手动输入验证码
                print("\n请选择:")
                print("1. 输入TOTP验证码")
                print("2. 输入邮箱验证码")
                print("3. 返回上级菜单")
                
                choice = input("\n请选择: ").strip()
                
                if choice == '1':
                    totp_code = input("请输入TOTP验证码: ").strip()
                    if totp_code:
                        success, msg = await self.app.vrc_api.authenticate(two_factor_code=totp_code)
                        if success:
                            print(f"✓ {msg}")
                        else:
                            print(f"✗ 验证失败: {msg}")
                    else:
                        print("未输入验证码")
                
                elif choice == '2':
                    email_code = input("请输入邮箱验证码: ").strip()
                    if email_code:
                        success, msg = await self.app.vrc_api.authenticate(two_factor_code=email_code)
                        if success:
                            print(f"✓ {msg}")
                        else:
                            print(f"✗ 验证失败: {msg}")
                    else:
                        print("未输入验证码")
            
            else:
                print(f"✗ 认证失败: {msg}")
                
        except Exception as e:
            logger.exception(f"交互式认证失败: {e}")
            print(f"认证失败: {e}")
    
    async def _cookie_authentication(self):
        """使用Cookie认证"""
        try:
            print("\n尝试使用已保存的Cookie认证...")
            
            if self.app.vrc_api.cookie_file and self.app.vrc_api.cookie_file.exists():
                print(f"Cookie文件: {self.app.vrc_api.cookie_file}")
                
                # 重新加载Cookie
                self.app.vrc_api._load_saved_cookie()
                
                # 测试认证
                if await self.app.vrc_api._test_auth():
                    print("✓ Cookie认证成功！")
                    self.app.vrc_api.is_authenticated = True
                else:
                    print("✗ Cookie认证失败")
                    print("可能的原因:")
                    print("- Cookie已过期")
                    print("- Cookie文件格式错误")
                    print("- 需要重新进行密码认证")
            else:
                print("✗ 未找到Cookie文件")
                print(f"预期路径: {self.app.vrc_api.cookie_file}")
                
        except Exception as e:
            logger.exception(f"Cookie认证失败: {e}")
            print(f"Cookie认证失败: {e}")
    
    async def _test_current_auth(self):
        """测试当前认证状态"""
        try:
            print("\n测试认证状态...")
            
            if self.app.vrc_api.is_authenticated:
                print("✓ 当前已认证")
                
                # 测试API调用
                print("\n测试API调用...")
                test_user_id = "usr_c1644b5b-3abb-44a8-b366-59f3bae8a1f5"  # VRChat官方账号
                user_info = await self.app.vrc_api.get_user_info(test_user_id)
                
                if user_info:
                    print(f"✓ API调用成功")
                    print(f"  测试用户: {user_info.get('displayName', 'Unknown')}")
                else:
                    print("✗ API调用失败")
            else:
                print("✗ 当前未认证")
                
        except Exception as e:
            logger.exception(f"测试认证状态失败: {e}")
            print(f"测试失败: {e}")
    
    async def _show_statistics(self):
        """显示统计信息"""
        try:
            print("\n" + "="*40)
            print("统计信息")
            print("="*40)
            
            stats = self.app.data_manager.get_statistics()
            
            print(f"总绑定数: {stats.get('total_bindings', 0)}")
            print(f"创建时间: {stats.get('created_at', 'N/A')}")
            print(f"最后更新: {stats.get('last_updated', 'N/A')}")
            
            time_dist = stats.get('time_distribution', {})
            if time_dist:
                print("\n每日绑定统计 (最近7天):")
                for date, count in sorted(time_dist.items())[-7:]:
                    print(f"  {date}: {count}")
            
            # 显示认证状态
            print(f"\nVRChat API认证状态: {'已认证' if self.app.vrc_api.is_authenticated else '未认证'}")
            
            # 显示QQ Bot状态
            login_info = await self.app.qq_bot.get_login_info()
            if login_info:
                print(f"QQ Bot: {login_info.get('nickname')} ({login_info.get('user_id')})")
            else:
                print("QQ Bot: 未连接")
                
        except Exception as e:
            logger.exception(f"显示统计信息失败: {e}")
            print(f"获取统计信息失败: {e}")
    
    async def _handle_bind_user(self):
        """处理绑定用户"""
        try:
            print("\n手动绑定用户")
            print("="*40)
            
            qq_id = input("请输入QQ号: ").strip()
            vrc_user_id = input("请输入VRChat用户ID: ").strip()
            
            if not qq_id.isdigit():
                print("✗ QQ号必须是数字")
                return
            
            if not self.app.vrc_api.validate_user_id(vrc_user_id):
                print("✗ VRChat用户ID格式不正确")
                print("正确格式: usr_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
                return
            
            # 获取VRChat用户信息
            print("\n正在获取VRChat用户信息...")
            user_info = await self.app.vrc_api.get_user_info(vrc_user_id)
            
            if not user_info:
                print("✗ 未找到该VRChat用户")
                return
            
            vrc_username = user_info.get('displayName', vrc_user_id)
            print(f"找到用户: {vrc_username}")
            
            # 确认绑定
            confirm = input(f"\n确认绑定 QQ {qq_id} -> VRC {vrc_username} 吗? (y/n): ").strip().lower()
            
            if confirm == 'y':
                success = self.app.data_manager.bind_user(int(qq_id), vrc_user_id, vrc_username)
                
                if success:
                    print("✓ 绑定成功！")
                else:
                    print("✗ 绑定失败，用户可能已绑定")
            else:
                print("已取消绑定")
                
        except Exception as e:
            logger.exception(f"绑定用户失败: {e}")
            print(f"绑定失败: {e}")
    
    async def _handle_unbind_user(self):
        """处理解绑用户"""
        try:
            print("\n手动解绑用户")
            print("="*40)
            
            qq_id = input("请输入要解绑的QQ号: ").strip()
            
            if not qq_id.isdigit():
                print("✗ QQ号必须是数字")
                return
            
            # 获取绑定信息
            binding = self.app.data_manager.get_binding_by_qq(int(qq_id))
            if not binding:
                print("✗ 该用户未绑定")
                return
            
            print(f"当前绑定:")
            print(f"  QQ: {binding['qq_id']}")
            print(f"  VRChat: {binding['vrc_username']}")
            print(f"  VRChat ID: {binding['vrc_user_id']}")
            print(f"  绑定时间: {binding['created_at']}")
            
            confirm = input("\n确认解绑吗? (y/n): ").strip().lower()
            
            if confirm == 'y':
                success = self.app.data_manager.unbind_user(int(qq_id))
                
                if success:
                    print("✓ 解绑成功！")
                else:
                    print("✗ 解绑失败")
            else:
                print("已取消解绑")
                
        except Exception as e:
            logger.exception(f"解绑用户失败: {e}")
            print(f"解绑失败: {e}")
    
    async def _handle_search(self):
        """处理搜索"""
        try:
            print("\n搜索绑定记录")
            print("="*40)
            
            keyword = input("请输入搜索关键词 (QQ号或VRChat用户名): ").strip()
            
            if not keyword:
                print("未输入关键词")
                return
            
            results = self.app.data_manager.search_bindings(keyword)
            
            if not results:
                print("✗ 未找到匹配的记录")
                return
            
            print(f"\n找到 {len(results)} 条匹配记录:")
            print("-" * 60)
            
            for i, binding in enumerate(results, 1):
                print(f"{i}. QQ: {binding['qq_id']}")
                print(f"   VRChat: {binding['vrc_username']}")
                print(f"   VRChat ID: {binding['vrc_user_id']}")
                print(f"   绑定时间: {binding['created_at']}")
                print("-" * 60)
                
        except Exception as e:
            logger.exception(f"搜索失败: {e}")
            print(f"搜索失败: {e}")
    
    async def _test_vrc_api(self):
        """测试VRChat API"""
        try:
            print("\n测试VRChat API...")
            
            if not self.app.vrc_api.is_authenticated:
                print("✗ VRChat API未认证，请先认证")
                return
            
            test_user_id = "usr_c1644b5b-3abb-44a8-b366-59f3bae8a1f5"  # VRChat官方账号
            print(f"测试用户ID: {test_user_id}")
            
            user_info = await self.app.vrc_api.get_user_info(test_user_id)
            
            if user_info:
                print("✓ API测试成功")
                print(f"  用户名: {user_info.get('displayName', 'Unknown')}")
                print(f"  状态: {user_info.get('state', 'Unknown')}")
                print(f"  标签: {user_info.get('tags', [])}")
            else:
                print("✗ API测试失败")
                
        except Exception as e:
            logger.exception(f"API测试失败: {e}")
            print(f"API测试失败: {e}")
    
    async def _test_qq_bot(self):
        """测试QQ Bot"""
        try:
            print("\n测试QQ Bot连接...")
            
            login_info = await self.app.qq_bot.get_login_info()
            
            if login_info:
                print("✓ QQ Bot连接成功")
                print(f"  昵称: {login_info.get('nickname')}")
                print(f"  QQ号: {login_info.get('user_id')}")
            else:
                print("✗ QQ Bot连接失败")
                print("可能的原因:")
                print("- Napcat未运行")
                print("- 配置错误（主机、端口）")
                print("- 网络连接问题")
                
        except Exception as e:
            logger.exception(f"QQ Bot测试失败: {e}")
            print(f"QQ Bot测试失败: {e}")
    
    async def _view_logs(self):
        """查看日志"""
        try:
            print("\n日志查看")
            print("="*40)
            
            log_files = {
                '1': ('应用日志', 'logs/app.log'),
                '2': ('错误日志', 'logs/error.log'),
                '3': ('HTTP日志', 'logs/http.log'),
                '4': ('VRChat API日志', 'logs/vrchat_api.log'),
                '5': ('QQ Bot日志', 'logs/qq_bot.log'),
                '0': ('返回上级', None)
            }
            
            for key, (name, path) in log_files.items():
                if key != '0':
                    print(f"{key}. {name} ({path})")
                else:
                    print(f"{key}. {name}")
            
            choice = input("\n请选择要查看的日志: ").strip()
            
            if choice == '0':
                return
            
            if choice in log_files:
                name, path = log_files[choice]
                if path:
                    print(f"\n查看 {name}:")
                    print("-" * 40)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            # 显示最后20行
                            for line in lines[-20:]:
                                print(line.rstrip())
                    except FileNotFoundError:
                        print(f"日志文件不存在: {path}")
                    except Exception as e:
                        print(f"读取日志失败: {e}")
                        
        except Exception as e:
            logger.exception(f"查看日志失败: {e}")
            print(f"查看日志失败: {e}")
    
    async def _data_management(self):
        """数据管理"""
        try:
            print("\n数据管理")
            print("="*40)
            print("1. 导出数据")
            print("2. 导入数据")
            print("3. 查看备份")
            print("4. 清理旧备份")
            print("0. 返回上级")
            
            choice = input("\n请选择: ").strip()
            
            if choice == '1':
                export_file = self.app.data_manager.export_data()
                if export_file:
                    print(f"✓ 数据导出成功: {export_file}")
                else:
                    print("✗ 数据导出失败")
            
            elif choice == '2':
                print("导入数据功能待实现")
            
            elif choice == '3':
                import os
                backup_dir = Path(self.app.data_manager.data_file).parent / 'backups'
                if backup_dir.exists():
                    print(f"\n备份文件列表 ({backup_dir}):")
                    for backup_file in sorted(backup_dir.glob('backup_*.json')):
                        print(f"  {backup_file.name}")
                else:
                    print("✗ 备份目录不存在")
            
            elif choice == '4':
                days = input("删除多少天前的备份? (默认30): ").strip()
                days = int(days) if days.isdigit() else 30
                print(f"清理 {days} 天前的备份...")
                # 这里可以添加清理逻辑
                print("清理功能待实现")
                
        except Exception as e:
            logger.exception(f"数据管理失败: {e}")
            print(f"数据管理失败: {e}")
    
    async def _config_management(self):
        """配置管理"""
        try:
            print("\n配置管理")
            print("="*40)
            print("1. 查看当前配置")
            print("2. 重新加载配置")
            print("3. 导出配置模板")
            print("4. 测试配置文件")
            print("0. 返回上级")
            
            choice = input("\n请选择: ").strip()
            
            if choice == '1':
                print("\n当前配置:")
                print("-" * 40)
                if self.app.config:
                    import yaml
                    print(yaml.dump(self.app.config, default_flow_style=False, allow_unicode=True))
                else:
                    print("配置未加载")
            
            elif choice == '2':
                try:
                    await self.app._load_config()
                    print("✓ 配置重新加载成功")
                except Exception as e:
                    print(f"✗ 配置重新加载失败: {e}")
            
            elif choice == '3':
                try:
                    from src.utils.config_loader import ConfigLoader
                    config_loader = ConfigLoader(self.app.config_file)
                    template = config_loader.export_template()
                    
                    output_file = f"config_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(template)
                    
                    print(f"✓ 配置模板已导出: {output_file}")
                except Exception as e:
                    print(f"✗ 导出配置模板失败: {e}")
            
            elif choice == '4':
                try:
                    import yaml
                    with open(self.app.config_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    print("✓ 配置文件格式正确")
                except Exception as e:
                    print(f"✗ 配置文件格式错误: {e}")
                
        except Exception as e:
            logger.exception(f"配置管理失败: {e}")
            print(f"配置管理失败: {e}")


# 辅助函数
async def prompt_for_totp(prompt: str = "请输入二步验证码: ") -> str:
    """提示用户输入TOTP验证码"""
    import sys
    import tty
    import termios
    
    print(prompt, end="", flush=True)
    
    # 保存当前终端设置
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    
    try:
        # 设置终端为原始模式
        tty.setraw(sys.stdin.fileno())
        
        code = ""
        while True:
            char = sys.stdin.read(1)
            if char == '\r' or char == '\n':  # 回车
                print()
                break
            elif char == '\x03':  # Ctrl+C
                print("\n取消输入")
                return ""
            elif char == '\x7f':  # 退格
                if code:
                    code = code[:-1]
                    print('\b \b', end="", flush=True)
            else:
                code += char
                print('*', end="", flush=True)  # 显示星号
        
        return code
        
    finally:
        # 恢复终端设置
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)