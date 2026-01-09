# QQ-VRC双向绑定机器人 Docker镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 复制依赖文件
COPY --chown=appuser:appuser requirements.txt .

# 安装Python依赖
RUN pip install --user --no-cache-dir -r requirements.txt

# 复制应用代码
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser main.py .
# 注意：配置文件应在运行时通过volume挂载到/data/config
# 这里不复制配置文件，使用默认配置或环境变量

# 创建必要目录
RUN mkdir -p /app/data /app/logs

# 暴露端口（如果使用Webhook）
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app'); from src.core.app import QQVRCBindingApp; print('OK')" || exit 1

# 启动命令
CMD ["python", "main.py"]