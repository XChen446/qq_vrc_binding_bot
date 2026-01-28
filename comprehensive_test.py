#!/usr/bin/env python
"""
VRChat-QQ机器人项目综合测试
包括导入测试、逻辑测试、功能测试等
"""

import asyncio
import sys
import os
import time as time_module  # 避免变量名冲突
import logging

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 设置环境变量，以便模块导入时能找到配置文件
os.environ.setdefault('CONFIG_PATH', os.path.join(project_root, 'config/config.json'))

def setup_logging():
    """设置测试日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

async def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("1. 模块导入测试")
    print("=" * 60)
    
    tests = [
        ("Core Modules", [
            ("src.core.global_config", "GlobalConfig"),
            ("src.core.bot_manager", "BotManager"),
            ("src.core.event_router", "EventRouter"),
            ("src.core.scheduler", "Scheduler"),
        ]),
        ("Database Modules", [
            ("src.core.database.base", "BaseDatabase"),
            ("src.core.database.sqlite_db", "SQLiteDatabase"),
            ("src.core.database.utils", "safe_db_operation"),
        ]),
        ("API Modules", [
            ("src.api.qq.websocket", "QQWebSocketManager"),
            ("src.api.qq.client", "QQClient"),
            ("src.api.vrc.client", "VRCApiClient"),
            ("src.api.vrc.auth", "VRCAuth"),
        ]),
        ("Handler Modules", [
            ("src.handlers.qq_handler.message_handler", "MessageHandler"),
            ("src.handlers.qq_handler.group_handler", "GroupHandler"),
            ("src.handlers.vrc_handler.world_handler", "WorldHandler"),
        ]),
        ("Utility Modules", [
            ("src.utils.logger", "setup_logger"),
            ("src.utils.admin_utils", "is_super_admin"),
            ("src.utils.verification", "calculate_verification_elapsed"),
            ("src.utils.code_generator", "generate_verification_code"),
            ("src.utils.image_generator", "generate_binding_list_image"),
        ])
    ]
    
    all_passed = True
    for category, module_tests in tests:
        print(f"\n{category}:")
        for module_path, class_name in module_tests:
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                print(f"  ✅ {module_path}.{class_name}")
            except Exception as e:
                print(f"  ❌ {module_path}.{class_name} - {e}")
                all_passed = False
    
    return all_passed

async def test_basic_logic():
    """测试基本逻辑功能"""
    print("\n" + "=" * 60)
    print("2. 基本逻辑测试")
    print("=" * 60)
    
    # 测试配置加载
    print("\n2.1 配置加载测试:")
    try:
        from src.core.global_config import load_all_config
        config_path = os.path.join(project_root, "config", "config.json")
        config = load_all_config(config_path)
        if config:
            print("  ✅ 配置加载成功")
            print(f"     - 日志级别: {config.get('bot', {}).get('log_level', 'NOT SET')}")
            print(f"     - 数据库类型: {config.get('database', {}).get('type', 'NOT SET')}")
        else:
            print("  ⚠️ 配置加载失败或使用默认配置")
    except Exception as e:
        print(f"  ❌ 配置加载失败: {e}")
        return False  # 如果配置加载失败，整个基本逻辑测试失败
    
    # 测试验证码生成
    print("\n2.2 验证码生成测试:")
    try:
        from src.utils.code_generator import generate_verification_code
        codes = [generate_verification_code() for _ in range(3)]
        print(f"  ✅ 生成验证码: {codes}")
        # 验证格式
        all_numeric = all(code.isdigit() and len(code) == 6 for code in codes)
        if all_numeric:
            print("  ✅ 验证码格式正确")
        else:
            print("  ❌ 验证码格式错误")
    except Exception as e:
        print(f"  ❌ 验证码生成失败: {e}")
    
    # 测试管理员权限检查
    print("\n2.3 管理员权限检查测试:")
    try:
        from src.utils.admin_utils import is_super_admin
        test_qq = 123456789
        super_admins = [123456789, 987654321]
        result = is_super_admin(test_qq, super_admins)
        print(f"  ✅ 管理员检查: QQ {test_qq} 在管理员列表中: {result}")
    except Exception as e:
        print(f"  ❌ 管理员检查失败: {e}")
    
    # 测试验证时间计算
    print("\n2.4 验证时间计算测试:")
    try:
        from src.utils.verification import calculate_verification_elapsed
        import time
        fake_verification = {"created_at": time.time() - 100}  # 100秒前
        elapsed = calculate_verification_elapsed(fake_verification)
        print(f"  ✅ 验证时间计算: {elapsed:.2f}秒")
    except Exception as e:
        print(f"  ❌ 验证时间计算失败: {e}")
    
    return True

async def test_database_operations():
    """测试数据库操作"""
    print("\n" + "=" * 60)
    print("3. 数据库操作测试")
    print("=" * 60)
    
    try:
        from src.core.database import get_database
        from src.core.global_config import load_all_config
        
        config_path = os.path.join(project_root, "config", "config.json")
        config = load_all_config(config_path)
        if not config:
            print("  ⚠️ 无法加载配置，使用默认配置")
            config = {
                "database": {
                    "type": "sqlite",
                    "path": "data/test_bot.db"
                }
            }
        
        db = get_database(config)
        print(f"  ✅ 数据库连接成功: {type(db).__name__}")
        
        # 测试基本操作（不实际执行，仅测试方法存在性）
        methods_to_test = [
            "bind_user", "get_binding", "get_group_bindings", 
            "get_verification", "add_verification", "delete_verification",
            "get_group_vrc_group_id", "set_group_vrc_group_id"
        ]
        
        missing_methods = []
        for method in methods_to_test:
            if hasattr(db, method):
                print(f"     - {method}: ✅")
            else:
                print(f"     - {method}: ❌")
                missing_methods.append(method)
        
        if missing_methods:
            print(f"  ⚠️ 以下方法缺失: {missing_methods}")
        
        return True
    except Exception as e:
        print(f"  ❌ 数据库测试失败: {e}")
        return False

async def test_vrc_api():
    """测试VRChat API功能"""
    print("\n" + "=" * 60)
    print("4. VRChat API测试")
    print("=" * 60)
    
    try:
        from src.api.vrc.client import VRCApiClient
        from src.api.vrc.auth import VRCAuth
        from src.core.global_config import load_all_config
        from vrchatapi.configuration import Configuration
        
        config_path = os.path.join(project_root, "config", "config.json")
        config = load_all_config(config_path)
        if not config:
            print("  ⚠️ 无法加载配置，使用默认配置")
            config = {
                "vrchat": {
                    "username": "",
                    "password": "",
                    "proxy": ""
                }
            }
        
        # 创建VRChat配置对象
        vrc_data = config.get("vrchat", {})
        username = vrc_data.get("username", "")
        password = vrc_data.get("password", "")
        
        # 创建vrchatapi配置对象
        api_config = Configuration(
            username=username,
            password=password
        )
        
        # 设置代理（如果有）
        if "proxy" in vrc_data and vrc_data["proxy"]:
            api_config.proxy = vrc_data["proxy"]
        
        # 创建客户端实例，绕过认证初始化问题
        client = VRCApiClient(type('SimpleConfig', (), {
            'username': username,
            'password': password,
            'proxy': vrc_data.get("proxy", ""),
            'totp_secret': vrc_data.get("totp_secret", "")
        })())
        
        print("  ✅ VRChat客户端创建成功")
        
        # 检查主要方法
        methods_to_test = [
            "get_user", "search_users", "get_group_member", 
            "add_group_role", "get_group_instances", "get_group"
        ]
        
        for method in methods_to_test:
            if hasattr(client, method):
                print(f"     - {method}: ✅")
            else:
                print(f"     - {method}: ❌")
        
        # 测试认证实例
        if hasattr(client, 'auth'):
            print("  ✅ 认证实例存在")
            auth_methods = ["login", "verify_auth"]
            for method in auth_methods:
                if hasattr(client.auth, method):
                    print(f"     - auth.{method}: ✅")
                else:
                    print(f"     - auth.{method}: ❌")
        else:
            print("  ❌ 认证实例不存在")
        
        return True
    except Exception as e:
        print(f"  ❌ VRChat API测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_message_handling():
    """测试消息处理逻辑"""
    print("\n" + "=" * 60)
    print("5. 消息处理逻辑测试")
    print("=" * 60)
    
    try:
        from src.handlers.qq_handler.message_handler import MessageHandler
        from src.core.global_config import load_all_config
        from src.utils.admin_utils import is_super_admin, is_group_admin_or_owner
        
        config_path = os.path.join(project_root, "config", "config.json")
        config = load_all_config(config_path)
        if not config:
            print("  ⚠️ 无法加载配置，使用默认配置")
            config = {
                "bot": {
                    "commands": {
                        "instances": {"enabled": True},
                        "code": {"enabled": True},
                        "verify": {"enabled": True},
                        "bind": {"enabled": True},
                        "unbind": {"enabled": True},
                        "list": {"enabled": True},
                        "unbound": {"enabled": True},
                        "search": {"enabled": True},
                        "query": {"enabled": True},
                        "me": {"enabled": True}
                    },
                    "admin_qq": []
                }
            }
        
        # 创建一个模拟的bot对象
        class MockBot:
            def __init__(self, config):
                self.config_data = config
                self.global_config = type('GlobalConfig', (), {
                    'commands': config.get('bot', {}).get('commands', {}),
                    'admin_qq': config.get('bot', {}).get('admin_qq', []),
                    'group_admins': {}  # 现在使用实时API获取角色信息
                })()
                self.vrc_config = type('VRCConfig', (), {
                    'verification': {'code_expiry': 300}
                })()
                
                # 模拟数据库
                class MockDB:
                    def get_binding(self, qq_id): return None
                    def get_verification(self, qq_id): return None
                    def get_pending_vrc_info(self, qq_id): return None
                    def get_group_vrc_group_id(self, group_id): return None
                    def get_group_bindings(self, group_id): return []
                
                self.db = MockDB()
                
                # 模拟QQ客户端
                class MockQQClient:
                    async def get_group_member_info(self, group_id, user_id):
                        # 模拟返回用户角色信息
                        return {"role": "member", "card": f"User_{user_id}", "nickname": f"Nickname_{user_id}"}
                    async def get_group_member_list(self, group_id): return []
                    async def get_stranger_info(self, user_id): return {"nickname": f"User_{user_id}"}
                    async def send_group_msg(self, group_id, message): pass
                    async def send_private_msg(self, user_id, message): pass
                    async def set_group_card(self, group_id, user_id, card): pass
                
                self.qq_client = MockQQClient()
        
        mock_bot = MockBot(config)
        handler = MessageHandler(mock_bot)
        print("  ✅ 消息处理器创建成功")
        
        # 测试命令配置获取
        cmd_config = handler._get_command_config("bind")
        print(f"  ✅ 命令配置获取: {bool(cmd_config)}")
        
        # 测试命令启用检查
        is_enabled = handler._is_command_enabled("bind")
        print(f"  ✅ 命令启用检查: bind命令启用状态 = {is_enabled}")
        
        # 测试冷却时间检查
        is_cooled = handler._check_cooldown("bind", 123456)
        print(f"  ✅ 冷却时间检查: {is_cooled}")
        
        # 测试消息处理（使用模拟数据）
        mock_message_data = {
            "user_id": 123456,
            "group_id": 654321,
            "raw_message": "!help"
        }
        
        try:
            await handler.handle_message(mock_message_data)
            print("  ✅ 消息处理调用成功")
        except Exception as e:
            print(f"  ⚠️ 消息处理调用出现预期外错误: {e}")
        
        return True
    except Exception as e:
        print(f"  ❌ 消息处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_message_config():
    """测试消息配置功能"""
    print("\n" + "=" * 60)
    print("6. 消息配置功能测试")
    print("=" * 60)
    
    try:
        from src.core.message_config import MessageConfig
        
        # 创建消息配置实例
        msg_config = MessageConfig()
        print("  ✅ 消息配置加载成功")
        
        # 测试获取不同类型的消息
        error_msg = msg_config.get_message('errors', 'group_only')
        if error_msg:
            print(f"  ✅ 错误消息获取: {error_msg}")
        else:
            print("  ❌ 错误消息获取失败")
        
        success_msg = msg_config.get_message('success', 'verification_success', default="验证成功！")
        if success_msg:
            print(f"  ✅ 成功消息获取: {success_msg}")
        else:
            print("  ❌ 成功消息获取失败")
        
        # 测试消息格式化
        formatted_msg = msg_config.format_message('success', 'verification_code_generated', 
                                               code='123456', 
                                               remaining=300, 
                                               vrc_name='TestUser')
        if formatted_msg:
            print(f"  ✅ 消息格式化: {formatted_msg[:50]}...")
        else:
            print("  ❌ 消息格式化失败")
        
        # 测试不存在的消息
        missing_msg = msg_config.get_message('nonexistent', 'key')
        print(f"  ✅ 缺失消息处理: '{missing_msg}'")
        
        return True
    except Exception as e:
        print(f"  ❌ 消息配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_performance():
    """测试性能和并发处理能力"""
    print("\n" + "=" * 60)
    print("6. 性能和并发测试")
    print("=" * 60)
    
    start_time = time_module.time()
    
    # 测试大量验证码生成的性能
    print("\n6.1 验证码生成性能测试:")
    try:
        from src.utils.code_generator import generate_verification_code
        import time
        
        start_gen = time_module.time()
        codes = [generate_verification_code() for _ in range(100)]
        end_gen = time_module.time()
        
        print(f"  ✅ 生成100个验证码耗时: {end_gen - start_gen:.4f}秒")
        print(f"  ✅ 平均每个验证码: {(end_gen - start_gen)/100*1000:.4f}毫秒")
        
        # 检查唯一性
        unique_codes = len(set(codes))
        print(f"  ✅ 唯一验证码数量: {unique_codes}/100")
        
    except Exception as e:
        print(f"  ❌ 性能测试失败: {e}")
    
    # 测试异步并发处理
    print("\n6.2 异步并发处理测试:")
    try:
        async def mock_api_call(n):
            await asyncio.sleep(0.01)  # 模拟API调用延迟
            return f"Result_{n}"
        
        start_concurrent = time_module.time()
        tasks = [mock_api_call(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        end_concurrent = time_module.time()
        
        print(f"  ✅ 并发执行10个任务耗时: {end_concurrent - start_concurrent:.4f}秒")
        print(f"  ✅ 任务结果示例: {results[:3]}...")
        
    except Exception as e:
        print(f"  ❌ 并发测试失败: {e}")
    
    total_time = time_module.time() - start_time
    print(f"\n总性能测试耗时: {total_time:.4f}秒")
    
    return True

async def run_comprehensive_test():
    """运行综合测试"""
    print("VRChat-QQ机器人项目综合测试")
    print("=" * 60)
    
    setup_logging()
    
    results = {}
    
    # 运行各项测试
    results['imports'] = await test_imports()
    results['basic_logic'] = await test_basic_logic()
    results['database'] = await test_database_operations()
    results['vrc_api'] = await test_vrc_api()
    results['message_handling'] = await test_message_handling()
    results['message_config'] = await test_message_config()
    results['performance'] = await test_performance()
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed_count = sum(1 for result in results.values() if result is True)
    total_count = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n总体结果: {passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("🎉 所有测试通过！项目基本功能正常。")
    else:
        print(f"⚠️  {total_count - passed_count} 个测试失败，请检查相关模块。")
    
    return passed_count == total_count

if __name__ == "__main__":
    success = asyncio.run(run_comprehensive_test())
    sys.exit(0 if success else 1)