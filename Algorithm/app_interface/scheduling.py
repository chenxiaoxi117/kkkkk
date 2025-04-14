import os
import sys
import time
import uuid  
import json
import threading
import subprocess
import concurrent.futures
import regex as re
import pandas as pd
from io import BytesIO
from log.log import log_debug,log_error
import xml.etree.ElementTree as ET
from flask import Flask, request, jsonify, send_file, Blueprint
# 创建 Blueprint 实例
scheduling_bp = Blueprint('scheduling', __name__)
task_status = {}  # 用于保存状态的字典
task_process = {}  # 用于保存进程的字典
device_results = {}
scheduling_results = {}
data = {}
def getform_data():
    return data
def getfrom_algorithm():
    return algorithm
def getfrom_scheduling_results():
    return scheduling_results
def getfrom_device_results():
    return device_results
@scheduling_bp.route('/api/v1/scheduling/task/start', methods=['POST'])
def task_start():
    global java_done_event
    global data
    try:
        # 获取前端发送的数据
        java_done_event = threading.Event()
        data = request.get_json()
        device_total = data.get('deviceTotal')  # 获取终端设备总数
        device_info = data.get('deviceInfo')  # 获取各城市终端设备信息
        app_info = data.get('appInfo')   # 获取任务应用信息
        global algorithm
        algorithm = data.get('algorithm')  # 获取调度算法
        log_debug(f"获取用户输入成功")
        # 更新 CSV 文件
        update_csv(device_info)
        # 更新 XML 文件
        update_xml(app_info)
        log_debug(f"根据用户输入，成功更新Java配置文件")
        # 生成调度任务 UUID
        global sch_uuid_status
        sch_uuid = f"sch-{uuid.uuid4()}"
        sch_uuid_status=sch_uuid
        with open('uuid.txt', "w") as file:
            file.write(sch_uuid)
        # 将任务初始状态存入字典
        global task_status
        task_status[sch_uuid] = {"status": 0, "startTime": 0}
        # 提交任务到线程池
        start_time = time.time()
        log_debug(f"Submitting task {sch_uuid} to background thread pool")
        # 异步执行 Java 和 Python 程序
        threading.Thread(target=run_scheduling_tasks, args=(device_total, algorithm, sch_uuid)).start()
        # with concurrent.futures.ThreadPoolExecutor() as executor:
        #     executor.submit(run_scheduling_tasks, device_total, algorithm, sch_uuid)
        # 记录任务提交后时间，确保没有阻塞
        submit_time = time.time()
        log_debug(f"Task {sch_uuid} 返回Uuid耗时 : {submit_time - start_time:.4f} seconds")
        # 立即返回 UUID 响应
        return jsonify({
            "errorCode": 0,
            "errorMsg": "",
            "message": {
                "schUuid": sch_uuid
            }
        })
    except Exception as e:
        return jsonify({
            "errorCode": 500,
            "errorMsg": str(e),
            "message": {}
        }), 500


def run_scheduling_tasks(device_total, algorithm, sch_uuid):
    try:
        # 启动 Java 进程
        java_process = subprocess.Popen(
            ["java", "-cp", "../task_generator/src", "device_task.device_task", str(device_total)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="../task_generator"
        )
         # 启动一个线程来异步读取 Java 进程的输出
        threading.Thread(target=monitor_java_output, args=(java_process, sch_uuid)).start()
        # 等待 Java 进程执行完再启动 Python 进程
        if algorithm == 1:
            python_script = "../trade_off_new.py"
        elif algorithm == 2:
            python_script = "../trade_off_new.py"
        elif algorithm == 3:
            python_script = "../GA_new.py"
        elif algorithm == 4:
            python_script = "../greedy_allocation.py"
        else:
            log_error(f"检测到无效的算法选择")  
            return
        
        # 启动 Python 进程
        java_done_event.wait()
        python_process = subprocess.Popen(
            ["python", python_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # 保存 Python 进程对象到全局字典中
        global task_process
        task_process[sch_uuid] = python_process
        # 启动一个线程来异步读取 Python 进程的输出
        threading.Thread(target=monitor_python_output, args=(python_process, sch_uuid)).start()
        # 创建线程来更新任务状态
        thread = threading.Thread(target=update_task_status, args=(sch_uuid, python_process))
        thread.start()
        # 立即返回任务的 UUID
        log_debug(f"py任务 {sch_uuid} 已提交到后台线程池")
        return sch_uuid  # 这里返回 UUID，响应客户端

    except Exception as e:
        log_error(f"调度任务执行出错: {e}")
        return None
def monitor_java_output(java_process, sch_uuid):
    """监控 Java 进程的输出"""
    try:
        stdout, stderr = java_process.communicate()  # 等待 Java 进程完成并获取输出
        if stdout:
            # 按行分割输出，去掉多余换行
            stdout_lines = stdout.decode().strip().split("\n")
            for line in stdout_lines:
                log_debug(f"Java 输出:{line.strip()}")  # 每行去掉多余空格后记录日志
            java_done_event.set()
            return  #java程序失败 不能执行python程序
        if stderr:
            log_error(f"Java 错误: {stderr.decode().strip()}")
    except Exception as e:
        log_error(f"监控 Java 进程输出失败: {e}")

def monitor_python_output(python_process, sch_uuid):
    """监控 Python 进程的输出"""
    try:
        stdout, stderr = python_process.communicate()  # 等待 Python 进程完成并获取输出
        if stdout:
            # 将 Python 的输出按两个 JSON 数据分割
            output_parts  = stdout.split("__SEPARATOR__")
            # 存储结果
            # 分别解析两个 JSON 数据
            if len(output_parts) >= 2:
                log_debug(f"解析成功:识别到共有{len(output_parts)}个Json数据")
                task_results_json = json.loads(output_parts[0])  # 第一个 JSON 数据
                scheduling_message_json = json.loads(output_parts[1])  # 第二个 JSON 数据
                global scheduling_results
                global device_results
                device_results = task_results_json  # 存储任务结果
                scheduling_results = scheduling_message_json  # 存储调度信息
                log_debug(f"成功获取两个 JSON 数据")
            else:
                log_debug(f"输出的 JSON 数据不完整，无法解析")
            # 替换默认 UUID 为 sch_uuid
            if "default_uuid" in device_results:
                device_results[sch_uuid] = device_results.pop("default_uuid")
                log_debug(f"Python 设备结果表输出成功并成功获取了 UUID: {sch_uuid}")
            if "default_uuid" in scheduling_results:
                scheduling_results[sch_uuid] = scheduling_results.pop("default_uuid")
                log_debug(f"Python 调度信息表输出成功并成功获取了 UUID: {sch_uuid}")
        if stderr:
            log_error(f"Python 错误: {stderr}")
    except Exception as e:
        log_error(f"监控 Python 进程输出失败: {e}")

def update_task_status(sch_uuid, python_process):
    """定期更新任务状态"""
    try:
        # 初始状态为 0
        task_status[sch_uuid] = {"status": 0, "startTime": None}
        start_time = int(time.time())
        start_time_real = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
        time.sleep(1)
        if python_process.poll() is None:
            task_status[sch_uuid]["status"] = 100  # 任务进行中
            task_status[sch_uuid]["startTime"] = start_time
            python_process.wait()
        if python_process.returncode == 0:
            time.sleep(1)
            end_time = int(time.time())
            log_debug(f"python算法运行时间为: {end_time-start_time} s")
            task_status[sch_uuid]["status"] = 200  # 任务成功完成
        else:
            task_status[sch_uuid]["status"] = 0  # 任务失败
        log_debug(f"任务 {sch_uuid} 状态更新为: {task_status[sch_uuid]}")
    except Exception as e:
        log_error(f"更新任务状态失败: {e}")


def update_csv(device_info):
    try:
        city_mapping = {
            "北京": "Beijing","天津": "Tianjin","石家庄": "Shijiazhuang",
            "衡水": "Hengshui","唐山": "Tangshan","邯郸": "Handan",
            "秦皇岛": "Qinhuangdao","保定": "Baoding","张家口": "Zhangjiakou",
            "承德": "Chengde","廊坊": "Langfang","沧州": "Cangzhou",
            "邢台": "Xingtai"
        }
        file_path = "../task_generator/data/13city.csv"
        df = pd.read_csv(file_path)
        for device in device_info:
            city = device['city']
            value = device['value']
            # 如果城市名是中文，则使用映射字典转换为拼音
            if city in city_mapping:
                city_pinyin = city_mapping[city]
                # 如果转换后的拼音城市名存在于 CSV 中，则更新对应的值
                if city_pinyin in df['City'].values:
                    df.loc[df['City'] == city_pinyin, 'percentageOfTotalDevices'] = value
        df.to_csv(file_path, index=False)
    except Exception as e:
        log_error(f"更新 CSV 文件出错: {e}")


def update_xml(app_info):
    try:
        xml_file_path = "../task_generator/src/applications.xml"
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        for app in app_info:
            app_type = str(app['category'])
            usage_percentage = app['value']
            for xml_app in root.findall('application'):
                if xml_app.find('type').text == app_type:
                    xml_app.find('usage_percentage').text = str(usage_percentage)
                    break
        tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)
    except Exception as e:
        log_error(f"更新 XML 文件出错: {e}")

@scheduling_bp.route('/api/v1/scheduling/task/status', methods=['GET'])
def task_status_query():
    try:
        # 如果任务 UUID 存在于任务状态字典中
        if task_status == {}:
            log_debug(f"调度执行之前开始查询")
            return jsonify({
                    "errorCode": 0,
                    "errorMsg": "没有开始执行调度",
                    "message": {
                        "schUuid": "请先执行调度，这样才会生成UUID",
                        "status": 0
                    }
            })
        if sch_uuid_status in task_status:
            status_info = task_status[sch_uuid_status]
            # 只有在任务状态为 200（完成）时，不返回 startTime
            if status_info["status"] == 200:
                log_debug(f"调度状态为执行完成")
                return jsonify({
                    "errorCode": 0,
                    "errorMsg": "调度算法执行完成",
                    "message": {
                        "schUuid": sch_uuid_status,
                        "status": status_info["status"],
                    }
                })
            if status_info["status"] == 100:
                # 如果任务状态是 100，返回当前状态并返回startTime，供前端展示运行了多少时间
                log_debug(f"调度状态为正在执行")
                return jsonify({
                    "errorCode": 0,
                    "errorMsg": "调度算法执行中",
                    "message": {
                        "schUuid": sch_uuid_status,
                        "status": status_info["status"],
                        "startTime": status_info["startTime"]
                    }
                })
            if status_info["status"] == 0:
                # 如果任务状态是0(没有开始调度)，返回当前状态但不返回startTime
                log_debug(f"调度状态为未开始调度")
                return jsonify({
                    "errorCode": 0,
                    "errorMsg": "没有开始执行调度或已被中断",
                    "message": {
                        "schUuid": sch_uuid_status,
                        "status": status_info["status"]
                    }
                })
    except Exception as e:
        log_error(f"获取调度状态出错: {e}")
        return jsonify({
            "errorCode": 500,
            "errorMsg": str(e),
            "message": {}
        }), 500

@scheduling_bp.route('/api/v1/scheduling/task/abort', methods=['POST'])
def task_abort():
    try:
        # 获取请求体中的 UUID
        data = request.get_json()
        sch_uuid = data.get('schUuid')
        # 查找任务对应的进程对象
        process = task_process.get(sch_uuid)
        if process:
            # 终止进程
            process.terminate()
            log_debug(f"python运行进程被用户中断")
            # 更新任务状态
            task_status[sch_uuid]["status"] = 0
            return jsonify({
                "errorCode": 0,
                "errorMsg": "终止该调度任务",
                "message": {}
            })
        else:
            return jsonify({
                "errorCode": 500,
                "errorMsg": "No running process found for task",
                "message": {}
            }), 500
    except Exception as e:
        log_error(f"终止任务状态出错: {e}")
        return jsonify({"errorCode": 500, "errorMsg": str(e), "message": {}}), 500
    


