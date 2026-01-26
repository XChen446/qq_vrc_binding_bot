import os
import json
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from core.global_config import ConfigLoader

CONFIG_PATH = os.path.join(project_root, "config", "config.json")

class Console:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    BG_BLUE = "\033[44m"
    
    @classmethod
    def print_header(cls, text):
        print(f"\n{cls.BG_BLUE}{cls.WHITE}{cls.BOLD} {text} {cls.RESET}\n")
        
    @classmethod
    def print_step(cls, step, total, text):
        print(f"{cls.BOLD}{cls.MAGENTA}[{step}/{total}]{cls.RESET} {cls.BOLD}{text}{cls.RESET}")
        
    @classmethod
    def print_success(cls, text):
        print(f" {cls.GREEN}✔{cls.RESET} {text}")
        
    @classmethod
    def print_info(cls, text):
        print(f" {cls.BLUE}ℹ{cls.RESET} {text}")
        
    @classmethod
    def print_warn(cls, text):
        print(f" {cls.YELLOW}⚠{cls.RESET} {text}")
        
    @classmethod
    def print_error(cls, text):
        print(f" {cls.RED}✖{cls.RESET} {text}")

    @classmethod
    def ask(cls, prompt, default_val=""):
        default_str = ""
        if default_val:
            default_str = f" {cls.DIM}({default_val}){cls.RESET}"
            
        prompt_formatted = f" {cls.GREEN}?{cls.RESET} {prompt}{default_str} {cls.DIM}›{cls.RESET} "
        
        try:
            user_input = input(prompt_formatted).strip()
            return user_input if user_input else default_val
        except EOFError:
            return default_val

    @classmethod
    def ask_bool(cls, prompt, default_val=True):
        default_char = "Y" if default_val else "N"
        choices_str = f" {cls.DIM}(Y/n){cls.RESET}" if default_val else f" {cls.DIM}(y/N){cls.RESET}"
        
        prompt_formatted = f" {cls.GREEN}?{cls.RESET} {prompt}{choices_str} {cls.DIM}›{cls.RESET} "
        
        while True:
            user_input = input(prompt_formatted).strip().lower()
            if not user_input:
                return default_val
            if user_input in ("y", "yes", "true", "1"):
                return True
            if user_input in ("n", "no", "false", "0"):
                return False

    @classmethod
    def ask_list(cls, prompt, default_val=[]):
        default_str = ""
        if default_val:
            val_str = ",".join(map(str, default_val))
            default_str = f" {cls.DIM}({val_str}){cls.RESET}"
            
        prompt_formatted = f" {cls.GREEN}?{cls.RESET} {prompt} {cls.DIM}(逗号分隔){cls.RESET}{default_str} {cls.DIM}›{cls.RESET} "
        
        user_input = input(prompt_formatted).strip()
        
        if not user_input:
            return default_val
            
        parts = [x.strip() for x in user_input.split(",") if x.strip()]
        try:
            return [int(x) for x in parts]
        except ValueError:
            return parts
            
    @classmethod
    def ask_choice(cls, prompt, choices, default_val=None):
        if default_val not in choices:
            default_val = choices[0]
            
        choices_display = []
        for c in choices:
            if c == default_val:
                choices_display.append(f"{cls.CYAN}{c}{cls.RESET}")
            else:
                choices_display.append(c)
        choices_str = f" {cls.DIM}({'/'.join(choices_display)}){cls.RESET}"
        
        prompt_formatted = f" {cls.GREEN}?{cls.RESET} {prompt}{choices_str} {cls.DIM}›{cls.RESET} "
        
        while True:
            val = input(prompt_formatted).strip()
            if not val:
                return default_val
            val_lower = val.lower()
            choices_lower = [c.lower() for c in choices]
            if val_lower in choices_lower:
                idx = choices_lower.index(val_lower)
                return choices[idx]

def main():

    if os.name == 'nt':
        os.system('color')  # Windows 下启用 ANSI 颜色支持
        
    Console.print_header("VRChat QQ 绑定机器人 - 配置向导")
    print(f" {Console.DIM}配置文件: {CONFIG_PATH}{Console.RESET}\n")

    # 1. 加载或初始化配置模板
    if os.path.exists(CONFIG_PATH):
        Console.print_info("发现现有配置文件，将基于现有配置进行修改...")
        config = ConfigLoader.load_config(CONFIG_PATH)
    else:
        Console.print_info("未找到配置文件，将创建新配置...")
        # 默认配置模板
        config = {
            "bot": {
                "log_level": "INFO",
                "admin_qq": [],
                "group_whitelist": [],
                "enable_welcome": True,
                "templates": {
                    "welcome": "欢迎加入！请查看群公告。",
                    "verify_success": "验证成功！",
                    "reject_no_user": "无法识别 VRChat 账号，请在验证消息中填写 VRChat 链接或 ID",
                    "reject_already_bound": "该 VRChat 账号已被 QQ {existing_qq} 绑定",
                    "reject_no_group": "您未加入指定的 VRChat 群组，请先加群",
                    "reject_troll": "系统检测到您的账号存在风险，拒绝入群",
                    "verification_request": "[CQ:at,qq={user_id}] 欢迎加入！\n检测到您申请绑定的 VRChat 账号为: {vrc_name}\n为了验证身份，请将您的 VRChat 状态描述(Status Description)修改为以下数字：\n{code}\n修改完成后，请在群内发送 !verify 完成验证。",
                    "reminder_not_bound": "欢迎！请绑定 VRChat 账号。"
                },
                "commands": {
                    "query": { "enabled": True, "admin_only": True, "max_results": 50 },
                    "bind": { "enabled": True, "admin_only": True },
                    "unbind": { "enabled": True, "admin_only": True },
                    "list": { "enabled": True, "admin_only": True },
                    "search": { "enabled": True, "admin_only": True },
                    "instances": { "enabled": True, "admin_only": False, "cooldown": 60 },
                    "me": { "enabled": True, "admin_only": False },
                    "code": { "enabled": True, "admin_only": False }
                },
                "features": {
                    "auto_approve_group_request": False,
                    "auto_bind_on_join": True
                },
                "verification": {
                    "mode": "mixed",
                    "group_id": "",
                    "timeout": 300,
                    "code_expiry": 300,
                    "auto_rename": True,
                    "check_occupy": True,
                    "check_group_membership": False,
                    "check_troll": False,
                    "auto_assign_role": False,
                    "target_role_id": ""
                }
            },
            "database": {
                "type": "sqlite",
                "path": "data/bot.db"
            },
            "napcat": {
                "ws_url": "ws://127.0.0.1:3001",
                "token": "",
                "ws_max_retries": 10,
                "ws_initial_delay": 5.0,
                "ws_max_delay": 60.0
            },
            "vrchat": {
                "username": "",
                "password": "",
                "totp_secret": "",
                "user_agent": "VRCQQBot/2.0",
                "proxy": ""
            }
        }

    try:
        # 2. 交互式配置各个模块
        
        # [Step 1] VRChat 账号配置
        Console.print_step(1, 5, "VRChat 账号配置")
        vrc = config.setdefault("vrchat", {})
        vrc["username"] = Console.ask("VRChat 用户名/邮箱", vrc.get("username", ""))
        vrc["password"] = Console.ask("VRChat 密码", vrc.get("password", ""))
        vrc["totp_secret"] = Console.ask("2FA 密钥 (选填，留空则手动输入验证码)", vrc.get("totp_secret", ""))
        vrc["proxy"] = Console.ask("HTTP 代理 (选填，如 http://127.0.0.1:7890)", vrc.get("proxy", ""))

        # [Step 2] NapCat (QQ 机器人后端) 配置
        Console.print_step(2, 5, "NapCat (OneBot) 配置")
        napcat = config.setdefault("napcat", {})
        napcat["ws_url"] = Console.ask("WebSocket 地址", napcat.get("ws_url", "ws://127.0.0.1:3001"))
        napcat["token"] = Console.ask("Access Token (选填)", napcat.get("token", ""))

        # [Step 3] 机器人基础功能配置
        Console.print_step(3, 5, "机器人基础配置")
        bot = config.setdefault("bot", {})
        bot["log_level"] = Console.ask_choice("日志等级", ["INFO", "DEBUG", "WARNING", "ERROR"], bot.get("log_level", "INFO"))
        
        # 日志归档配置
        bot["log_retention_days"] = int(Console.ask("日志保留天数", str(bot.get("log_retention_days", 30))))
        
        print(f" {Console.DIM}日志归档策略:{Console.RESET}")
        print(f" {Console.DIM} - standard:   标准模式 (全部归档){Console.RESET}")
        print(f" {Console.DIM} - save-space: 节省空间 (无错删除，有错归档){Console.RESET}")
        print(f" {Console.DIM} - debug:      调试模式 (有错保留文件，无错归档){Console.RESET}")
        print(f" {Console.DIM} - error-only: 仅保留错误 (无错删除，有错保留文件){Console.RESET}")
        
        # 尝试从现有配置推断当前策略模式
        current_policy = bot.get("log_archive_policy", {})
        default_policy_mode = "standard"
        if current_policy.get("on_error") == "archive" and current_policy.get("on_success") == "delete":
            default_policy_mode = "save-space"
        elif current_policy.get("on_error") == "keep" and current_policy.get("on_success") == "archive":
            default_policy_mode = "debug"
        elif current_policy.get("on_error") == "keep" and current_policy.get("on_success") == "delete":
            default_policy_mode = "error-only"
            
        policy_choice = Console.ask_choice("日志归档策略", ["standard", "save-space", "debug", "error-only"], default_policy_mode)
        
        if policy_choice == "standard":
            bot["log_archive_policy"] = {"on_error": "archive", "on_success": "archive"}
        elif policy_choice == "save-space":
            bot["log_archive_policy"] = {"on_error": "archive", "on_success": "delete"}
        elif policy_choice == "debug":
            bot["log_archive_policy"] = {"on_error": "keep", "on_success": "archive"}
        elif policy_choice == "error-only":
            bot["log_archive_policy"] = {"on_error": "keep", "on_success": "delete"}

        bot["admin_qq"] = Console.ask_list("管理员 QQ 号列表", bot.get("admin_qq", []))
        bot["group_whitelist"] = Console.ask_list("启用机器人的群号列表", bot.get("group_whitelist", []))
        bot["enable_welcome"] = Console.ask_bool("是否开启入群欢迎语", bot.get("enable_welcome", True))
        
        features = bot.setdefault("features", {})
        print(f"\n {Console.BOLD}{Console.WHITE}高级特性{Console.RESET}")
        features["auto_approve_group_request"] = Console.ask_bool("是否自动通过加群申请", features.get("auto_approve_group_request", False))
        features["auto_bind_on_join"] = Console.ask_bool("是否在用户入群时自动尝试绑定", features.get("auto_bind_on_join", True))

        # [Step 4] 验证功能配置
        Console.print_step(4, 5, "验证功能配置")
        verify = bot.setdefault("verification", {})
        
        print(f" {Console.DIM}验证模式说明:{Console.RESET}")
        print(f" {Console.DIM} - group:  仅检查是否加入 VRChat Group{Console.RESET}")
        print(f" {Console.DIM} - strict: 严格模式 (检查 Group + 账号查重 + 风险账号检测){Console.RESET}")
        print(f" {Console.DIM} - mixed:  混合模式 (推荐){Console.RESET}")
        
        verify["mode"] = Console.ask_choice("验证模式", ["group", "strict", "mixed", "none"], verify.get("mode", "mixed"))
        
        verify["check_group_membership"] = Console.ask_bool("是否检查 VRChat 群组白名单 (仅允许群组成员通过)", verify.get("check_group_membership", False))
        verify["check_troll"] = Console.ask_bool("是否检测风险账号 (Troll/Nuisance)", verify.get("check_troll", False))

        if verify["mode"] != "none":
            verify["group_id"] = Console.ask("VRChat Group ID (如 grp_...)", verify.get("group_id", ""))
        
        verify["code_expiry"] = int(Console.ask("验证码有效期 (秒)", str(verify.get("code_expiry", 300))))
        verify["auto_rename"] = Console.ask_bool("验证通过后自动修改群名片", verify.get("auto_rename", True))
        verify["check_occupy"] = Console.ask_bool("是否检查 VRC 账号占用 (防止重复绑定)", verify.get("check_occupy", True))
        
        verify["auto_assign_role"] = Console.ask_bool("是否自动分配 VRChat Group 角色", verify.get("auto_assign_role", False))
        if verify["auto_assign_role"]:
            verify["target_role_id"] = Console.ask("目标角色 ID (如 grol_...)", verify.get("target_role_id", ""))

        # [Step 5] 数据库配置
        Console.print_step(5, 5, "数据库配置")
        db = config.setdefault("database", {})
        db_type = Console.ask_choice("数据库类型", ["sqlite", "json", "mysql"], db.get("type", "sqlite")).lower()
        db["type"] = db_type
        
        if db_type == "sqlite":
            db["path"] = Console.ask("数据库文件路径", db.get("path", "data/bot.db"))
        elif db_type == "json":
            db["path"] = Console.ask("JSON 文件路径", db.get("path", "data/bot.json"))
        elif db_type == "mysql":
            db["host"] = Console.ask("主机地址", db.get("host", "localhost"))
            db["port"] = int(Console.ask("端口", db.get("port", 3306)))
            db["user"] = Console.ask("用户名", db.get("user", "root"))
            db["password"] = Console.ask("密码", db.get("password", ""))
            db["database"] = Console.ask("数据库名", db.get("database", "vrc_bot"))

        # 3. 保存配置
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        print("")
        Console.print_success(f"配置已保存至 {CONFIG_PATH}")
        Console.print_info("提示: 更多高级配置（如自定义回复模板、命令权限等）请直接编辑配置文件。")
        
        print(f"\n {Console.GREEN}🎉 配置完成！你可以使用以下命令启动机器人：{Console.RESET}")
        print(f" {Console.BG_BLUE}{Console.WHITE} python main.py {Console.RESET}\n")

    except KeyboardInterrupt:
        Console.print_warn("\n配置已取消")
        sys.exit(0)
    except Exception as e:
        Console.print_error(f"\n发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()