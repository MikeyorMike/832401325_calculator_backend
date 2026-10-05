# 后端容器镜像
#
# 构建：docker build -t calculator-backend .
# 运行：docker run -d -p 8000:8000 -e CORS_ALLOW_ORIGINS="*" calculator-backend

FROM python:3.12-slim

# 时区设置为东八区，保证历史记录里的 created_at 是本地时间
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先复制依赖清单，利用 Docker 层缓存：只要依赖没变就不会重复安装
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 再复制源码
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY run.py ./

# SQLite 数据文件目录（可用 -v 挂载出来做持久化）
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
