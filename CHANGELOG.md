# 更新日志

## v1.1.0 (2024-01-09)

### ✨ 新功能

1. **Cookie持久化支持**
   - Cookie自动保存到 `data/vrchat_cookie.json`
   - Cookie有效期30天
   - 避免每次启动都需要重新认证

2. **改进的TOTP处理**
   - TOTP密钥生成改为可选功能
   - 新增 `auto_generate` 配置选项
   - 更灵活的二步验证处理

3. **CLI交互式模式**
   - 全新 `--cli-v2` 命令行模式
   - 支持交互式验证码输入
   - 完整的认证测试和配置管理
   - 更友好的用户界面

4. **优化的目录结构**
   - 配置文件建议放在 `data/config/` 目录
   - 便于Docker单volume挂载
   - 更符合容器化部署规范

### 🔄 改进

1. **VRChat API客户端**
   - 使用改进版异步客户端
   - 更好的错误处理和重试机制
   - 支持Cookie自动加载和保存

2. **认证流程**
   - 优先使用已保存的Cookie
   - 自动检测Cookie有效性
   - 认证失败时提供更详细的错误信息

3. **CLI体验**
   - 增强的交互式菜单
   - 实时状态显示
   - 更完善的帮助信息

### 📚 文档更新

1. **README.md**
   - 添加CLI交互式模式说明
   - 更新目录结构说明
   - 完善TOTP配置文档
   - 增加故障排除指南

2. **新增文档**
   - `CHANGELOG.md`: 版本更新日志
   - `src/core/cli_handler.py`: CLI处理器
   - `src/api/async_vrchat_api_v2.py`: 改进版API客户端

### 🐛 Bug修复

1. 修复了TOTP强制生成的问题
2. 修复了CLI模式下认证失败直接退出的问题
3. 修复了目录结构不符合容器化规范的问题

### ⚠️ 破坏性变更

1. **配置文件路径变更**
   - 旧路径: `config/config.yaml`
   - 新路径: `data/config/config.yaml`
   - 迁移方法:
     ```bash
     mkdir -p data/config
     cp config/config.yaml data/config/
     ```

2. **CLI命令变更**
   - 旧命令: `python main.py --cli`
   - 新命令（交互式）: `python main.py --cli-v2`
   - 旧命令仍然可用，但建议使用新版

### 🚀 使用建议

1. **首次使用**
   ```bash
   python main.py --cli-v2
   # 选择"认证和连接测试"进行交互式配置
   ```

2. **Docker部署**
   ```bash
   mkdir -p data/config
   cp config/config.yaml.example data/config/config.yaml
   # 编辑配置文件
   docker-compose up -d
   ```

3. **故障排除**
   - 检查 `data/vrchat_cookie.json` 是否存在
   - 使用 `--cli-v2` 模式进行交互式调试
   - 查看日志文件获取详细信息

## v1.0.0 (2024-01-08)

### ✨ 初始版本功能

1. **自动入群审查**
   - 自动提取VRChat用户ID
   - 验证ID格式和有效性
   - 自动批准或通知管理员

2. **VRChat API集成**
   - 用户认证（支持2FA）
   - 用户信息查询
   - 群组管理和角色分配

3. **QQ Bot管理**
   - Napcat API集成
   - 消息发送和接收
   - 群成员管理

4. **数据管理**
   - JSON文件存储
   - 用户绑定关系管理
   - 自动备份机制

5. **消息模板**
   - 可自定义的消息模板
   - 变量替换功能

6. **日志系统**
   - 多级别日志记录
   - 分类日志文件

7. **管理员功能**
   - 手动绑定/解绑用户
   - 查看绑定列表
   - 搜索绑定记录

8. **部署支持**
   - Docker容器化
   - 系统服务部署
   - 自动化脚本

---

## 版本规划

### 即将推出 (v1.2.0)

- [ ] Web管理界面
- [ ] 数据统计图表
- [ ] 插件系统
- [ ] API接口
- [ ] 消息队列支持

### 未来计划 (v2.0.0)

- [ ] 多平台支持（微信、Discord等）
- [ ] 数据库后端（MySQL/PostgreSQL）
- [ ] 分布式部署
- [ ] 监控告警系统
- [ ] 插件市场

---

## 升级指南

### 从v1.0.0升级到v1.1.0

1. **备份数据**
   ```bash
   cp -r data data.backup
   ```

2. **迁移配置文件**
   ```bash
   mkdir -p data/config
   cp config/config.yaml data/config/
   ```

3. **更新配置**
   - 在 `vrchat.two_factor` 下添加 `auto_generate: false`
   - 检查其他配置项是否有变化

4. **测试运行**
   ```bash
   python main.py --cli-v2
   # 检查认证是否正常
   ```

5. **更新Docker配置**
   - 修改volume挂载路径
   - 更新docker-compose.yml

---

## 兼容性说明

- **Python版本**: 3.7+
- **Napcat版本**: 最新稳定版
- **VRChat API**: 当前版本
- **Docker**: 20.10+
- **Docker Compose**: 1.27+