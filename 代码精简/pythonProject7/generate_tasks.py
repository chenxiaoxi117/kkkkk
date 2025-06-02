# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random


## 本文件为任务生成逻辑


TASK_CONFIG = {
    "低时延": {
        "prob": 0.4,
        "delay": 0.3,  # 300ms
        "bw": 10,  # mbps
        "flops": 5e9, #bit
        "core": 1,
        "devices": ["传感器"]
    },
    "高算力": {
        "prob": 0.6,
        "delay": 10,
        "bw": 10,
        "flops": 1.5e11,
        "core": 40,
        "devices": ["PC"]
    },
    "大带宽": {
        "prob": 0.4,
        "delay": 3,
        "bw": 200,
        "flops": 5e9,
        "core": 2,
        "devices": ["PC", "手机", "laptop"]
    },
    "低需求": {
        "prob": 0.4,
        "delay": 1,
        "bw": 10,
        "flops": 5e8,
        "core": 1,
        "devices": ["传感器", "PC", "手机", "laptop"]
    },
    "长时间占用网络资源": {
        "prob": 0.4,
        "delay": 2,
        "bw": 50,
        "flops": 5e9,
        "core": 2,
        "devices": ["传感器", "laptop"]
    }
}

DEVICE_TASK_MAP = {
    "传感器": ["低时延", "低需求", "长时间占用网络资源"],
    "手机": ["大带宽", "低需求"],
    "PC": ["高算力", "大带宽", "低需求"],
    "laptop": ["高算力", "大带宽", "低需求"]
}


def format_time_delta(delta_td):
    """将timedelta转换为xx分xx秒xxx.xxx毫秒格式"""
    total_seconds = delta_td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    milliseconds = round((total_seconds - int(total_seconds)) * 1000, 3)
    return f"{minutes:02d}分{seconds:02d}秒{milliseconds:06.3f}毫秒"


def generate_tasks(device_df, duration=300, output_path="任务历史记录.csv"):
    tasks = []
    base_time = datetime.now()

    for _, device in device_df.iterrows():
        device_type = device["设备类型"]

        # 跳过不生成任务的设备
        if device_type in ["手机", "PC", "laptop"] and random.random() < 0.05:
            continue

        # 获取设备对应任务类型及生成策略
        if device_type not in DEVICE_TASK_MAP:
            continue

        # 确定生成时间序列
        time_points = generate_time_sequence(
            device_type,
            base_time,
            duration
        )

        # 生成每个时间点的任务
        for t in time_points:
            task_type = select_task_type(device_type)
            config = TASK_CONFIG[task_type]

            task = {
                "TaskID": f"{device['设备ID']}-{int(t.timestamp() * 1000)}",
                "AppType": task_type,
                "DeviceID": device["设备ID"],
                "RequestSize": config["bw"],
                "Max Latency": config["delay"],
                "Length": config["flops"],
                "core": config["core"],
                "任务生成时间": format_time_delta(t - base_time),
                "任务发送时间": format_time_delta(
                    (t + timedelta(seconds=device["接入时延"])/1000) - base_time ## 单位换算
                ),
                "接入节点": device["接入节点"]
            }
            tasks.append(task)

        # 按任务发送时间排序
    sorted_tasks = sorted(tasks, key=lambda x: x["任务发送时间"])

    # 保存并覆盖原有文件
    df = pd.DataFrame(sorted_tasks)
    df.to_csv(output_path, index=False, encoding="utf_8_sig")
    return sorted_tasks


def select_task_type(device_type):
    available_tasks = DEVICE_TASK_MAP[device_type]
    probs = [TASK_CONFIG[t]["prob"] for t in available_tasks]
    probs = np.array(probs) / sum(probs)  # 归一化
    return np.random.choice(available_tasks, p=probs)


def generate_time_sequence(device_type, base_time, duration):
    """生成时间序列"""
    if device_type == "传感器":
        interval = random.uniform(0.1, 5)  # 0.1-5秒间隔
        return [base_time + timedelta(seconds=i * interval)
                for i in range(int(duration / interval))]  ##按照固定时间间隔生成
    else:  # 手机/电脑等
        return [base_time + timedelta(seconds=random.uniform(0, duration))
                for _ in range(random.randint(1, 5))]  ##按照随机时间间隔生成