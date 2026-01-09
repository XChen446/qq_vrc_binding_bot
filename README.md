# QQ到VRChat双向绑定机器人

一个基于Napcat的QQ群到VRChat用户自动双向绑定应用，支持自动入群审查、角色管理、手动绑定等功能。

## 功能特性

- 🔄 **自动双向绑定**: 自动处理入群申请，验证VRChat用户ID并绑定QQ账号
- 🛡️ **智能审查**: 自动检查VRChat用户ID格式、用户状态和群组权限
- 👥 **角色管理**: 自动将用户添加到指定的VRChat群组角色中
- 🔧 **手动管理**: 管理员可通过命令手动绑定/解绑用户
- 📊 **日志系统**: 多级别日志记录，支持HTTP请求和API调用详细日志
- 🌐 **代理支持**: 支持HTTP/HTTPS代理，适应国内网络环境
- 🔐 **二步验证**: 支持TOTP和邮箱二步验证
- 💬 **消息模板**: 可自定义的欢迎、退群、错误等消息模板

## 项目结构

```
qq_vrc_binding_bot/
├── src/
│   ├── api/                    # VRChat API客户端
│   │   ├── vrchat_api.py       # 同步版本
│   │   └── async_vrchat_api.py # 异步版本
│   ├── core/                   # 核心组件
│   │   ├── app.py              # 主应用类
│   │   ├── qq_bot.py           # QQ Bot管理器
│   │   ├── async_qq_bot.py     # 异步QQ Bot管理器
│   │   └── data_manager.py     # 数据管理器
│   ├── handlers/               # 事件处理器
│   │   └── group_handler.py    # 群组事件处理器
│   └── utils/                  # 工具类
│       ├── message_template.py # 消息模板系统
│       ├── logger.py           # 日志系统
│       └── config_loader.py    # 配置加载器
├── config/
│   ├── config.yaml             # 主配置文件
│   └── config.yaml.example     # 配置示例
├── data/                       # 数据目录
├── logs/                       # 日志目录
├── main.py                     # 主入口文件
├── requirements.txt            # Python依赖
├── README.md                   # 项目文档
└── .env.example               # 环境变量示例
```

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd qq_vrc_binding_bot

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置应用

#### 方式一：使用配置文件

```bash
# 复制配置文件模板
cp config/config.yaml.example config/config.yaml

# 编辑配置文件
nano config/config.yaml  # 或使用其他编辑器
```

#### 方式二：使用环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件
nano .env
```

### 3. 配置Napcat

确保Napcat已安装并运行：

```bash
# 安装Napcat（如果尚未安装）
npm install -g napcat

# 启动Napcat
napcat
```

### 4. 运行应用

#### 服务模式（后台运行）

```bash
# 运行应用
python main.py
```

#### CLI模式（交互式调试）

```bash
# 运行CLI模式
python main.py --cli
```

#### 指定配置文件

```bash
# 使用指定配置文件
python main.py --config /path/to/config.yaml

# CLI模式 + 指定配置
python main.py --cli --config /path/to/config.yaml
```

## 配置文件说明

### 应用配置 (app)

```yaml
app:
  name: "QQ-VRC双向绑定机器人"  # 应用名称
  version: "1.0.0"              # 版本
  enabled: true                 # 是否启用
  log_level: "INFO"            # 日志级别: DEBUG, INFO, WARNING, ERROR
  data_dir: "./data"           # 数据目录
  log_dir: "./logs"            # 日志目录
```

### Napcat配置 (napcat)

```yaml
napcat:
  enabled: true
  host: "127.0.0.1"            # Napcat服务器地址
  port: 3000                   # Napcat服务器端口
  access_token: ""             # 访问令牌（可选）
  webhook_url: ""              # Webhook地址（可选）
```

### VRChat配置 (vrchat)

```yaml
vrchat:
  username: "your_username"    # VRChat用户名
  password: "your_password"    # VRChat密码
  api_key: "JlE5Jldo5JibnkqO"  # VRChat API Key
  proxy:
    enabled: false
    http_proxy: "http://127.0.0.1:7890"
    https_proxy: "http://127.0.0.1:7890"
  two_factor:
    enabled: false
    method: "totp"             # totp 或 email
    totp_secret: ""            # TOTP密钥（可选）
```

### 群组配置 (groups)

```yaml
groups:
  managed_groups:
    - group_id: 123456789      # QQ群号
      enabled: true
      vrc_group_id: "grp_fdd4cdf6-b3e0-4be3-a040-5b8abf2617f4"  # VRChat群组ID
      auto_assign_role: "rol_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # 角色ID
      join_request_keyword: "VRChat用户ID"  # 入群申请关键词
      admin_qq_ids: [111111, 222222]  # 管理员QQ号列表
```

### 消息模板配置 (messages)

```yaml
messages:
  welcome_message: |
    欢迎 %vrc_username% 加入本群！
    您的VRChat用户ID: %vrc_userid%
    已自动为您分配角色，祝您游戏愉快！
  
  leave_message: |
    用户 %vrc_username% (%vrc_userid%) 已离开群组
  
  role_assignment_failed: |
    为用户 %vrc_username% (%vrc_userid%) 分配角色失败
    失败原因: %error_reason%
    请管理员手动处理
```

### 审查规则配置 (review)

```yaml
review:
  auto_approve: true           # 是否自动批准
  userid_pattern: "usr_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
  check_user_status: true      # 是否检查用户状态
  on_role_fail: "notify_admin"  # 角色分配失败处理方式: notify_admin, ignore
```

## 管理员命令

在QQ群中，管理员可以使用以下命令：

| 命令 | 说明 | 示例 |
|------|------|------|
| `!bind <QQ号> <VRChat用户ID>` | 手动绑定用户 | `!bind 123456 usr_abc123...` |
| `!unbind <QQ号>` | 解绑用户 | `!unbind 123456` |
| `!list` | 查看所有绑定记录 | `!list` |
| `!search <关键词>` | 搜索绑定记录 | `!search username` |
| `!help` | 显示帮助信息 | `!help` |

## 支持的变量

消息模板支持以下变量：

| 变量 | 说明 |
|------|------|
| `%vrc_username%` | VRChat用户名 |
| `%vrc_userid%` | VRChat用户ID |
| `%qq_user_num%` | QQ号 |
| `%qq_group_id%` | 群号 |
| `%execute_user%` | 执行操作的用户 |
| `%error_reason%` | 错误原因 |
| `%operation_time%` | 操作时间 |
| `%status%` | 操作状态 |

## 环境变量

可以通过环境变量覆盖配置文件：

```bash
# VRChat账号
VRCHAT_USERNAME=your_username
VRCHAT_PASSWORD=your_password

# TOTP密钥（二步验证）
TOTP_SECRET=your_totp_secret

# 代理配置
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# Napcat配置
NAPCAT_ACCESS_TOKEN=your_token
```

## 日志系统

应用使用多级别日志系统：

- **DEBUG**: 详细的HTTP请求和响应
- **INFO**: 一般操作记录
- **WARNING**: 警告信息
- **ERROR**: 错误信息

日志文件保存在 `logs/` 目录：

- `app.log` - 主日志文件
- `error.log` - 错误日志
- `http.log` - HTTP请求日志
- `vrchat_api.log` - VRChat API日志
- `qq_bot.log` - QQ Bot日志

## 数据管理

用户绑定数据存储在 `data/user_bindings.json` 中，包含：

- QQ号到VRChat用户ID的映射
- VRChat用户ID到QQ号的反向映射
- 绑定时间、操作者等元数据

数据自动备份到 `data/backups/` 目录。

## 故障排除

### VRChat API连接失败

1. 检查用户名和密码是否正确
2. 如果使用二步验证，配置TOTP密钥
3. 检查代理设置（国内网络需要）
4. 查看 `logs/vrchat_api.log` 获取详细错误信息

### QQ Bot连接失败

1. 确保Napcat正在运行
2. 检查主机地址和端口配置
3. 验证访问令牌（如果设置了）
4. 查看 `logs/qq_bot.log` 获取详细错误信息

### 入群申请未自动处理

1. 检查群组是否在管理列表中
2. 确认群组已启用
3. 检查VRChat用户ID格式是否正确
4. 查看 `logs/app.log` 获取处理详情

## 性能优化

- 使用异步IO处理并发请求
- 实现速率限制防止API滥用
- 数据自动备份和清理
- 日志文件自动轮转和压缩

## 安全建议

- 不要将密码直接写入配置文件，使用环境变量
- 定期更换VRChat密码
- 限制管理员的QQ号列表
- 监控日志文件中的异常活动
- 使用防火墙限制Napcat的访问

## 更新日志

### v1.0.0
- 初始版本
- 支持自动入群审查和绑定
- 支持手动绑定管理
- 支持VRChat角色管理
- 支持代理和二步验证

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 技术支持

如有问题，请查看：
- 项目Wiki
- Issue Tracker
- 日志文件
- VRChat API文档
- Napcat文档