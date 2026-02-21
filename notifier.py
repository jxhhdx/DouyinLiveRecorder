#!/usr/bin/env python3
"""
邮件通知模块
用于发送系统告警邮件
"""
import os
import sys
import time
import json
import smtplib
import configparser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# 配置文件路径
CONFIG_FILE = os.environ.get("NOTIFY_CONFIG", "/app/config/notify_config.ini")
STATE_FILE = os.environ.get("NOTIFY_STATE", "/app/logs/notify_state.json")


class MailNotifier:
    def __init__(self):
        self.config = self._load_config()
        self.state = self._load_state()
        
    def _load_config(self):
        """加载邮件配置（优先环境变量）"""
        config = configparser.ConfigParser()
        
        # 优先从环境变量读取
        defaults = {
            'enabled': os.environ.get('MAIL_ENABLED', 'false'),
            'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.qq.com'),
            'smtp_port': os.environ.get('SMTP_PORT', '465'),
            'use_ssl': os.environ.get('SMTP_USE_SSL', 'true'),
            'sender_email': os.environ.get('SENDER_EMAIL', ''),
            'sender_password': os.environ.get('SENDER_PASSWORD', ''),
            'receiver_email': os.environ.get('RECEIVER_EMAIL', ''),
            'min_interval_minutes': os.environ.get('MAIL_MIN_INTERVAL', '60')
        }
        
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE, encoding='utf-8')
            if 'mail' not in config.sections():
                config['mail'] = defaults
        else:
            config['mail'] = defaults
            # 创建默认配置文件
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                config.write(f)
                
        return config['mail']
    
    def _load_state(self):
        """加载通知状态（用于频率控制）"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_state(self):
        """保存通知状态"""
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False)
    
    def _can_send(self, alert_type):
        """检查是否可以发送邮件（频率控制）"""
        if not self.config.getboolean('enabled', False):
            return False
            
        min_interval = self.config.getint('min_interval_minutes', 60)
        last_send = self.state.get(f'last_{alert_type}', 0)
        current_time = time.time()
        
        if current_time - last_send < min_interval * 60:
            return False
            
        return True
    
    def _record_send(self, alert_type):
        """记录邮件发送时间"""
        self.state[f'last_{alert_type}'] = time.time()
        self._save_state()
    
    def send_email(self, subject, body, alert_type='general'):
        """
        发送邮件
        
        Args:
            subject: 邮件主题
            body: 邮件内容
            alert_type: 告警类型（用于频率控制）
        
        Returns:
            bool: 是否发送成功
        """
        if not self._can_send(alert_type):
            return False
            
        smtp_server = self.config.get('smtp_server', 'smtp.qq.com')
        smtp_port = self.config.getint('smtp_port', 465)
        use_ssl = self.config.getboolean('use_ssl', True)
        sender_email = self.config.get('sender_email', '')
        sender_password = self.config.get('sender_password', '')
        receiver_email = self.config.get('receiver_email', sender_email)
        
        if not sender_email or not sender_password:
            print(f"[Notify] 邮件配置不完整，无法发送邮件")
            return False
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        
        # 添加发送时间
        body_with_time = f"""
{body}

---
发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
服务器: {os.uname().nodename}
"""
        msg.attach(MIMEText(body_with_time, 'plain', 'utf-8'))
        
        try:
            # 连接 SMTP 服务器
            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                server.starttls()
            
            # 登录
            server.login(sender_email, sender_password)
            
            # 发送邮件
            server.sendmail(sender_email, receiver_email.split(','), msg.as_string())
            server.quit()
            
            self._record_send(alert_type)
            print(f"[Notify] 邮件发送成功: {subject}")
            return True
            
        except Exception as e:
            print(f"[Notify] 邮件发送失败: {e}")
            return False
    
    def notify_token_expired(self, detail=""):
        """发送 Token 过期提醒"""
        subject = "【直播录制系统】阿里云盘 Token 已过期"
        body = f"""
您的阿里云盘 Token 已过期，无法继续上传录制文件。

详细信息:
{detail}

请尽快登录服务器重新授权:
    cd ~/aliyunpan
    ./aliyunpan login

登录后请检查上传服务是否正常运行:
    ~/status.sh

如果不及时处理，新的录制文件将堆积在本地硬盘。
"""
        return self.send_email(subject, body, alert_type='token_expired')
    
    def notify_upload_error(self, error_msg, filename=""):
        """发送上传错误提醒"""
        subject = f"【直播录制系统】上传失败提醒"
        body = f"""
上传文件时发生错误。

文件名: {filename or '未知'}
错误信息: {error_msg}

请检查:
1. 阿里云盘登录状态: ~/aliyunpan/aliyunpan who
2. 网络连接是否正常
3. 阿里云盘空间是否充足

如需重新登录:
    cd ~/aliyunpan
    ./aliyunpan login
"""
        return self.send_email(subject, body, alert_type='upload_error')
    
    def notify_upload_success(self, filename, file_size_mb, remote_path):
        """发送上传成功通知"""
        subject = f"【直播录制系统】文件上传成功"
        body = f"""
录制文件已成功上传到阿里云盘。

文件名: {filename}
文件大小: {file_size_mb:.2f} MB
上传路径: {remote_path}

您可以在阿里云盘 App 或网页版中查看该文件。

如需查看本地日志:
    tail -f ~/DouyinLiveRecorder/logs/auto_uploader.log
"""
        return self.send_email(subject, body, alert_type='upload_success')
    
    def notify_system_started(self):
        """发送系统启动通知"""
        subject = "【直播录制系统】服务已启动"
        body = f"""
直播录制自动上传服务已启动。

监控目录: ~/DouyinLiveRecorder/downloads
上传目标: /直播录制

系统将自动:
1. 检测直播间开播状态并录制
2. 录制完成后自动上传到阿里云盘
3. 上传成功后删除本地文件

查看状态: ~/status.sh
查看日志: tail -f ~/DouyinLiveRecorder/logs/auto_uploader.log
"""
        return self.send_email(subject, body, alert_type='system_start')
    
    def notify_disk_full(self, usage_percent, free_gb):
        """发送磁盘空间不足提醒"""
        subject = "【直播录制系统】磁盘空间不足警告"
        body = f"""
服务器磁盘空间不足，可能影响录制！

当前磁盘使用率: {usage_percent}%
剩余空间: {free_gb:.2f} GB

建议:
1. 检查阿里云盘上传是否正常
2. 手动清理本地录制文件
3. 扩容服务器磁盘

查看文件: ls -lh ~/DouyinLiveRecorder/downloads/
"""
        return self.send_email(subject, body, alert_type='disk_full')


# 测试邮件功能
if __name__ == "__main__":
    notifier = MailNotifier()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "test":
            print("发送测试邮件...")
            result = notifier.send_email(
                "【直播录制系统】测试邮件",
                "这是一封测试邮件，如果您收到说明邮件配置正确。",
                "test"
            )
            if result:
                print("测试邮件发送成功！")
            else:
                print("测试邮件发送失败，请检查配置。")
        elif cmd == "token":
            notifier.notify_token_expired("手动测试触发")
        elif cmd == "error":
            notifier.notify_upload_error("测试错误信息", "test.mp4")
        elif cmd == "config":
            print(f"配置文件路径: {CONFIG_FILE}")
            print(f"邮件启用: {notifier.config.getboolean('enabled', False)}")
            print(f"SMTP服务器: {notifier.config.get('smtp_server', '')}")
            print(f"发件人: {notifier.config.get('sender_email', '')}")
            print(f"收件人: {notifier.config.get('receiver_email', '')}")
        else:
            print("用法: python3 notifier.py [test|token|error|config]")
    else:
        print("邮件通知模块")
        print("用法: python3 notifier.py [test|token|error|config]")
