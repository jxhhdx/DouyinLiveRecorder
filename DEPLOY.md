# 🎥 直播录制自动上传系统 - Docker 部署指南

一站式直播录制 + 自动上传阿里云盘解决方案

## ✨ 功能特性

- 📹 **自动录制**: 支持抖音、快手等多个直播平台
- ☁️ **自动上传**: 录制完成后自动上传至阿里云盘
- 🗑️ **自动清理**: 上传成功后自动删除本地文件，节省磁盘空间
- 📧 **邮件通知**: 上传成功/失败邮件提醒（可选）
- 🐳 **Docker 部署**: 一键启动，易于维护

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/DouyinLiveRecorder.git
cd DouyinLiveRecorder
```

### 2. 配置直播间

```bash
# 复制配置文件模板
cp config/URL_config.ini.example config/URL_config.ini

# 编辑配置文件，添加要监控的直播间
vi config/URL_config.ini
```

配置文件格式：
```ini
# 抖音直播
https://live.douyin.com/93777291150,主播: 幻瞳

# 快手直播
https://live.kuaishou.com/u/3x7cff8hm8b9uwi,主播: 骚白
```

### 3. 阿里云盘登录

```bash
# 启动临时容器进行登录
docker run --rm -it \
  -v $(pwd)/aliyunpan:/root/aliyunpan \
  douyin-live-recorder:latest \
  /usr/local/bin/aliyunpan login

# 按提示扫码登录
```

### 4. 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f recorder
docker-compose logs -f uploader
```

## ⚙️ 详细配置

### 录制配置 (config/config.ini)

```ini
[录制设置]
# 视频质量: 原画|超清|高清|标清|流畅
原画|超清|高清|标清|流畅 = 高清

# 分段时长（秒）
视频分段时间(秒) = 900

# 自动转MP4
录制完成后自动转为mp4格式 = 是
```

### 邮件通知（可选）

编辑 `docker-compose.yaml` 中的环境变量：

```yaml
uploader:
  environment:
    - MAIL_ENABLED=true
    - SMTP_SERVER=smtp.qq.com
    - SMTP_PORT=465
    - SENDER_EMAIL=your_email@qq.com
    - SENDER_PASSWORD=your_auth_code
    - RECEIVER_EMAIL=receiver@qq.com
```

或使用配置文件方式：

```bash
cp config/notify_config.ini.example config/notify_config.ini
vi config/notify_config.ini
```

## 📁 目录结构

```
.
├── config/                 # 配置文件
│   ├── config.ini         # 录制配置
│   ├── URL_config.ini     # 直播间列表
│   └── notify_config.ini  # 邮件配置（可选）
├── downloads/             # 录制文件存放
├── logs/                  # 日志文件
├── aliyunpan/             # 阿里云盘登录凭证
├── docker-compose.yaml    # Docker 编排
└── Dockerfile             # Docker 镜像
```

## 🔧 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看录制日志
docker-compose logs -f recorder

# 查看上传日志
docker-compose logs -f uploader

# 进入录制容器
docker exec -it live-recorder bash

# 手动触发阿里云盘登录
docker exec -it live-uploader /usr/local/bin/aliyunpan login
```

## ⚠️ 注意事项

1. **首次登录**: 必须先执行阿里云盘登录，否则上传会失败
2. **磁盘空间**: 确保有足够的临时存储空间（建议 > 5GB）
3. **网络稳定**: 上传大文件需要稳定的网络连接
4. **Cookie 配置**: 录制抖音/快手需要配置 cookie（详见原项目文档）

## 🐛 故障排查

### 上传失败

1. 检查阿里云盘是否登录：
   ```bash
   docker exec live-uploader /usr/local/bin/aliyunpan who
   ```

2. 重新登录：
   ```bash
   docker exec -it live-uploader /usr/local/bin/aliyunpan login
   ```

### 录制失败

1. 检查直播间链接是否有效
2. 检查 cookie 是否配置正确
3. 查看录制日志：
   ```bash
   docker-compose logs recorder | tail -100
   ```

## 📄 License

MIT License
