#!/bin/bash
# 查看日志

case "$1" in
  recorder|r)
    docker-compose logs -f recorder
    ;;
  uploader|u)
    docker-compose logs -f uploader
    ;;
  *)
    echo "用法: ./logs.sh [recorder|r|uploader|u]"
    echo ""
    echo "示例:"
    echo "  ./logs.sh recorder  # 查看录制日志"
    echo "  ./logs.sh uploader  # 查看上传日志"
    exit 1
    ;;
esac
