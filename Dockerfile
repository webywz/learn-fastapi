# ============================================================
# FastAPI 应用 Docker 镜像
# ============================================================
#
# 多阶段构建：
# - 第一阶段：构建依赖
# - 第二阶段：运行应用
#
# 优点：
# - 镜像体积小
# - 安全性高
# - 构建速度快

# ============================================================
# 第一阶段：基础镜像
# ============================================================
FROM python:3.11-slim as base

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# 第二阶段：安装 Python 依赖
# ============================================================
FROM base as builder

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --user -r requirements.txt

# ============================================================
# 第三阶段：最终镜像
# ============================================================
FROM base as final

# 从 builder 阶段复制已安装的包
COPY --from=builder /root/.local /root/.local

# 将 .local/bin 添加到 PATH
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码
COPY . .

# 创建非 root 用户（安全性）
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/')"

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
