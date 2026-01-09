#!/bin/bash
# QQ-VRC双向绑定机器人安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  QQ-VRC双向绑定机器人安装脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查Python版本
check_python() {
    echo -e "${YELLOW}检查Python版本...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        echo -e "${GREEN}✓ 找到Python 3.${NC} 版本: $PYTHON_VERSION"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if [[ ${PYTHON_VERSION%%.*} -eq 3 ]]; then
            echo -e "${GREEN}✓ 找到Python 3.${NC} 版本: $PYTHON_VERSION"
            PYTHON_CMD="python"
        else
            echo -e "${RED}✗ 需要Python 3.7或更高版本${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ 未找到Python${NC}"
        exit 1
    fi
}

# 检查pip
check_pip() {
    echo -e "${YELLOW}检查pip...${NC}"
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
        echo -e "${GREEN}✓ 找到pip3${NC}"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
        echo -e "${GREEN}✓ 找到pip${NC}"
    else
        echo -e "${RED}✗ 未找到pip${NC}"
        exit 1
    fi
}

# 创建虚拟环境
create_venv() {
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    if [ ! -d "$PROJECT_DIR/venv" ]; then
        $PYTHON_CMD -m venv "$PROJECT_DIR/venv"
        echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"
    else
        echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
    fi
}

# 激活虚拟环境
activate_venv() {
    echo -e "${YELLOW}激活虚拟环境...${NC}"
    source "$PROJECT_DIR/venv/bin/activate"
    echo -e "${GREEN}✓ 虚拟环境已激活${NC}"
}

# 安装依赖
install_dependencies() {
    echo -e "${YELLOW}安装Python依赖...${NC}"
    $PIP_CMD install --upgrade pip
    $PIP_CMD install -r "$PROJECT_DIR/requirements.txt"
    echo -e "${GREEN}✓ 依赖安装完成${NC}"
}

# 创建必要目录
create_directories() {
    echo -e "${YELLOW}创建必要目录...${NC}"
    mkdir -p "$PROJECT_DIR/data"
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/config"
    echo -e "${GREEN}✓ 目录创建完成${NC}"
}

# 配置文件设置
setup_config() {
    echo -e "${YELLOW}配置文件设置...${NC}"
    
    if [ ! -f "$PROJECT_DIR/config/config.yaml" ]; then
        if [ -f "$PROJECT_DIR/config/config.yaml.example" ]; then
            cp "$PROJECT_DIR/config/config.yaml.example" "$PROJECT_DIR/config/config.yaml"
            echo -e "${GREEN}✓ 配置文件已创建${NC}"
            echo -e "${YELLOW}请编辑 config/config.yaml 文件来配置您的设置${NC}"
        else
            echo -e "${RED}✗ 配置文件模板不存在${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ 配置文件已存在${NC}"
    fi
    
    # 环境变量文件
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
            echo -e "${GREEN}✓ 环境变量文件已创建${NC}"
            echo -e "${YELLOW}请编辑 .env 文件来设置敏感信息${NC}"
        fi
    else
        echo -e "${GREEN}✓ 环境变量文件已存在${NC}"
    fi
}

# 检查Napcat
check_napcat() {
    echo -e "${YELLOW}检查Napcat...${NC}"
    if command -v napcat &> /dev/null; then
        echo -e "${GREEN}✓ Napcat已安装${NC}"
        NAPCAT_VERSION=$(napcat --version 2>&1 || echo "未知版本")
        echo -e "  版本: $NAPCAT_VERSION"
    else
        echo -e "${YELLOW}! Napcat未安装${NC}"
        echo -e "${YELLOW}  请按照Napcat文档安装: https://github.com/NapNeko/NapCatQQ${NC}"
    fi
}

# 创建系统服务
create_systemd_service() {
    echo -e "${YELLOW}创建系统服务...${NC}"
    
    read -p "是否创建systemd服务? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}跳过创建系统服务${NC}"
        return
    fi
    
    # 检查是否为root用户
    if [[ $EUID -ne 0 ]]; then
        echo -e "${YELLOW}需要root权限创建系统服务${NC}"
        sudo -E "$0" --create-service
        return
    fi
    
    cat > /etc/systemd/system/qq-vrc-bot.service << EOF
[Unit]
Description=QQ-VRC双向绑定机器人
After=network.target
Wants=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    echo -e "${GREEN}✓ 系统服务已创建${NC}"
    echo -e "${YELLOW}使用以下命令管理服务:${NC}"
    echo -e "  启动: sudo systemctl start qq-vrc-bot"
    echo -e "  停止: sudo systemctl stop qq-vrc-bot"
    echo -e "  重启: sudo systemctl restart qq-vrc-bot"
    echo -e "  状态: sudo systemctl status qq-vrc-bot"
    echo -e "  开机自启: sudo systemctl enable qq-vrc-bot"
}

# 创建启动脚本
create_startup_scripts() {
    echo -e "${YELLOW}创建启动脚本...${NC}"
    
    # 启动脚本
    cat > "$PROJECT_DIR/start.sh" << 'EOF'
#!/bin/bash
# QQ-VRC双向绑定机器人启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 启动应用
python main.py "$@"
EOF
    chmod +x "$PROJECT_DIR/start.sh"
    
    # CLI模式启动脚本
    cat > "$PROJECT_DIR/cli.sh" << 'EOF'
#!/bin/bash
# QQ-VRC双向绑定机器人CLI模式启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 启动CLI模式
python main.py --cli "$@"
EOF
    chmod +x "$PROJECT_DIR/cli.sh"
    
    echo -e "${GREEN}✓ 启动脚本已创建${NC}"
}

# 显示配置向导
show_config_wizard() {
    echo -e "${YELLOW}配置向导${NC}"
    echo -e "=========="
    echo -e "1. 编辑配置文件: ${GREEN}nano $PROJECT_DIR/config/config.yaml${NC}"
    echo -e "2. 编辑环境变量: ${GREEN}nano $PROJECT_DIR/.env${NC}"
    echo -e "3. 启动应用测试: ${GREEN}./cli.sh${NC}"
    echo -e "4. 查看日志: ${GREEN}tail -f logs/app.log${NC}"
    echo -e ""
    echo -e "${YELLOW}必要配置项:${NC}"
    echo -e "- VRChat用户名和密码"
    echo -e "- QQ群号和VRChat群组ID"
    echo -e "- Napcat服务器地址和端口"
}

# 主安装流程
main() {
    echo -e "${GREEN}开始安装...${NC}"
    
    check_python
    check_pip
    check_napcat
    create_directories
    create_venv
    activate_venv
    install_dependencies
    setup_config
    create_startup_scripts
    
    # 检查是否需要创建系统服务
    if [[ "$1" == "--create-service" ]]; then
        create_systemd_service
    else
        read -p "是否创建systemd服务以便后台运行? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            create_systemd_service
        fi
    fi
    
    echo -e ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  安装完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    show_config_wizard
}

# 卸载
uninstall() {
    echo -e "${YELLOW}卸载QQ-VRC双向绑定机器人...${NC}"
    
    # 停止服务
    if systemctl is-active --quiet qq-vrc-bot; then
        sudo systemctl stop qq-vrc-bot
        echo -e "${GREEN}✓ 服务已停止${NC}"
    fi
    
    # 禁用服务
    if systemctl is-enabled --quiet qq-vrc-bot; then
        sudo systemctl disable qq-vrc-bot
        echo -e "${GREEN}✓ 服务已禁用${NC}"
    fi
    
    # 删除服务文件
    if [ -f /etc/systemd/system/qq-vrc-bot.service ]; then
        sudo rm /etc/systemd/system/qq-vrc-bot.service
        sudo systemctl daemon-reload
        echo -e "${GREEN}✓ 服务文件已删除${NC}"
    fi
    
    echo -e "${GREEN}卸载完成！${NC}"
}

# 显示帮助
show_help() {
    echo -e "${GREEN}QQ-VRC双向绑定机器人安装脚本${NC}"
    echo -e ""
    echo -e "用法:"
    echo -e "  ./install.sh                    # 安装应用"
    echo -e "  ./install.sh --uninstall        # 卸载应用"
    echo -e "  ./install.sh --help             # 显示帮助"
    echo -e ""
    echo -e "选项:"
    echo -e "  --create-service    创建systemd服务"
    echo -e "  --uninstall        卸载应用"
    echo -e "  --help            显示帮助信息"
}

# 处理命令行参数
case "${1:-}" in
    --uninstall)
        uninstall
        ;;
    --help)
        show_help
        ;;
    --create-service)
        create_systemd_service
        ;;
    *)
        main "$@"
        ;;
esac