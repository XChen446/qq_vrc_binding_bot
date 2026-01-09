# QQ-VRC双向绑定机器人架构设计

## 系统架构概述

本应用采用模块化设计，支持异步并发处理，主要由以下几个核心组件构成：

```
┌─────────────────────────────────────────────────────────────┐
│                        应用层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   主应用    │  │  配置加载   │  │  日志管理   │         │
│  │   (App)     │  │   (Config)  │  │   (Logger)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      核心服务层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  VRChat API │  │   QQ Bot    │  │  数据管理   │         │
│  │   (Async)   │  │   (Async)   │  │   (Data)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      事件处理层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 群组处理器  │  │ 消息模板    │  │  速率限制   │         │
│  │ (Handler)   │  │ (Template)  │  │  (Rate)     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      外部服务层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  VRChat     │  │   Napcat    │  │   文件系统  │         │
│  │   服务器    │  │   QQ Bot    │  │   (JSON)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 组件详细说明

### 1. 主应用类 (QQVRCBindingApp)

**职责:**
- 协调所有组件的初始化和运行
- 管理应用生命周期（启动、停止、重启）
- 处理信号和异常
- 提供CLI和GUI界面

**关键方法:**
- `initialize()`: 初始化所有组件
- `start()`: 启动应用主循环
- `stop()`: 优雅关闭应用
- `authenticate_vrc()`: VRChat API认证

### 2. VRChat API客户端 (AsyncVRChatAPIClient)

**职责:**
- 处理VRChat API调用
- 支持代理和二步验证
- 管理认证状态
- 处理错误和重试

**核心功能:**
- 用户认证（支持2FA）
- 用户信息查询
- 群组管理（添加/移除成员、分配角色）
- 请求速率控制
- 代理支持

**关键方法:**
- `authenticate()`: 用户认证
- `get_user_info()`: 获取用户信息
- `add_user_to_group()`: 添加用户到群组
- `remove_user_from_group()`: 从群组移除用户

### 3. QQ Bot管理器 (AsyncQQBotManager)

**职责:**
- 与Napcat API交互
- 发送和接收QQ消息
- 管理群组操作
- 处理事件回调

**核心功能:**
- 发送群消息和私聊消息
- 处理入群申请
- 获取群成员信息
- 踢出群成员
- 事件处理器注册

**关键方法:**
- `send_group_message()`: 发送群消息
- `handle_group_request()`: 处理入群申请
- `get_group_member_list()`: 获取群成员列表
- `register_event_handler()`: 注册事件处理器

### 4. 数据管理器 (DataManager)

**职责:**
- 用户绑定数据持久化
- 数据查询和搜索
- 自动备份和恢复
- 统计数据生成

**数据存储结构:**
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

**关键方法:**
- `bind_user()`: 绑定用户
- `unbind_user()`: 解绑用户
- `get_binding_by_qq()`: 通过QQ号查询绑定
- `search_bindings()`: 搜索绑定记录

### 5. 群组处理器 (GroupHandler)

**职责:**
- 处理QQ群相关事件
- 执行自动审查逻辑
- 调用VRChat API
- 发送通知消息

**处理流程:**

#### 入群申请处理流程
```
1. 接收入群申请事件
2. 提取VRChat用户ID
3. 验证ID格式
4. 获取VRChat用户信息
5. 检查用户状态
6. 自动批准/通知管理员
7. 绑定用户数据
8. 添加到VRChat群组
9. 发送欢迎消息
```

#### 退群处理流程
```
1. 接收退群事件
2. 获取用户绑定信息
3. 从VRChat群组移除
4. 删除绑定数据
5. 发送退群消息
```

**关键方法:**
- `handle_group_request()`: 处理入群申请
- `handle_group_increase()`: 处理成员入群
- `handle_group_decrease()`: 处理成员退群
- `handle_admin_command()`: 处理管理员命令

### 6. 消息模板系统 (MessageTemplate)

**职责:**
- 管理消息模板
- 变量替换
- 模板渲染

**支持的变量:**
- `%vrc_username%`: VRChat用户名
- `%vrc_userid%`: VRChat用户ID
- `%qq_user_num%`: QQ号
- `%execute_user%`: 执行操作的用户
- `%error_reason%`: 错误原因
- 等等...

**模板示例:**
```yaml
welcome_message: |
  欢迎 %vrc_username% 加入本群！
  您的VRChat用户ID: %vrc_userid%
  已自动为您分配角色，祝您游戏愉快！
```

### 7. 日志系统 (AppLogger)

**职责:**
- 多级别日志记录
- 文件分割和轮转
- 分类日志输出

**日志分类:**
- `app.log`: 主应用日志
- `error.log`: 错误日志
- `http.log`: HTTP请求日志
- `vrchat_api.log`: VRChat API日志
- `qq_bot.log`: QQ Bot日志

**日志级别:**
- DEBUG: 详细调试信息
- INFO: 一般操作记录
- WARNING: 警告信息
- ERROR: 错误信息

## 数据流图

### 入群申请数据流

```
QQ用户申请入群
    ↓
Napcat接收申请事件
    ↓
QQ Bot管理器转发事件
    ↓
群组处理器处理申请
    ↓
提取VRChat用户ID
    ↓
VRChat API验证用户
    ↓
[验证成功]      [验证失败]
    ↓              ↓
自动批准      通知管理员
    ↓              ↓
绑定用户数据      等待处理
    ↓              ↓
添加到VRChat群组  管理员处理
    ↓              ↓
发送欢迎消息    完成绑定
```

### 管理员命令数据流

```
管理员发送命令
    ↓
Napcat接收消息事件
    ↓
QQ Bot管理器转发事件
    ↓
群组处理器解析命令
    ↓
执行相应操作
    ↓
[bind]  [unbind]  [list]  [search]
    ↓       ↓         ↓        ↓
绑定用户 解绑用户  列出绑定  搜索绑定
    ↓       ↓         ↓        ↓
返回结果消息
```

## 并发处理

应用使用异步IO处理并发请求：

```python
# 异步处理多个入群申请
async def handle_multiple_requests(requests):
    tasks = []
    for request in requests:
        task = asyncio.create_task(
            group_handler.handle_group_request(request)
        )
        tasks.append(task)
    
    # 并发执行所有任务
    results = await asyncio.gather(*tasks)
    return results
```

## 错误处理

### 异常处理策略

1. **捕获并重试**: 网络错误自动重试
2. **降级处理**: 主功能失败时使用备用方案
3. **通知管理员**: 严重错误时通知管理员
4. **记录日志**: 所有异常都记录详细日志

### 常见错误处理

- **VRChat API超时**: 自动重试，最多3次
- **速率限制**: 等待后重试，指数退避
- **认证失败**: 尝试刷新token或使用2FA
- **网络错误**: 使用代理重试

## 安全考虑

1. **数据加密**: 敏感信息使用环境变量存储
2. **访问控制**: 限制管理员QQ号列表
3. **输入验证**: 严格验证VRChat用户ID格式
4. **日志脱敏**: 日志中不记录密码等敏感信息
5. **速率限制**: 防止API滥用

## 性能优化

1. **异步IO**: 使用asyncio处理并发请求
2. **连接池**: HTTP连接复用
3. **缓存**: 缓存常用数据（用户信息等）
4. **批量操作**: 批量处理多个请求
5. **日志异步**: 使用异步日志避免阻塞

## 监控和告警

### 监控指标

- 入群申请处理成功率
- VRChat API响应时间
- QQ Bot连接状态
- 内存和CPU使用率
- 绑定数据增长趋势

### 告警规则

- API错误率超过阈值
- 队列积压过多
- 内存使用过高
- 长时间无心跳

## 扩展性设计

### 插件系统

```python
class Plugin:
    """插件基类"""
    
    def on_group_request(self, event):
        """处理入群申请"""
        pass
    
    def on_user_join(self, event):
        """处理用户入群"""
        pass
    
    def on_user_leave(self, event):
        """处理用户退群"""
        pass
```

### 数据存储扩展

支持多种数据存储后端：
- JSON文件（默认）
- SQLite数据库
- MySQL/PostgreSQL
- Redis缓存

### 消息适配器

支持多种消息平台：
- QQ（Napcat）
- 微信
- Discord
- Telegram

## 部署架构

### Docker部署

```yaml
# docker-compose.yml
version: '3.8'
services:
  qq-vrc-bot:
    build: .
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - napcat
  
  napcat:
    image: napneko/napcat:latest
    volumes:
      - napcat_data:/app/napcat
```

### 系统服务部署

```ini
# /etc/systemd/system/qq-vrc-bot.service
[Unit]
Description=QQ-VRC双向绑定机器人
After=network.target

[Service]
Type=simple
User=qqbot
WorkingDirectory=/opt/qq-vrc-bot
ExecStart=/opt/qq-vrc-bot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 测试策略

### 单元测试

```python
# 测试VRChat API客户端
async def test_vrc_api():
    api = AsyncVRChatAPIClient("test", "test")
    assert await api.authenticate() == True

# 测试消息模板
async def test_message_template():
    template = MessageTemplate({})
    result = template.render("test", {"var": "value"})
    assert result == "Expected result"
```

### 集成测试

```python
# 测试完整流程
async def test_full_workflow():
    # 模拟入群申请
    event = create_mock_group_request()
    
    # 处理申请
    await group_handler.handle_group_request(event)
    
    # 验证结果
    binding = data_manager.get_binding_by_qq(123456)
    assert binding is not None
```

## 总结

本应用采用现代化的异步架构设计，具有良好的可扩展性和维护性。模块化设计使得各个组件可以独立开发和测试，同时支持多种部署方式和扩展机制。

关键设计原则：
- **高内聚低耦合**: 各组件职责明确
- **异步优先**: 充分利用异步IO提高性能
- **容错设计**: 完善的错误处理和恢复机制
- **可扩展性**: 支持插件和多种后端
- **可观测性**: 详细的日志和监控

通过这样的设计，应用可以稳定高效地处理大量并发请求，同时保持良好的可维护性和扩展性。