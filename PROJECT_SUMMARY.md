# QQ-VRC双向绑定机器人项目总结

## 项目概述

本项目实现了一个基于Napcat的QQ到VRChat用户双向绑定应用，支持自动入群审查、角色管理、手动绑定等功能。

## 已完成的功能

### ✅ 核心功能

1. **自动入群审查系统**
   - 自动提取入群申请中的VRChat用户ID
   - 验证ID格式和有效性
   - 检查用户状态（是否被封禁）
   - 自动批准或通知管理员

2. **VRChat API集成**
   - 支持用户名密码认证
   - 支持TOTP二步验证
   - 支持HTTP/HTTPS代理
   - 用户信息和群组管理
   - 角色分配和移除

3. **QQ Bot管理**
   - Napcat API集成
   - 发送群消息和私聊消息
   - 处理入群申请
   - 群成员管理

4. **数据管理**
   - JSON文件存储
   - 自动备份机制
   - 数据查询和搜索
   - 统计数据生成

5. **消息模板系统**
   - 可自定义的消息模板
   - 变量替换功能
   - 支持多种消息类型

6. **日志系统**
   - 多级别日志记录
   - 分类日志文件
   - 自动轮转和压缩
   - 详细的HTTP/API日志

7. **管理员功能**
   - 手动绑定/解绑用户
   - 查看绑定列表
   - 搜索绑定记录
   - 命令行管理界面

### ✅ 部署和运维

1. **多种部署方式**
   - 源码部署
   - Docker部署
   - 系统服务部署

2. **自动化脚本**
   - 安装脚本
   - 部署脚本
   - 启动/停止脚本

3. **监控和日志**
   - 详细日志记录
   - 健康检查
   - 性能监控

## 项目结构

```
qq_vrc_binding_bot/
├── src/
│   ├── api/
│   │   ├── vrchat_api.py          # 同步VRChat API客户端
│   │   └── async_vrchat_api.py    # 异步VRChat API客户端
│   ├── core/
│   │   ├── app.py                 # 主应用类
│   │   ├── qq_bot.py              # 同步QQ Bot管理器
│   │   ├── async_qq_bot.py        # 异步QQ Bot管理器
│   │   └── data_manager.py        # 数据管理器
│   ├── handlers/
│   │   └── group_handler.py       # 群组事件处理器
│   └── utils/
│       ├── message_template.py    # 消息模板系统
│       ├── logger.py              # 日志系统
│       └── config_loader.py       # 配置加载器
├── config/
│   ├── config.yaml                # 主配置文件
│   └── config.yaml.example        # 配置示例
├── docs/
│   ├── ARCHITECTURE.md            # 架构设计文档
│   └── DEPLOYMENT.md              # 部署指南
├── data/                          # 数据目录
├── logs/                          # 日志目录
├── main.py                        # 主入口文件
├── requirements.txt               # Python依赖
├── Dockerfile                     # Docker镜像配置
├── docker-compose.yml             # Docker Compose配置
├── install.sh                     # 安装脚本
├── deploy.sh                      # 快速部署脚本
├── README.md                      # 项目文档
├── PROJECT_SUMMARY.md             # 项目总结
└── .env.example                   # 环境变量示例
```

## 技术栈

### 后端
- **Python 3.7+**: 主编程语言
- **asyncio**: 异步IO框架
- **aiohttp**: 异步HTTP客户端
- **requests**: 同步HTTP客户端
- **PyYAML**: YAML配置文件解析
- **loguru**: 日志系统
- **python-dotenv**: 环境变量管理

### 外部服务
- **Napcat**: QQ Bot框架
- **VRChat API**: VRChat官方API

### 部署
- **Docker**: 容器化部署
- **Docker Compose**: 多容器编排
- **systemd**: 系统服务管理

## 配置系统

### 配置文件 (config.yaml)

应用使用YAML配置文件，包含以下主要配置项：

- **应用配置**: 日志级别、数据目录等
- **Napcat配置**: 连接信息、访问令牌
- **VRChat配置**: 账号信息、代理设置、二步验证
- **群组配置**: 管理的QQ群和对应的VRChat群组
- **消息模板**: 欢迎、退群、错误等消息模板
- **审查规则**: 自动审批、格式验证等

### 环境变量

支持通过环境变量覆盖配置：

- `VRCHAT_USERNAME`: VRChat用户名
- `VRCHAT_PASSWORD`: VRChat密码
- `TOTP_SECRET`: TOTP密钥
- `HTTP_PROXY`/`HTTPS_PROXY`: 代理配置
- `NAPCAT_ACCESS_TOKEN`: 访问令牌

## 数据管理

### 数据存储结构

```json
{
  "bindings": {
    "123456": {
      "qq_id": 123456,
      "vrc_user_id": "usr_xxx...",
      "vrc_username": "username",
      "created_at": "2024-01-01T00:00:00",
      "operator_qq": 789012
    }
  },
  "vrc_to_qq": {
    "usr_xxx...": 123456
  },
  "metadata": {
    "version": "1.0",
    "created_at": "2024-01-01T00:00:00",
    "total_bindings": 100
  }
}
```

### 数据备份

- 自动备份到 `data/backups/` 目录
- 保留最近30天的备份
- 出错时自动创建错误备份

## 日志系统

### 日志分类

- **app.log**: 主应用日志
- **error.log**: 错误日志（ERROR级别及以上）
- **http.log**: HTTP请求日志（DEBUG级别）
- **vrchat_api.log**: VRChat API调用日志
- **qq_bot.log**: QQ Bot事件日志

### 日志级别

- **DEBUG**: 详细调试信息，包括HTTP请求和响应
- **INFO**: 一般操作记录
- **WARNING**: 警告信息
- **ERROR**: 错误信息

## 部署方式

### 1. Docker部署（推荐）

```bash
# 使用Docker Compose一键部署
docker-compose up -d
```

优点：
- 环境隔离
- 易于管理
- 快速部署

### 2. 源码部署

```bash
# 使用安装脚本
./install.sh

# 或使用部署脚本
./deploy.sh -t source
```

优点：
- 灵活性高
- 易于调试
- 资源占用少

### 3. 系统服务部署

```bash
# 创建systemd服务
sudo systemctl enable qq-vrc-bot
sudo systemctl start qq-vrc-bot
```

优点：
- 开机自启
- 系统级管理
- 稳定可靠

## 运维管理

### 启动和停止

```bash
# Docker方式
docker-compose up -d    # 启动
docker-compose down     # 停止

# 系统服务方式
sudo systemctl start qq-vrc-bot   # 启动
sudo systemctl stop qq-vrc-bot    # 停止
sudo systemctl restart qq-vrc-bot # 重启
```

### 查看日志

```bash
# Docker方式
docker-compose logs -f

# 系统服务方式
sudo journalctl -u qq-vrc-bot -f

# 直接查看日志文件
tail -f logs/app.log
```

### 数据管理

```bash
# 导出数据
python main.py --cli
# 选择导出数据选项

# 查看统计数据
python main.py --cli
# 选择查看统计信息
```

## 管理员命令

在QQ群中，管理员可以使用以下命令：

| 命令 | 说明 |
|------|------|
| `!bind <QQ号> <VRChat用户ID>` | 手动绑定用户 |
| `!unbind <QQ号>` | 解绑用户 |
| `!list` | 查看所有绑定记录 |
| `!search <关键词>` | 搜索绑定记录 |
| `!help` | 显示帮助信息 |

## 监控指标

### 关键指标

- **入群申请处理成功率**: 目标 >95%
- **VRChat API响应时间**: 目标 <2秒
- **QQ Bot连接状态**: 保持连接
- **内存使用率**: 目标 <100MB
- **数据备份成功率**: 目标 100%

### 告警规则

- API错误率 > 10%
- 队列积压 > 100
- 内存使用 > 200MB
- 连接断开 > 5分钟

## 安全考虑

1. **数据加密**: 敏感信息使用环境变量存储
2. **访问控制**: 限制管理员QQ号列表
3. **输入验证**: 严格验证VRChat用户ID格式
4. **日志脱敏**: 不记录密码等敏感信息
5. **速率限制**: 防止API滥用

## 性能优化

1. **异步IO**: 使用asyncio处理并发请求
2. **连接池**: HTTP连接复用
3. **缓存**: 缓存常用数据
4. **批量操作**: 批量处理多个请求
5. **日志异步**: 避免日志阻塞

## 扩展性

### 插件系统

支持通过插件扩展功能：

```python
class Plugin:
    def on_group_request(self, event):
        pass
    
    def on_user_join(self, event):
        pass
```

### 数据存储扩展

支持多种存储后端：
- JSON文件（默认）
- SQLite数据库
- MySQL/PostgreSQL
- Redis缓存

### 消息平台扩展

支持多个消息平台：
- QQ（已实现）
- 微信
- Discord
- Telegram

## 测试

### 单元测试

```python
# 测试VRChat API
async def test_vrc_api():
    api = AsyncVRChatAPIClient("test", "test")
    assert await api.authenticate()

# 测试消息模板
async def test_message_template():
    template = MessageTemplate({})
    result = template.render("test", {"var": "value"})
    assert result == "Expected"
```

### 集成测试

```python
# 测试完整流程
async def test_full_workflow():
    event = create_mock_group_request()
    await group_handler.handle_group_request(event)
    binding = data_manager.get_binding_by_qq(123456)
    assert binding is not None
```

## 故障排除

### 常见问题

1. **VRChat API连接失败**
   - 检查用户名和密码
   - 配置代理（国内用户）
   - 查看 `logs/vrchat_api.log`

2. **QQ Bot连接失败**
   - 确保Napcat正在运行
   - 检查主机和端口配置
   - 查看 `logs/qq_bot.log`

3. **入群申请未处理**
   - 检查群组配置
   - 确认群组已启用
   - 查看 `logs/app.log`

### 调试技巧

1. 使用CLI模式进行交互式测试
2. 启用DEBUG日志级别查看详细信息
3. 使用 `--config` 参数测试不同配置
4. 检查配置文件语法（YAML）

## 未来改进

### 功能增强

- [ ] Web管理界面
- [ ] 数据统计图表
- [ ] 多语言支持
- [ ] 插件市场
- [ ] API接口

### 性能优化

- [ ] Redis缓存
- [ ] 数据库连接池
- [ ] 消息队列
- [ ] 分布式部署

### 监控告警

- [ ] Prometheus指标
- [ ] Grafana仪表盘
- [ ] 邮件/短信告警
- [ ] 健康检查API

## 总结

本项目实现了一个功能完整的QQ到VRChat双向绑定机器人，具有以下特点：

### 优点

1. **功能完善**: 支持自动审查、手动管理、角色分配等
2. **易于部署**: 支持Docker、源码、系统服务多种方式
3. **稳定可靠**: 完善的错误处理和日志系统
4. **易于扩展**: 模块化设计，支持插件扩展
5. **安全可控**: 权限控制、日志脱敏、速率限制

### 适用场景

- VRChat社群管理
- 游戏公会管理
- 跨平台用户绑定
- 自动化群管理

### 使用建议

1. **小规模测试**: 先在小群测试功能
2. **监控日志**: 定期检查日志发现问题
3. **备份数据**: 定期备份绑定数据
4. **更新维护**: 及时更新到最新版本

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目Issue Tracker
- 项目Wiki
- 技术文档