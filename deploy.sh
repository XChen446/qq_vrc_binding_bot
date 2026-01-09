#!/bin/bash
# QQ-VRC双向绑定机器人快速部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
DEPLOY_TYPE="docker"  # docker 或 source
PROJECT_NAME="qq-vrc-binding-bot"
PROJECT_DIR="$(pwd)"

# 帮助信息
show_help() {
    echo -e "${GREEN}QQ-VRC双向绑定机器人快速部署脚本${NC}"
    echo -e ""
    echo -e "用法:"
    echo -e "  ./deploy.sh [OPTIONS]"
    echo -e ""
    echo -e "选项:"
    echo -e "  -t, --type TYPE     部署类型: docker 或 source (默认: docker)"
    echo -e "  -d, --dir DIR       项目目录 (默认: 当前目录)"
    echo -e "  -n, --name NAME     项目名称 (默认: qq-vrc-binding-bot)"
    echo -e "  -h, --help          显示帮助信息"
    echo -e ""
    echo -e "示例:"
    echo -e "  ./deploy.sh -t docker                    # Docker部署"
    echo -e "  ./deploy.sh -t source -d /opt/qq-vrc     # 源码部署"
    echo -e "  ./deploy.sh --type docker --name my-bot  # 自定义名称的Docker部署"
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                DEPLOY_TYPE="$2"
                shift 2
                ;;
            -d|--dir)
                PROJECT_DIR="$2"
                shift 2
                ;;
            -n|--name)
                PROJECT_NAME="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}未知选项: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 打印步骤信息
print_step() {
    echo -e ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e ""
}

# Docker部署
deploy_docker() {
    print_step "Docker部署模式"
    
    # 检查Docker
    if ! command_exists docker; then
        echo -e "${RED}错误: 未安装Docker${NC}"
        echo -e "请先安装Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command_exists docker-compose; then
        echo -e "${YELLOW}警告: 未安装Docker Compose${NC}"
        echo -e "正在安装Docker Compose..."
        pip install docker-compose
    fi
    
    # 创建项目目录
    if [ ! -d "$PROJECT_DIR" ]; then
        echo -e "${YELLOW}创建项目目录: $PROJECT_DIR${NC}"
        mkdir -p "$PROJECT_DIR"
    fi
    
    cd "$PROJECT_DIR"
    
    # 复制必要文件
    echo -e "${YELLOW}准备Docker配置文件...${NC}"
    
    # 创建Docker Compose文件
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  qq-vrc-bot:
    image: qq-vrc-bot:latest
    build: .
    container_name: qq-vrc-binding-bot
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
    networks:
      - bot-network
    depends_on:
      - napcat
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.path.insert(0, '/app'); from src.core.app import QQVRCBindingApp"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
  napcat:
    image: napneko/napcat:latest
    container_name: napcat-qq
    restart: unless-stopped
    environment:
      - TZ=Asia/Shanghai
      - ACCOUNT=${QQ_ACCOUNT:-}
      - WS_ENABLE=true
      - WS_PORT=3000
      - HTTP_ENABLE=true
      - HTTP_PORT=6099
    volumes:
      - napcat_data:/app/napcat
    ports:
      - "3000:3000"
      - "6099:6099"
    networks:
      - bot-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6099/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  bot-network:
    driver: bridge

volumes:
  napcat_data:
EOF
    
    # 创建环境变量模板
    cat > .env.template << 'EOF'
# VRChat配置
VRCHAT_USERNAME=your_vrchat_username
VRCHAT_PASSWORD=your_vrchat_password
TOTP_SECRET=your_totp_secret_if_needed

# 代理配置（国内用户需要）
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# QQ配置
QQ_ACCOUNT=your_qq_account

# Napcat配置
NAPCAT_ACCESS_TOKEN=your_token_if_needed

# 应用配置
LOG_LEVEL=INFO
EOF
    
    # 创建配置文件模板
    mkdir -p config
    cat > config/config.yaml.template << 'EOF'
# 应用基本配置
app:
  name: "QQ-VRC双向绑定机器人"
  version: "1.0.0"
  enabled: true
  log_level: "INFO"
  data_dir: "/app/data"
  log_dir: "/app/logs"

# Napcat配置
napcat:
  enabled: true
  host: "napcat"
  port: 3000
  access_token: ""
  webhook_url: ""

# VRChat API配置
vrchat:
  username: ""
  password: ""
  api_key: "JlE5Jldo5JibnkqO"
  proxy:
    enabled: false
    http_proxy: ""
    https_proxy: ""
  
  two_factor:
    enabled: false
    method: "totp"
    totp_secret: ""

# 群组配置
groups:
  managed_groups:
    - group_id: 123456789
      enabled: true
      vrc_group_id: "grp_fdd4cdf6-b3e0-4be3-a040-5b8abf2617f4"
      auto_assign_role: "rol_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
      join_request_keyword: "VRChat用户ID"
      admin_qq_ids: [111111, 222222]

# 消息模板配置
messages:
  welcome_message: |
    欢迎 %vrc_username% 加入本群！
    您的VRChat用户ID: %vrc_userid%
    已自动为您分配角色，祝您游戏愉快！
  
  leave_message: |
    用户 %vrc_username% (%vrc_userid%) 已离开群组
  
  review_request: |
    有新的入群申请需要审查：
    QQ号: %qq_user_num%
    VRChat用户ID: %vrc_userid%
    请在VRChat中确认用户信息
  
  role_assignment_failed: |
    为用户 %vrc_username% (%vrc_userid%) 分配角色失败
    失败原因: %error_reason%
    请管理员手动处理
  
  invalid_format: |
    您的入群申请格式不正确
    请提供正确的VRChat用户ID格式：usr_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  
  manual_bind_success: |
    绑定成功！
    QQ: %qq_user_num%
    VRChat: %vrc_username% (%vrc_userid%)
  
  manual_unbind_success: |
    解绑成功！
    QQ: %qq_user_num%
    VRChat: %vrc_username% (%vrc_userid%)

# 审查规则
review:
  auto_approve: true
  userid_pattern: "usr_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
  check_user_status: true
  on_role_fail: "notify_admin"

# 数据库配置
database:
  type: "json"
  file_path: "/app/data/user_bindings.json"
  backup_enabled: true
  backup_interval: 86400
EOF
    
    # 创建Dockerfile
    cat > Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .
COPY config/ ./config/

RUN mkdir -p /app/data /app/logs

EXPOSE 8080

CMD ["python", "main.py"]
EOF
    
    # 创建启动脚本
    cat > start-docker.sh << 'EOF'
#!/bin/bash
# Docker启动脚本

set -e

# 检查配置文件
if [ ! -f .env ]; then
    echo "创建环境变量文件..."
    cp .env.template .env
    echo "请编辑 .env 文件配置您的设置"
    exit 1
fi

if [ ! -f config/config.yaml ]; then
    echo "创建配置文件..."
    cp config/config.yaml.template config/config.yaml
    echo "请编辑 config/config.yaml 文件配置您的设置"
    exit 1
fi

# 加载环境变量
source .env

# 启动服务
echo "启动Docker服务..."
docker-compose up -d

echo "服务已启动！"
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
EOF
    chmod +x start-docker.sh
    
    # 创建停止脚本
    cat > stop-docker.sh << 'EOF'
#!/bin/bash
# Docker停止脚本

docker-compose down
echo "服务已停止"
EOF
    chmod +x stop-docker.sh
    
    echo -e "${GREEN}✓ Docker配置文件已创建${NC}"
    echo -e "${YELLOW}下一步:${NC}"
    echo -e "1. 编辑 .env 文件配置您的设置"
    echo -e "2. 编辑 config/config.yaml 文件配置群组信息"
    echo -e "3. 运行 ./start-docker.sh 启动服务"
}

# 源码部署
deploy_source() {
    print_step "源码部署模式"
    
    # 检查Python
    if ! command_exists python3; then
        echo -e "${RED}错误: 未安装Python 3${NC}"
        exit 1
    fi
    
    # 检查Git
    if ! command_exists git; then
        echo -e "${RED}错误: 未安装Git${NC}"
        exit 1
    fi
    
    # 克隆项目
    if [ ! -d "$PROJECT_DIR/.git" ]; then
        echo -e "${YELLOW}克隆项目...${NC}"
        git clone <repository-url> "$PROJECT_DIR"
    fi
    
    cd "$PROJECT_DIR"
    
    # 运行安装脚本
    if [ -f "install.sh" ]; then
        echo -e "${YELLOW}运行安装脚本...${NC}"
        chmod +x install.sh
        ./install.sh
    else
        echo -e "${RED}错误: 安装脚本不存在${NC}"
        exit 1
    fi
}

# 主函数
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  QQ-VRC双向绑定机器人快速部署${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    echo -e "${YELLOW}部署类型: $DEPLOY_TYPE${NC}"
    echo -e "${YELLOW}项目目录: $PROJECT_DIR${NC}"
    echo -e "${YELLOW}项目名称: $PROJECT_NAME${NC}"
    
    if [ "$DEPLOY_TYPE" = "docker" ]; then
        deploy_docker
    elif [ "$DEPLOY_TYPE" = "source" ]; then
        deploy_source
    else
        echo -e "${RED}错误: 无效的部署类型 $DEPLOY_TYPE${NC}"
        echo -e "支持的类型: docker, source"
        exit 1
    fi
    
    echo -e ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  部署完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# 解析参数并执行
parse_args "$@"
main