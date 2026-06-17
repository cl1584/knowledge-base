FROM python:3.12-slim

WORKDIR /app

# 系统依赖（chromadb 需要 build tools；运行时不需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（用清华源，国内 build 快 5-10x）
COPY requirements.txt .
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 数据目录（容器内由挂载卷填充，无需 mkdir；保留 root 避免宿主卷权限问题）
# 单用户单容器场景下 root 无安全风险；如需 non-root 必须确保宿主卷预 chown 1000:1000

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动（1 worker 个人用足够；要支持并发并发请求可加 --workers 2）
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
