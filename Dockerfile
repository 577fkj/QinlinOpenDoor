# 使用包含 Node.js 的 Python 镜像
FROM python:3.13

# 安装 Node.js 和 npm
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制前端文件并构建
COPY web ./web
WORKDIR /app/web
RUN npm config set registry https://registry.npmmirror.com
RUN npm install
RUN npm run build

# 复制后端文件
WORKDIR /app
COPY requirements.txt ./
COPY run.py ./
COPY app ./app

# 创建配置目录（用于挂载）
RUN mkdir -p config

# 安装 Python 依赖
RUN pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple
RUN pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple

EXPOSE 5000

CMD ["python3", "run.py"]