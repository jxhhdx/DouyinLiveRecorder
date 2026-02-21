#!/bin/bash
# 直播录制系统自动部署脚本

set -e

echo "🎥 直播录制自动上传系统 - 部署脚本"
echo "===================================="
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker 环境检查通过"
echo ""

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p config downloads logs aliyunpan backup_config

# 复制配置文件模板
if [ ! -f "config/URL_config.ini" ]; then
    echo "📝 创建直播间配置文件..."
    cp config/URL_config.ini.example config/URL_config.ini
    echo "   请编辑 config/URL_config.ini 添加要监控的直播间"
fi

if [ ! -f "config/config.ini" ]; then
    echo "📝 创建录制配置文件..."
    # 使用项目自带的 config.ini 作为默认配置
    echo "   使用默认录制配置（高清画质，15分钟分段）"
fi

echo ""
echo "🔨 构建 Docker 镜像..."
docker-compose build

echo ""
echo "☁️  阿里云盘登录"
echo "==============="
echo "请按提示扫码登录阿里云盘"
echo ""

# 启动临时容器进行登录
docker run --rm -it \
  -v $(pwd)/aliyunpan:/root/aliyunpan \
  douyin-live-recorder:latest \
  /usr/local/bin/aliyunpan login

echo ""
echo "🚀 启动服务..."
docker-compose up -d

echo ""
echo "✅ 部署完成！"
echo "==============="
echo ""
echo "查看录制日志: docker-compose logs -f recorder"
echo "查看上传日志: docker-compose logs -f uploader"
echo ""
echo "配置文件:"
echo "  - 直播间列表: config/URL_config.ini"
echo "  - 录制设置:   config/config.ini"
echo ""
