# Docker 和 Nginx 完整学习指南

## 目录

### Docker 部分
1. [什么是 Docker](#什么是-docker)
2. [为什么需要 Docker](#为什么需要-docker)
3. [Docker 核心概念](#docker-核心概念)
4. [Dockerfile 详解](#dockerfile-详解)
5. [Docker Compose 详解](#docker-compose-详解)
6. [Docker 命令大全](#docker-命令大全)
7. [Docker 最佳实践](#docker-最佳实践)

### Nginx 部分
8. [什么是 Nginx](#什么是-nginx)
9. [为什么需要 Nginx](#为什么需要-nginx)
10. [Nginx 核心概念](#nginx-核心概念)
11. [Nginx 配置详解](#nginx-配置详解)
12. [反向代理配置](#反向代理配置)
13. [Nginx 最佳实践](#nginx-最佳实践)

### 实战部分
14. [实战示例](#实战示例)
15. [常见问题](#常见问题)

---

# Docker 部分

## 什么是 Docker？

**Docker** 是一个开源的容器化平台，用于打包、分发和运行应用程序。

### 核心理念

```
传统方式：应用 + 依赖 → 直接安装到服务器
Docker 方式：应用 + 依赖 + 环境 → 打包成镜像 → 运行成容器
```

### 类比前端

**类似 npm/pnpm 的作用**：

```javascript
// 前端：package.json 定义依赖
{
  "dependencies": {
    "react": "^18.0.0",
    "axios": "^1.0.0"
  }
}

// npm install → 安装依赖
```

```dockerfile
# Docker：Dockerfile 定义环境和依赖
FROM node:18
COPY package.json .
RUN npm install
COPY . .
CMD ["npm", "start"]

# docker build → 构建镜像
# docker run → 运行容器
```

**区别**：
- npm 只管理 JavaScript 包
- Docker 管理整个运行环境（操作系统、运行时、应用）

---

## 为什么需要 Docker？

### 问题 1: "在我电脑上能跑" 😅

```
开发环境：Python 3.11 + SQLite + Redis 6
测试环境：Python 3.10 + MySQL + Redis 7
生产环境：Python 3.9 + PostgreSQL + Redis 5

结果：三个环境都有不同的问题！
```

**Docker 解决**：
```
所有环境运行同一个 Docker 镜像
→ 开发、测试、生产完全一致
→ 再也不会有"在我电脑上能跑"的问题
```

### 问题 2: 环境配置复杂

```bash
# 传统方式（手动安装）
# 1. 安装 Python
# 2. 安装 Redis
# 3. 安装 PostgreSQL
# 4. 配置环境变量
# 5. 安装依赖
# 6. ...（50 步）

# Docker 方式
docker-compose up -d  # 一键启动所有服务
```

### 问题 3: 多版本冲突

```
项目 A 需要 Python 3.9
项目 B 需要 Python 3.11
项目 C 需要 Node.js 16
项目 D 需要 Node.js 18

传统方式：版本管理工具（pyenv, nvm）
Docker 方式：每个项目独立容器，互不影响
```

### 问题 4: 资源隔离

```
传统方式：所有应用共享系统资源
Docker 方式：每个容器独立隔离
- 内存限制
- CPU 限制
- 磁盘限制
```

---

## Docker 核心概念

### 1. 镜像 (Image)

**定义**：只读的模板，包含运行应用所需的一切

**类比**：
- 镜像 = 类（Class）
- 容器 = 实例（Instance）

```
镜像（Image）          容器（Container）
   ↓                      ↓
   类                    对象
   模板                   实例
   静态                   运行中
```

**示例**：
```bash
# 查看镜像
docker images

# 输出：
# REPOSITORY    TAG       IMAGE ID       SIZE
# python        3.11      abc123         900MB
# nginx         alpine    def456         20MB
# redis         7         ghi789         100MB
```

### 2. 容器 (Container)

**定义**：镜像的运行实例

**特点**：
- 轻量级（共享宿主机内核）
- 隔离性（独立的文件系统、网络）
- 可移植（任何地方运行）

```bash
# 从镜像创建并运行容器
docker run -d --name my_app python:3.11

# 查看运行中的容器
docker ps

# 输出：
# CONTAINER ID   IMAGE          COMMAND       STATUS
# abc123         python:3.11    "python..."   Up 2 hours
```

### 3. 数据卷 (Volume)

**定义**：持久化数据存储

**为什么需要**：
- 容器删除后，数据也会丢失
- Volume 让数据独立于容器生命周期

```bash
# 创建数据卷
docker volume create my_data

# 挂载数据卷
docker run -v my_data:/app/data python:3.11
```

**类比前端 localStorage**：
```javascript
// 前端：localStorage 持久化数据
localStorage.setItem('user', 'Alice');

// Docker：Volume 持久化容器数据
docker run -v db_data:/var/lib/mysql mysql
```

### 4. 网络 (Network)

**定义**：容器之间的通信方式

```
容器 A (app)  ←→  容器 B (redis)  ←→  容器 C (postgres)
     ↓                  ↓                    ↓
   同一个网络（bridge）
```

**示例**：
```bash
# 创建网络
docker network create my_network

# 容器加入网络
docker run --network my_network --name app fastapi_app
docker run --network my_network --name db postgres

# 容器内访问：
# app 可以通过 "db" 这个名字访问数据库
```

---

## Dockerfile 详解

**Dockerfile**：定义如何构建镜像的脚本

### 基本结构

```dockerfile
# 1. 基础镜像
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制文件
COPY requirements.txt .

# 4. 安装依赖
RUN pip install -r requirements.txt

# 5. 复制应用代码
COPY . .

# 6. 暴露端口
EXPOSE 8080

# 7. 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### 常用指令

#### FROM - 基础镜像

```dockerfile
# 完整版（包含所有工具）
FROM python:3.11

# 精简版（推荐，体积小）
FROM python:3.11-slim

# 超精简版（最小体积）
FROM python:3.11-alpine
```

#### WORKDIR - 工作目录

```dockerfile
# 设置工作目录（相当于 cd）
WORKDIR /app

# 后续命令都在 /app 目录执行
RUN pip install ...
COPY . .
```

#### COPY vs ADD

```dockerfile
# COPY：简单复制文件
COPY requirements.txt /app/

# ADD：复制 + 自动解压（不推荐）
ADD archive.tar.gz /app/

# 推荐：只用 COPY
```

#### RUN vs CMD vs ENTRYPOINT

```dockerfile
# RUN：构建时执行（安装依赖）
RUN pip install flask

# CMD：容器启动时执行（可被覆盖）
CMD ["python", "app.py"]

# ENTRYPOINT：容器启动时执行（不可被覆盖）
ENTRYPOINT ["python", "app.py"]
```

**区别**：
```bash
# CMD 可以被覆盖
docker run my_image python other.py  # 执行 other.py

# ENTRYPOINT 不可被覆盖
docker run my_image other.py  # 仍然执行 app.py，other.py 作为参数
```

#### ENV - 环境变量

```dockerfile
# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBUG=False

# 等价于 export
```

#### EXPOSE - 暴露端口

```dockerfile
# 声明容器监听的端口（文档作用）
EXPOSE 8080

# 注意：仍需要 -p 映射端口
docker run -p 8080:8080 my_image
```

### 多阶段构建

**问题**：镜像体积大（包含构建工具）

**解决**：多阶段构建

```dockerfile
# ============================================================
# 第一阶段：构建
# ============================================================
FROM python:3.11 as builder

WORKDIR /app
COPY requirements.txt .

# 安装依赖到用户目录
RUN pip install --user -r requirements.txt

# ============================================================
# 第二阶段：运行
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# 只复制已安装的包（不包含构建工具）
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY . .

ENV PATH=/root/.local/bin:$PATH

CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

**优势**：
```
单阶段：1.2 GB
多阶段：300 MB

减少 75% 体积！
```

---

## Docker Compose 详解

**Docker Compose**：管理多容器应用的工具

### 为什么需要 Compose？

**问题**：
```bash
# 手动启动每个容器（太繁琐）
docker run -d --name redis redis
docker run -d --name db postgres
docker run -d --name app \
  --link redis \
  --link db \
  -p 8080:8080 \
  my_app
```

**解决**：
```yaml
# docker-compose.yml（一键启动）
version: '3.8'

services:
  redis:
    image: redis

  db:
    image: postgres

  app:
    build: .
    ports:
      - "8080:8080"
    depends_on:
      - redis
      - db
```

```bash
# 一键启动所有服务
docker-compose up -d
```

### 完整示例

```yaml
version: '3.8'

services:
  # ----------------------------------------------------------
  # Redis 服务
  # ----------------------------------------------------------
  redis:
    image: redis:7-alpine
    container_name: my_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - app_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  # ----------------------------------------------------------
  # FastAPI 应用
  # ----------------------------------------------------------
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: my_app
    ports:
      - "8080:8080"
    volumes:
      - .:/app
    environment:
      - REDIS_HOST=redis
      - DEBUG=True
    depends_on:
      - redis
    networks:
      - app_network
    restart: unless-stopped

# ----------------------------------------------------------
# 网络配置
# ----------------------------------------------------------
networks:
  app_network:
    driver: bridge

# ----------------------------------------------------------
# 数据卷配置
# ----------------------------------------------------------
volumes:
  redis_data:
```

### 关键配置项

#### image vs build

```yaml
# 使用现成镜像
services:
  redis:
    image: redis:7

# 构建自定义镜像
services:
  app:
    build: .  # 使用当前目录的 Dockerfile
```

#### ports - 端口映射

```yaml
services:
  app:
    ports:
      - "8080:8080"  # 宿主机:容器
      - "8000:8080"  # 可以映射到不同端口
```

#### volumes - 数据卷

```yaml
services:
  app:
    volumes:
      # 命名卷（持久化）
      - db_data:/var/lib/mysql

      # 绑定挂载（开发时）
      - .:/app

      # 只读挂载
      - ./config:/app/config:ro

volumes:
  db_data:  # 声明命名卷
```

#### environment - 环境变量

```yaml
services:
  app:
    environment:
      # 方式1：直接定义
      - DEBUG=True
      - REDIS_HOST=redis

      # 方式2：从 .env 文件读取
      - DATABASE_URL=${DATABASE_URL}
```

#### depends_on - 依赖关系

```yaml
services:
  app:
    depends_on:
      - redis
      - db
    # app 会在 redis 和 db 启动后再启动
```

**注意**：只保证启动顺序，不保证服务就绪

#### restart - 重启策略

```yaml
services:
  app:
    restart: unless-stopped
    # no: 不自动重启
    # always: 总是重启
    # on-failure: 失败时重启
    # unless-stopped: 除非手动停止，否则总是重启
```

#### healthcheck - 健康检查

```yaml
services:
  db:
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 10s  # 每 10 秒检查一次
      timeout: 5s    # 超时时间
      retries: 3     # 重试次数
      start_period: 30s  # 启动后等待 30 秒再检查
```

---

## Docker 命令大全

### 镜像管理

```bash
# 查看镜像列表
docker images

# 构建镜像
docker build -t my_image:latest .

# 删除镜像
docker rmi my_image

# 拉取镜像
docker pull python:3.11

# 推送镜像（到 Docker Hub）
docker push username/my_image:latest

# 清理未使用的镜像
docker image prune -a
```

### 容器管理

```bash
# 运行容器
docker run -d --name my_app my_image

# 查看运行中的容器
docker ps

# 查看所有容器（包括停止的）
docker ps -a

# 停止容器
docker stop my_app

# 启动容器
docker start my_app

# 重启容器
docker restart my_app

# 删除容器
docker rm my_app

# 删除所有停止的容器
docker container prune
```

### 日志和调试

```bash
# 查看容器日志
docker logs my_app

# 实时查看日志
docker logs -f my_app

# 查看最近 100 行
docker logs --tail 100 my_app

# 进入容器（交互式）
docker exec -it my_app bash

# 在容器中执行命令
docker exec my_app python manage.py migrate

# 查看容器详情
docker inspect my_app

# 查看容器资源使用
docker stats my_app
```

### Compose 命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
docker-compose logs -f app  # 单个服务

# 重启服务
docker-compose restart app

# 重新构建
docker-compose up -d --build

# 执行命令
docker-compose exec app python manage.py shell

# 查看资源使用
docker-compose stats
```

---

## Docker 最佳实践

### 1. 使用精简基础镜像

```dockerfile
# ❌ 不推荐（体积大）
FROM python:3.11

# ✅ 推荐（体积小）
FROM python:3.11-slim

# 体积对比：
# python:3.11 → 900MB
# python:3.11-slim → 120MB
```

### 2. 利用缓存层

```dockerfile
# ✅ 推荐顺序（依赖变化少，代码变化多）
COPY requirements.txt .
RUN pip install -r requirements.txt  # 缓存
COPY . .  # 经常变化

# ❌ 不推荐（每次都重新安装依赖）
COPY . .
RUN pip install -r requirements.txt
```

### 3. 合并 RUN 命令

```dockerfile
# ❌ 每个 RUN 都是一层
RUN apt-get update
RUN apt-get install -y gcc
RUN apt-get clean

# ✅ 合并成一层
RUN apt-get update && \
    apt-get install -y gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

### 4. 使用 .dockerignore

```
# .dockerignore
.git
__pycache__
*.pyc
.env
node_modules
.vscode
```

### 5. 非 root 用户运行

```dockerfile
# 创建非 root 用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 切换用户
USER appuser

# 安全性更高
```

### 6. 健康检查

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

### 7. 环境变量管理

```yaml
# docker-compose.yml
services:
  app:
    env_file:
      - .env.production  # 从文件加载

# 不要在镜像中硬编码敏感信息
```

---

# Nginx 部分

## 什么是 Nginx？

**Nginx**（发音 "engine-x"）是一个高性能的 HTTP 服务器和反向代理服务器。

### 核心功能

1. **Web 服务器** - 提供静态文件（HTML, CSS, JS, 图片）
2. **反向代理** - 转发请求到后端服务器
3. **负载均衡** - 分发请求到多台服务器
4. **缓存** - 缓存静态内容，提高性能
5. **HTTPS** - SSL/TLS 加密

### 类比前端

**类似前端的什么？**

Nginx 就像前端的 **Webpack Dev Server** 或 **Vite**：

```
前端开发：
浏览器 → Vite Dev Server → React 应用

生产环境：
浏览器 → Nginx → FastAPI 应用
```

---

## 为什么需要 Nginx？

### 问题 1: 静态文件服务

```python
# ❌ FastAPI 提供静态文件（慢）
@app.get("/static/{file_path}")
async def serve_static(file_path: str):
    return FileResponse(f"static/{file_path}")

# ✅ Nginx 提供静态文件（快 10 倍）
location /static/ {
    alias /app/static/;
}
```

### 问题 2: 反向代理

**反向代理 vs 正向代理**：

```
正向代理（VPN）：
客户端 → 代理 → 服务器
（隐藏客户端）

反向代理（Nginx）：
客户端 → 代理 → 后端服务器
（隐藏服务器）
```

**好处**：
- 隐藏后端服务器 IP
- 负载均衡
- 缓存
- SSL 终止

### 问题 3: 负载均衡

```
单机：
客户端 → FastAPI（处理 100 req/s）

负载均衡：
              ┌→ FastAPI 1 (100 req/s)
客户端 → Nginx ┼→ FastAPI 2 (100 req/s)
              └→ FastAPI 3 (100 req/s)
总处理能力：300 req/s
```

### 问题 4: HTTPS

```
FastAPI 配置 HTTPS：复杂
Nginx 配置 HTTPS：简单

nginx.conf:
ssl_certificate /path/to/cert.pem;
ssl_certificate_key /path/to/key.pem;
```

---

## Nginx 核心概念

### 1. 配置文件结构

```nginx
# nginx.conf
http {
    # 全局 HTTP 配置

    server {
        # 虚拟主机 1
        listen 80;
        server_name example.com;

        location / {
            # 路由 1
        }

        location /api/ {
            # 路由 2
        }
    }

    server {
        # 虚拟主机 2
        listen 443 ssl;
        server_name example.com;
    }
}
```

**层级关系**：
```
http 块
├── server 块（虚拟主机）
│   ├── location 块（路由）
│   └── location 块
└── server 块
    └── location 块
```

### 2. 指令（Directive）

```nginx
# 简单指令（以 ; 结尾）
listen 80;
server_name example.com;

# 块指令（包含 {}）
server {
    location / {
        root /var/www/html;
    }
}
```

### 3. 上下文（Context）

- **main**: 全局配置
- **events**: 连接处理
- **http**: HTTP 配置
- **server**: 虚拟主机
- **location**: URL 路由

### 4. 变量

```nginx
# 内置变量
$host          # 请求的主机名
$uri           # 请求的 URI
$args          # 查询参数
$remote_addr   # 客户端 IP
$request_method  # HTTP 方法

# 使用示例
location / {
    return 200 "Host: $host, URI: $uri";
}
```

---

## Nginx 配置详解

### 基本配置

```nginx
# nginx.conf
user nginx;
worker_processes auto;  # 工作进程数（自动 = CPU 核心数）

events {
    worker_connections 1024;  # 每个进程最大连接数
}

http {
    include mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $request - $status';
    access_log /var/log/nginx/access.log main;

    # Gzip 压缩
    gzip on;
    gzip_types text/css application/json;

    # 包含站点配置
    include /etc/nginx/conf.d/*.conf;
}
```

### Server 块配置

```nginx
server {
    listen 80;  # 监听端口
    server_name example.com www.example.com;  # 域名

    # 字符集
    charset utf-8;

    # 访问日志
    access_log /var/log/nginx/example.log;

    # 根路径
    location / {
        root /var/www/html;
        index index.html;
    }
}
```

### Location 匹配规则

```nginx
# 1. 精确匹配（优先级最高）
location = /api/users {
    # 只匹配 /api/users
}

# 2. 前缀匹配
location ^~ /static/ {
    # 匹配 /static/* 且停止正则匹配
}

# 3. 正则匹配（区分大小写）
location ~ \.php$ {
    # 匹配 .php 结尾
}

# 4. 正则匹配（不区分大小写）
location ~* \.(jpg|png|gif)$ {
    # 匹配图片文件
}

# 5. 通用匹配（优先级最低）
location / {
    # 匹配所有
}
```

**匹配顺序**：
```
1. = 精确匹配
2. ^~ 前缀匹配
3. ~ 或 ~* 正则匹配（按顺序）
4. / 通用匹配
```

**示例**：
```nginx
# URL: /static/image.jpg

location = /static/image.jpg { }  # ✅ 匹配（精确）
location ^~ /static/ { }          # ✅ 匹配（前缀）
location ~* \.(jpg|png)$ { }      # ✅ 匹配（正则）
location / { }                     # ✅ 匹配（通用）

# 实际使用：精确匹配优先
```

---

## 反向代理配置

### 基本反向代理

```nginx
# 定义后端服务器组
upstream backend {
    server app:8080;
}

server {
    listen 80;

    location /api/ {
        # 代理到后端
        proxy_pass http://backend;

        # 转发原始请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 负载均衡

```nginx
# 轮询（默认）
upstream backend {
    server app1:8080;
    server app2:8080;
    server app3:8080;
}

# 权重
upstream backend {
    server app1:8080 weight=3;  # 60% 流量
    server app2:8080 weight=2;  # 40% 流量
}

# 最少连接
upstream backend {
    least_conn;
    server app1:8080;
    server app2:8080;
}

# IP 哈希（会话保持）
upstream backend {
    ip_hash;
    server app1:8080;
    server app2:8080;
}
```

### WebSocket 代理

```nginx
location /ws/ {
    proxy_pass http://backend;

    # WebSocket 必需配置
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # 长连接超时
    proxy_read_timeout 86400;
}
```

### 静态文件 + 反向代理

```nginx
server {
    listen 80;

    # 静态文件（Nginx 直接提供）
    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API 请求（代理到 FastAPI）
    location /api/ {
        proxy_pass http://backend;
    }

    # 前端 SPA（React/Vue）
    location / {
        root /app/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## Nginx 最佳实践

### 1. Gzip 压缩

```nginx
http {
    gzip on;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/javascript
        application/json
        application/javascript;
}
```

### 2. 缓存控制

```nginx
# 静态文件长缓存
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# HTML 文件不缓存
location ~ \.html$ {
    expires -1;
    add_header Cache-Control "no-cache, no-store, must-revalidate";
}
```

### 3. 安全配置

```nginx
# 隐藏 Nginx 版本号
server_tokens off;

# 限制请求体大小
client_max_body_size 10M;

# 防止点击劫持
add_header X-Frame-Options "SAMEORIGIN";

# XSS 保护
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
```

### 4. 限流

```nginx
# 定义限流区域
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# 应用限流
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    proxy_pass http://backend;
}
```

### 5. HTTPS 配置

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # SSL 证书
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # SSL 协议
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000" always;
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 实战示例

### 示例 1: FastAPI + React 部署

**架构**：
```
浏览器
   ↓
Nginx (80/443)
   ├→ /api/* → FastAPI (8080)
   ├→ /static/* → 静态文件
   └→ /* → React SPA
```

**配置**：
```nginx
upstream fastapi_backend {
    server app:8080;
}

server {
    listen 80;
    server_name example.com;

    # React 前端
    location / {
        root /app/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 前端静态资源
    location /assets/ {
        alias /app/frontend/dist/assets/;
        expires 1y;
    }

    # API 请求
    location /api/ {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API 文档
    location /docs {
        proxy_pass http://fastapi_backend;
    }
}
```

### 示例 2: 多服务部署

```
Nginx (80)
   ├→ /app1/* → Service 1 (8001)
   ├→ /app2/* → Service 2 (8002)
   └→ /app3/* → Service 3 (8003)
```

```nginx
upstream service1 {
    server app1:8001;
}

upstream service2 {
    server app2:8002;
}

upstream service3 {
    server app3:8003;
}

server {
    listen 80;

    location /app1/ {
        proxy_pass http://service1/;
    }

    location /app2/ {
        proxy_pass http://service2/;
    }

    location /app3/ {
        proxy_pass http://service3/;
    }
}
```

---

## 常见问题

### Q1: 502 Bad Gateway

**原因**：
- 后端服务未启动
- 后端服务地址错误
- 防火墙阻止

**排查**：
```bash
# 检查后端服务
docker-compose ps app

# 检查 Nginx 配置
docker-compose exec nginx nginx -t

# 查看 Nginx 日志
docker-compose logs nginx

# 查看后端日志
docker-compose logs app
```

### Q2: 413 Request Entity Too Large

**原因**：上传文件过大

**解决**：
```nginx
http {
    client_max_body_size 100M;  # 允许 100MB
}
```

### Q3: 跨域问题（CORS）

**解决**：
```nginx
location /api/ {
    # 允许跨域
    add_header Access-Control-Allow-Origin *;
    add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
    add_header Access-Control-Allow-Headers "Authorization, Content-Type";

    # OPTIONS 预检请求
    if ($request_method = 'OPTIONS') {
        return 204;
    }

    proxy_pass http://backend;
}
```

**更好的方案**：在 FastAPI 中配置 CORS
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Q4: WebSocket 连接失败

**解决**：
```nginx
location /ws/ {
    proxy_pass http://backend;

    # 必需配置
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    # 超时配置
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;
}
```

### Q5: 如何重载配置不停机

```bash
# 测试配置是否正确
nginx -t

# 重载配置（不停机）
nginx -s reload

# Docker Compose 环境
docker-compose exec nginx nginx -s reload
```

---

## 总结

### Docker 核心要点

1. **镜像 vs 容器**
   - 镜像 = 类，容器 = 实例
   - 镜像只读，容器可写

2. **Dockerfile 最佳实践**
   - 使用精简基础镜像
   - 利用缓存层
   - 多阶段构建

3. **Docker Compose**
   - 管理多容器应用
   - 一键启动所有服务

4. **数据持久化**
   - Volume 持久化数据
   - 数据独立于容器生命周期

### Nginx 核心要点

1. **核心功能**
   - 反向代理
   - 负载均衡
   - 静态文件服务
   - HTTPS

2. **配置结构**
   - http → server → location
   - 精确匹配 > 前缀匹配 > 正则匹配

3. **反向代理**
   - 隐藏后端服务器
   - 负载均衡
   - 缓存优化

4. **最佳实践**
   - Gzip 压缩
   - 缓存控制
   - 安全配置
   - 限流

### 快速开始

```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 查看状态
docker-compose ps

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

**访问地址**：
- FastAPI: http://localhost:8080
- API 文档: http://localhost:8080/docs
- Nginx 代理: http://localhost
- Flower: http://localhost:5555

Docker + Nginx 让部署变得简单、可靠、高效！🚀
