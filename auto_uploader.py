#!/usr/bin/env python3
"""
直播录制自动上传守护进程
实时监控录制目录，文件完成后自动上传到阿里云盘
"""
import os
import sys
import time
import json
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 导入邮件通知模块
try:
    from notifier import MailNotifier
    NOTIFIER = MailNotifier()
except Exception as e:
    print(f"[警告] 邮件通知模块加载失败: {e}")
    NOTIFIER = None

# ============================================
# 配置区域
# ============================================

# 录制文件保存目录
RECORD_DIR = os.environ.get("RECORD_DIR", "/app/downloads")

# 阿里云盘配置
ALIYUNPAN_BIN = os.environ.get("ALIYUNPAN_BIN", "/usr/local/bin/aliyunpan")
ALIYUNPAN_REMOTE_PATH = "/直播录制"  # 阿里云盘中的目标目录

# 上传配置
DELETE_AFTER_UPLOAD = True      # 上传成功后删除本地文件
UPLOAD_INTERVAL = 30            # 文件大小检测间隔（秒）
STABLE_CHECKS = 3               # 文件大小连续稳定次数才认为录制完成
MIN_FILE_SIZE = 10 * 1024 * 1024  # 最小文件大小 10MB（小于此值不上传）

# 日志配置
LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")
LOG_FILE = os.path.join(LOG_DIR, "auto_uploader.log")
STATE_FILE = os.path.join(LOG_DIR, "upload_state.json")

# 视频文件扩展名
VIDEO_EXTENSIONS = {'.mp4', '.ts', '.flv', '.mkv', '.mov', '.avi', '.wmv'}

# ============================================

os.makedirs(LOG_DIR, exist_ok=True)

class AutoUploader:
    def __init__(self):
        self.file_states = defaultdict(lambda: {
            'size_history': [],
            'stable_count': 0,
            'uploaded': False
        })
        self.load_state()
        self.lock = threading.Lock()
        
    def log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    
    def load_state(self):
        """加载上传状态"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 过滤掉已删除的文件记录
                    self.file_states.update({
                        k: v for k, v in data.items() 
                        if os.path.exists(k)
                    })
            except Exception as e:
                self.log(f"加载状态文件失败: {e}")
    
    def save_state(self):
        """保存上传状态"""
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(dict(self.file_states), f, ensure_ascii=False)
        except Exception as e:
            self.log(f"保存状态文件失败: {e}")
    
    def is_recording_file(self, filepath):
        """检查是否是正在录制的临时文件"""
        # 常见的录制临时文件标识
        temp_patterns = ['.tmp', '.part', '.recording', '.download']
        return any(pattern in filepath.lower() for pattern in temp_patterns)
    
    def get_file_size(self, filepath):
        """获取文件大小"""
        try:
            return os.path.getsize(filepath)
        except:
            return 0
    
    def is_file_stable(self, filepath):
        """
        检查文件是否稳定（录制完成）
        通过连续检测文件大小是否变化来判断
        """
        with self.lock:
            state = self.file_states[filepath]
            current_size = self.get_file_size(filepath)
            
            if current_size == 0:
                return False
            
            # 记录大小历史
            state['size_history'].append(current_size)
            if len(state['size_history']) > 5:
                state['size_history'].pop(0)
            
            # 检查文件大小是否稳定
            if len(state['size_history']) >= 2:
                if state['size_history'][-1] == state['size_history'][-2]:
                    state['stable_count'] += 1
                else:
                    state['stable_count'] = 0
                
                if state['stable_count'] >= STABLE_CHECKS:
                    return True
            
            return False
    
    def upload_file(self, filepath):
        """上传文件到阿里云盘"""
        filepath = Path(filepath)
        filename = filepath.name
        
        # 检查文件大小
        file_size = filepath.stat().st_size
        if file_size < MIN_FILE_SIZE:
            self.log(f"⏭️ 文件太小，跳过上传: {filename} ({file_size/1024/1024:.2f}MB)")
            return True
        
        # 创建日期子目录
        today = datetime.now().strftime("%Y-%m-%d")
        remote_path = f"{ALIYUNPAN_REMOTE_PATH}/{today}"
        
        self.log(f"📤 开始上传: {filename} ({file_size/1024/1024:.2f}MB)")
        
        try:
            # 检查 aliyunpan 是否已登录
            check_login = subprocess.run(
                [ALIYUNPAN_BIN, "who"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=10
            )
            
            if "登录失败" in check_login.stdout or check_login.returncode != 0:
                self.log(f"❌ 阿里云盘未登录，请先执行: {ALIYUNPAN_BIN} login")
                # 发送邮件通知
                if NOTIFIER:
                    NOTIFIER.notify_token_expired(f"命令输出: {check_login.stdout}\n错误: {check_login.stderr}")
                return False
            
            # 执行上传（同步阻塞，不捕获输出避免PIPE缓冲区问题）
            cmd = [
                ALIYUNPAN_BIN,
                "upload",
                "-ow",  # 覆盖同名文件
                str(filepath),
                remote_path
            ]
            
            self.log(f"⏳ 正在上传（可能需要10-40分钟，取决于文件大小和网络）...")
            
            # 使用DEVNULL丢弃输出，避免PIPE缓冲区满导致阻塞
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                self.log(f"✅ 上传命令执行成功: {filename}")
                
                # 上传完成后再验证一下
                self.log(f"⏳ 验证云端文件...")
                
                # 验证文件是否确实上传成功
                verify_cmd = [
                    ALIYUNPAN_BIN,
                    "ls",
                    f"{remote_path}/{filename}"
                ]
                
                verify_success = False
                verify_output = ""
                
                try:
                    verify_result = subprocess.run(
                        verify_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        timeout=30
                    )
                    verify_output = verify_result.stdout + verify_result.stderr
                    
                    # 检查验证结果
                    if (verify_result.returncode == 0 and 
                        "不存在" not in verify_output and 
                        "文件大小" in verify_output and
                        filename in verify_output):
                        verify_success = True
                        
                except Exception as e:
                    self.log(f"⚠️ 验证异常: {e}")
                
                if verify_success:
                    self.log(f"✅ 云端验证成功，文件已存在: {filename}")
                    self.log(f"   本地大小: {file_size/1024/1024:.2f}MB")
                    # 发送上传成功邮件通知
                    if NOTIFIER:
                        NOTIFIER.notify_upload_success(filename, file_size/1024/1024, remote_path)
                else:
                    self.log(f"⚠️ 云端验证失败，文件可能未上传成功: {filename}")
                    self.log(f"   验证输出: {verify_output}")
                    # 不删除本地文件，等待下次重试
                    return False
                
                # 更新状态
                with self.lock:
                    self.file_states[str(filepath)]['uploaded'] = True
                self.save_state()
                
                # 删除本地文件
                if DELETE_AFTER_UPLOAD:
                    try:
                        filepath.unlink()
                        self.log(f"🗑️ 已删除本地文件: {filename}")
                        # 从状态中移除
                        with self.lock:
                            if str(filepath) in self.file_states:
                                del self.file_states[str(filepath)]
                        self.save_state()
                    except Exception as e:
                        self.log(f"⚠️ 删除文件失败: {filename}, 错误: {e}")
                
                return True
            else:
                self.log(f"❌ 上传失败: {filename} (返回码: {result.returncode})")
                # 发送上传失败通知
                if NOTIFIER:
                    NOTIFIER.notify_upload_error(f"上传命令返回非零状态码: {result.returncode}", filename)
                return False
                
        except subprocess.TimeoutExpired:
            self.log(f"⏰ 上传超时: {filename}")
            if NOTIFIER:
                NOTIFIER.notify_upload_error(f"上传超时（超过1小时）", filename)
            return False
        except Exception as e:
            self.log(f"❌ 上传异常: {filename}, 错误: {e}")
            if NOTIFIER:
                NOTIFIER.notify_upload_error(str(e), filename)
            return False
    
    def scan_files(self):
        """扫描录制目录，查找需要上传的文件"""
        record_path = Path(RECORD_DIR)
        
        if not record_path.exists():
            self.log(f"⚠️ 录制目录不存在: {RECORD_DIR}")
            return
        
        files_to_check = []
        
        for file_path in record_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS:
                str_path = str(file_path)
                
                # 跳过临时文件
                if self.is_recording_file(str_path):
                    continue
                
                # 跳过已上传的文件
                with self.lock:
                    if self.file_states[str_path].get('uploaded'):
                        continue
                
                files_to_check.append(file_path)
        
        return files_to_check
    
    def check_disk_space(self):
        """检查磁盘空间"""
        try:
            stat = os.statvfs(RECORD_DIR)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            percent = (used / total) * 100 if total > 0 else 0
            free_gb = free / (1024**3)
            
            if percent > 90:  # 磁盘使用率超过 90%
                self.log(f"⚠️ 磁盘空间不足！使用率: {percent:.1f}%, 剩余: {free_gb:.2f}GB")
                if NOTIFIER:
                    NOTIFIER.notify_disk_full(percent, free_gb)
            
            return percent, free_gb
        except Exception as e:
            self.log(f"检查磁盘空间失败: {e}")
            return 0, 0
    
    def run(self):
        """主循环"""
        self.log("=" * 50)
        self.log("🚀 自动上传守护进程已启动")
        self.log(f"📁 录制目录: {RECORD_DIR}")
        self.log(f"☁️  阿里云盘路径: {ALIYUNPAN_REMOTE_PATH}")
        self.log(f"⏱️  检测间隔: {UPLOAD_INTERVAL}秒")
        self.log(f"🗑️  上传后删除: {'是' if DELETE_AFTER_UPLOAD else '否'}")
        self.log("=" * 50)
        
        # 发送系统启动通知
        if NOTIFIER:
            NOTIFIER.notify_system_started()
        
        # 检查磁盘空间
        self.check_disk_space()
        
        try:
            loop_count = 0
            while True:
                files = self.scan_files()
                
                if files:
                    self.log(f"📂 发现 {len(files)} 个待处理文件")
                    
                    for file_path in files:
                        str_path = str(file_path)
                        
                        # 检查文件是否稳定
                        if self.is_file_stable(str_path):
                            self.log(f"📋 文件已稳定，准备上传: {file_path.name}")
                            self.upload_file(file_path)
                        else:
                            size_mb = self.get_file_size(str_path) / 1024 / 1024
                            self.log(f"⏳ 文件录制中: {file_path.name} ({size_mb:.2f}MB)")
                
                # 每30次循环检查一次磁盘空间（约15分钟）
                loop_count += 1
                if loop_count % 30 == 0:
                    self.check_disk_space()
                
                time.sleep(UPLOAD_INTERVAL)
                
        except KeyboardInterrupt:
            self.log("\n👋 收到中断信号，正在退出...")
            self.save_state()
            sys.exit(0)

def main():
    uploader = AutoUploader()
    uploader.run()

if __name__ == "__main__":
    main()
