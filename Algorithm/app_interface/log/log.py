import os
import time
import time

LOG_FILE_PATH = "log/app_interface_logs.log"
LOG_START_MARKER = "--->< SCHEDULING START ><---\n"

def log_debug(message):
    """自定义日志函数，用于将日志写入指定文件"""
    try:
        # 获取当前时间
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # 组装日志内容
        log_message = f"{current_time} - DEBUG - {message}\n"
        if not os.path.exists(LOG_FILE_PATH):
            with open(LOG_FILE_PATH, "a") as log_file:
                log_file.write(LOG_START_MARKER)
            first_write = True  # 标记为第一次写入
        else:
            first_write = False  # 非第一次写入
        with open(LOG_FILE_PATH, "a") as log_file:
            if not first_write and message == "获取用户输入成功":
                log_file.write("\n")
                log_file.write(LOG_START_MARKER)
        # 追加写入日志文件
        with open(LOG_FILE_PATH, "a") as log_file:
            log_file.write(log_message)
    except Exception as e:
        print(f"写入日志失败: {e}")

def log_error(message):
    """自定义日志函数，用于将日志写入指定文件"""
    try:
        # 定义日志文件路径
        LOG_FILE_PATH = "log/app_interface_logs.log"
        # 获取当前时间
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # 组装日志内容
        log_message = f"{current_time} - ERROR - {message}\n"
        # 追加写入日志文件
        with open(LOG_FILE_PATH, "a") as log_file:
            log_file.write(log_message)
    except Exception as e:
        print(f"写入日志失败: {e}")


