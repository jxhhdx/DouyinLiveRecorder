FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y curl gnupg wget && \
    curl -sL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# 安装 FFmpeg 和时区设置
RUN apt-get update && \
    apt-get install -y ffmpeg tzdata && \
    ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# 安装 aliyunpan CLI
RUN cd /tmp && \
    wget https://github.com/tickstep/aliyunpan/releases/download/v0.3.8/aliyunpan-v0.3.8-linux-amd64.zip && \
    unzip aliyunpan-v0.3.8-linux-amd64.zip && \
    mv aliyunpan-v0.3.8-linux-amd64/aliyunpan /usr/local/bin/aliyunpan && \
    chmod +x /usr/local/bin/aliyunpan && \
    rm -rf aliyunpan-v0.3.8-linux-amd64*

# 复制项目代码
COPY . /app

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要目录
RUN mkdir -p /app/downloads /app/logs /app/config

# 默认命令
CMD ["python", "main.py"]
