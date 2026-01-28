# VRChat-QQ 双向绑定机器人

一个强大的VRChat-QQ双向绑定机器人，支持多种验证模式、群组管理和角色分配功能，旨在为VRChat社群提供高效的QQ群管理解决方案。

## 🚀 功能特性

- **多验证模式支持**
  - 混合模式：允许用户先入群后验证，超时未验证将被禁言
  - 严格模式：必须先验证才能入群，超时未验证将被踢出
  - 禁用模式：不强制验证，仅做登记

- **灵活的群组配置**
  - 群组特定的验证规则设置
  - 支持多个QQ群和VRChat群组的独立配置
  - 可配置的自动重命名、角色分配等功能

- **智能绑定管理**
  - 防占用机制：防止同一VRChat账号被多个QQ号绑定
  - 群组成员资格检查
  - 风险账号检测（Troll账户）

- **自动化功能**
  - 自动验证处理
  - 自动角色分配（需权限）
  - 自动重命名群名片

## 🛠️ 技术栈

- **Python 3.8+**
- **异步框架**：asyncio
- **数据库**：SQLite（默认）/ MySQL
- **API**：VRChat API, QQ Bot API (通过NapCat)
- **图像生成**：Pillow

## 📋 依赖项

- `requests>=2.31.0`
- `pyotp>=2.9.0`
- `colorama>=0.4.6`
- `websockets>=12.0`
- `pymysql>=1.1.0`
- `aiohttp>=3.9.0`
- `pillow>=12.1.0`
- `dynaconf>=3.2.12`
- `vrchatapi>=1.20.7`
- `ncatbot>=0.1.0`

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd vrchatQQbot

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置机器人

首次运行时，程序会自动创建配置文件 `config/config.json`，你需要编辑该文件以配置：

- **VRChat 账号信息**：用户名、密码（支持双因素认证）
- **NapCat WebSocket**：连接地址和认证令牌
- **数据库配置**：SQLite 或 MySQL 设置
- **机器人管理员**：超级管理员QQ号列表

### 3. 启动机器人

```bash
python main.py --config config/config.json
```

### 4. 配置群组设置

机器人启动后，可以在QQ群中使用 `!set` 命令配置各项功能：

```text
!set verification_mode mixed          # 设置验证模式
!set auto_reject_on_join true         # 开启自动拒绝
!set vrc_group_id [群组ID]           # 设置VRChat群组ID
!set target_role_id [角色ID]         # 设置目标角色ID
!set auto_assign_role true            # 开启自动分配角色
!set auto_rename true                # 开启自动重命名
!set check_group_membership true      # 开启群组成员检查
!set check_troll true                # 开启风险账号检测
```

## ⚙️ 配置说明

### 验证模式详解

- **混合模式 (mixed)**：用户提交的进群请求将被直接接受并收录global_bindings中，允许用户进群之后再完成绑定操作，如果用户在指定时间内未完成绑定则进入无限期禁言状态，完成绑定后自动解除。

- **严格模式 (strict)**：优先检测该群是否被以其它方式（例如群管的!bind指令）对于该用户进行了绑定，如果已经被绑定，则依然类似于混合行为（即允许进群后再完成绑定），但不同的是，如果在配置文件中指定的超时时间内未完成验证操作，则会进行踢出并在群内警报；上述条件不成立时，如果自动拒绝功能被开启，则无条件拒绝理由，如果自动拒绝被关闭则在群内报警，不进行任何操作。

- **禁用模式 (disabled)**：仅进行登记，只要答案全字匹配某vrc账号或匹配上usrid即可进群，进入登记，但是不进入绑定。

### 重要提醒

当启用自动分配角色功能时，需要确保：

1. 机器人账号在VRChat群组中拥有分配角色的权限
2. 已正确设置VRChat群组ID (`vrc_group_id`)
3. 已正确设置目标角色ID (`target_role_id`)

## 🎯 主要命令

- `!help` - 显示帮助信息
- `!bind [QQ号] [VRChat ID/名字]` - 手动绑定账号（管理员）
- `!unbind [QQ号]` - 解绑账号（管理员）
- `!verify` - 完成验证
- `!code` - 重新获取验证码
- `!list` - 查看绑定列表
- `!query [用户名]` - 查询绑定记录
- `!search [用户名]` - 搜索VRChat用户
- `!set [设置项] [值]` - 设置群组功能

## 🔐 权限管理

- **超级管理员**：配置文件中指定的QQ号，拥有所有权限
- **群管理员**：可使用部分管理命令，如设置群组功能
- **普通用户**：可使用基本验证和查询命令

## 🛡️ 安全特性

- **防占用检查**：确保同一VRChat账号只能绑定一个QQ号
- **群组成员验证**：验证用户是否为指定VRChat群组的成员
- **风险账号检测**：识别并阻止潜在的风险账号
- **验证时效性**：验证码和验证请求有过期时间

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

pass

## 🆘 支持

如有问题，请查看项目Issues或联系维护者。