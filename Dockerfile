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

# 复制前端构建所需文件
COPY package.json package-lock.json* ./
COPY vite.config.js ./
COPY build-post.js ./
COPY src ./src
COPY public ./public

# 安装 npm 依赖并构建前端
RUN npm config set registry https://registry.npmmirror.com
RUN npm install
RUN npm run build

# 复制 Python 相关文件
COPY requirements.txt ./
COPY server.py ./
COPY qinlinAPI.py ./
COPY config ./config

# 安装 Python 依赖
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

EXPOSE 5000

CMD ["python3", "server.py"]