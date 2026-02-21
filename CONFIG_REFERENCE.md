# 📋 关键配置参考（方便复制）

## 1. 监控主播列表

**文件**: `config/URL_config.ini`

```ini
# 支持的格式：
#   - 直接链接: https://live.douyin.com/xxxxx
#   - 带画质设置: 超清,https://live.douyin.com/xxxxx
#   - 注释行: 以 # 开头

# 正式监控的主播
https://live.douyin.com/你的抖音直播间ID,主播: 主播名字
https://live.kuaishou.com/u/你的快手用户ID,主播: 主播名字
```

---

## 2. Cookie 配置

**文件**: `config/config.ini` [Cookie] 部分

### 抖音 Cookie（必填）
```ini
抖音cookie = 你的抖音Cookie（从浏览器开发者工具复制）
```

**获取方式**: 登录抖音网页版 → F12 开发者工具 → Application/Storage → Cookies → 复制所有 cookie

**⚠️ 注意**: Cookie 中有 `%` 字符，在 config.ini 中需要写成 `%%` 进行转义

### 快手 Cookie
```ini
快手cookie = 你的快手Cookie（从浏览器开发者工具复制）
```

---

## 3. 邮箱授权码配置

**文件**: `config/notify_config.ini`

```ini
[mail]
enabled = true
smtp_server = smtp.qq.com
smtp_port = 465
use_ssl = true
sender_email = 你的发件邮箱@qq.com
sender_password = 你的授权码
receiver_email = 你的收件邮箱@qq.com
min_interval_minutes = 60
```

### 如何获取 QQ 邮箱授权码

1. 登录 QQ 邮箱网页版
2. 点击顶部「设置」→「账户」
3. 找到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务」
4. 开启「SMTP服务」
5. 按提示发送短信验证
6. 获得 16 位授权码（如：`abcdxyz123456789`）
7. 将授权码填入 `sender_password`

**⚠️ 重要**: 
- 不是 QQ 登录密码！是专门的授权码
- 授权码只显示一次，请妥善保存
- 如果忘记需要重新生成

---

## 4. 录制配置推荐

**文件**: `config/config.ini` [录制设置] 部分

```ini
[录制设置]
# 画质: 原画|超清|高清|标清|流畅
# 推荐高清，文件大小适中
原画|超清|高清|标清|流畅 = 高清

# 分段时长（秒）
# 15分钟 = 900秒，推荐
视频分段时间(秒) = 900

# 自动转 MP4，兼容性更好
录制完成后自动转为mp4格式 = 是
mp4格式重新编码为h264 = 否
追加格式后删除原文件 = 是
```

---

## 5. Docker Compose 环境变量

**文件**: `docker-compose.yaml`

```yaml
uploader:
  environment:
    # 阿里云盘配置
    - ALIYUNPAN_BIN=/usr/local/bin/aliyunpan
    - ALIYUNPAN_REMOTE_PATH=/直播录制
    
    # 路径配置
    - RECORD_DIR=/app/downloads
    - LOG_DIR=/app/logs
    
    # 上传配置
    - DELETE_AFTER_UPLOAD=true
    - UPLOAD_INTERVAL=30
    - MIN_FILE_SIZE=10485760
    
    # 邮件通知（修改后启用）
    - MAIL_ENABLED=true
    - SMTP_SERVER=smtp.qq.com
    - SMTP_PORT=465
    - SMTP_USE_SSL=true
    - SENDER_EMAIL=你的发件邮箱@qq.com
    - SENDER_PASSWORD=你的授权码
    - RECEIVER_EMAIL=你的收件邮箱@qq.com
    - MAIL_MIN_INTERVAL=60
```

---

## 6. 快速复制清单

部署时需要修改的文件清单：

| 文件 | 需要修改 | 关键配置 |
|------|----------|----------|
| `config/URL_config.ini` | ✅ | 主播直播间链接 |
| `config/config.ini` | ✅ | 抖音/快手 Cookie |
| `config/notify_config.ini` | ⚪ | 邮箱授权码（可选） |
| `docker-compose.yaml` | ⚪ | 环境变量（可选） |

**部署步骤**: 
1. 复制上面的配置到对应文件
2. 执行 `./setup.sh`
3. 扫码登录阿里云盘
4. 完成！
