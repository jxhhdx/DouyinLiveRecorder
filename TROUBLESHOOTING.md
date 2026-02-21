# 🐛 踩坑记录与解决方案

本文档记录了在开发和部署过程中遇到的各种问题及解决方案，帮助你少走弯路。

---

## 1. aliyunpan CLI 参数问题

### ❌ 错误
```python
cmd = ["aliyunpan", "upload", "--overwrite", "file.mp4", "/remote"]
```

### ✅ 正确
```python
cmd = ["aliyunpan", "upload", "-ow", "file.mp4", "/remote"]
```

### 💡 说明
aliyunpan CLI 的参数使用单横线短格式，双横线 `--overwrite` 会报错 `flag provided but not defined`。

---

## 2. subprocess PIPE 缓冲区阻塞

### ❌ 问题现象
上传命令执行后卡住不动，进程无响应。

### ❌ 错误代码
```python
result = subprocess.run(
    cmd,
    stdout=subprocess.PIPE,  # ← 问题在这里
    stderr=subprocess.PIPE,  # ← 缓冲区满了会阻塞
    timeout=3600
)
```

### ✅ 解决方案
```python
result = subprocess.run(
    cmd,
    stdout=subprocess.DEVNULL,  # 丢弃输出
    stderr=subprocess.DEVNULL,  # 避免缓冲区满
    timeout=3600
)
```

### 💡 原理
aliyunpan CLI 会实时输出上传进度（带 `\r` 的进度条），PIPE 缓冲区有限（通常 64KB），满了之后进程会阻塞等待读取。使用 DEVNULL 直接丢弃输出可避免此问题。

---

## 3. 阿里云盘异步上传

### ❌ 问题现象
CLI 返回"上传成功"，但文件实际上还没传完，云端找不到文件。

### 💡 真相
aliyunpan CLI 是**同步上传**的（会等待实际传输完成），但是：
- 大文件上传需要时间（500MB 约 15-30 分钟）
- 上传完成后还需要服务器处理时间
- 立即 `ls` 检查可能还看不到文件

### ✅ 解决方案
上传完成后轮询验证：
```python
# 上传命令完成后，轮询检查云端文件
for check in range(max_checks):
    result = subprocess.run(["aliyunpan", "ls", "/path/file"], ...)
    if "文件大小" in result.stdout and "不存在" not in result.stdout:
        return True  # 确认上传成功
    time.sleep(30)  # 等待 30 秒后重试
```

---

## 4. 文件录制完成检测

### ❌ 问题现象
文件还在录制中就开始上传，导致上传不完整或失败。

### 💡 分析
直播录制是流式写入，文件大小会持续增长。需要检测文件大小**稳定**后才认为录制完成。

### ✅ 解决方案
```python
# 连续多次检测文件大小不变才认为稳定
stable_count = 0
for i in range(STABLE_CHECKS):  # 默认 3 次
    size1 = os.path.getsize(file)
    time.sleep(UPLOAD_INTERVAL)  # 间隔 30 秒
    size2 = os.path.getsize(file)
    
    if size1 == size2:
        stable_count += 1
    else:
        stable_count = 0  # 重置
        
if stable_count >= STABLE_CHECKS:
    # 文件稳定，可以上传
```

---

## 5. Cookie 特殊字符处理

### ❌ 问题现象
配置 Cookie 后程序报错 `InterpolationSyntaxError` 或解析失败。

### 💡 原因
ConfigParser 会解析 `%` 为特殊字符，而 Cookie 中常有 URL 编码如 `%22`、`%3D` 等。

### ✅ 解决方案
在 `config.ini` 中使用 `%%` 转义：
```ini
抖音cookie = device_web_memory_size=8; __live_version__=%%221.0.0%%22; ...
```

或者使用原始字符串（如果配置支持）。

---

## 6. 视频画质与文件体积

### 📊 各画质文件大小对比（15分钟片段）

| 画质 | 文件大小 | 上传时间 | 适用场景 |
|------|----------|----------|----------|
| 原画 | 1.5-2.5GB | 60-90分钟 | 收藏级，不建议 |
| 超清 | 600-900MB | 20-40分钟 | 画质较好 |
| **高清** | **200-350MB** | **10-20分钟** | **推荐** |
| 标清 | 100-200MB | 5-10分钟 | 省空间 |

### 💡 建议
- **画质选择高清**：画质足够，文件大小适中
- **分段 15 分钟**：平衡文件大小和管理便利性
- **自动转 MP4**：ts 格式兼容性差，建议开启自动转码

配置：`config/config.ini`
```ini
原画|超清|高清|标清|流畅 = 高清
视频分段时间(秒) = 900
录制完成后自动转为mp4格式 = 是
```

---

## 7. 磁盘空间管理

### ❌ 问题现象
磁盘满导致录制失败或系统崩溃。

### 💡 风险
- 40GB 磁盘录制 2 小时原画就会满
- 上传失败后文件堆积

### ✅ 解决方案
1. **及时删除已上传文件**（已实现）
2. **监控磁盘空间**：
   ```bash
   df -h
   ```
3. **设置录制空间阈值**：
   ```ini
   录制空间剩余阈值(gb) = 1.0
   ```
4. **分段录制**：小文件上传快，及时释放空间

---

## 8. 邮件通知配置

### ❌ 问题现象
邮件发送失败或进垃圾箱。

### ✅ 正确配置（QQ邮箱示例）
```ini
[mail]
enabled = true
smtp_server = smtp.qq.com
smtp_port = 465
use_ssl = true
sender_email = 1490960584@qq.com
sender_password = xxxxxxxxxxxxxxxx  # 授权码，不是登录密码！
receiver_email = 907317607@qq.com
```

### 💡 注意事项
1. **使用授权码**：QQ/163 邮箱需要开启 SMTP 并生成授权码
2. **SSL 加密**：端口 465 需要 SSL，端口 587 不需要
3. **频率限制**：同一类型邮件 60 分钟内只发一次，避免轰炸

---

## 9. Docker 权限问题

### ❌ 问题现象
容器内无法访问配置文件或保存目录。

### ✅ 解决方案
确保宿主机目录有正确权限：
```bash
# 创建目录并设置权限
mkdir -p config downloads logs aliyunpan
chmod 777 downloads logs aliyunpan

# 或者使用当前用户权限
sudo chown -R $USER:$USER config downloads logs aliyunpan
```

---

## 10. 网络与上传速度

### 📊 实际上传速度参考

| 文件大小 | 网络环境 | 实际上传时间 |
|----------|----------|--------------|
| 551MB | 国内服务器 | 约 15 分钟 |
| 885MB | 国内服务器 | 约 38 分钟 |
| 2GB | 国内服务器 | 约 60+ 分钟 |

### 💡 优化建议
1. **选择国内服务器**：阿里云盘在国内速度快
2. **避开高峰期**：晚 8-11 点可能较慢
3. **适当降低画质**：高清 vs 超清可节省 50% 时间

---

## 11. 日志查看技巧

### 实时查看日志
```bash
# 录制日志
docker-compose logs -f recorder

# 上传日志
docker-compose logs -f uploader

# 只看最近 100 行
docker-compose logs --tail=100 recorder
```

### 关键词过滤
```bash
# 查看上传成功记录
docker-compose logs uploader | grep "上传成功"

# 查看错误
docker-compose logs uploader | grep -E "(失败|错误|异常)"
```

---

## 12. 重新登录阿里云盘

### ❌ 问题现象
提示 token 过期或登录失效。

### ✅ 重新登录步骤
```bash
# 1. 停止上传服务
docker-compose stop uploader

# 2. 重新登录
docker run --rm -it \
  -v $(pwd)/aliyunpan:/root/aliyunpan \
  douyin-live-recorder:latest \
  /usr/local/bin/aliyunpan login

# 3. 启动服务
docker-compose start uploader
```

---

## 快速诊断清单

遇到问题先检查：

- [ ] 阿里云盘已登录：`docker exec live-uploader /usr/local/bin/aliyunpan who`
- [ ] 直播间链接有效：在浏览器中能正常打开
- [ ] Cookie 配置正确：特殊字符已转义
- [ ] 磁盘空间充足：`df -h`
- [ ] 网络连接正常：`ping www.aliyundrive.com`
- [ ] 配置文件格式正确：INI 格式无语法错误

---

## 联系与支持

如果以上方法都无法解决问题：
1. 查看完整日志：`docker-compose logs > logs.txt`
2. 提交 Issue 附上日志文件
3. 描述清楚问题现象和已尝试的解决方案
