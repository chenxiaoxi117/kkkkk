# -*- coding: utf-8 -*-
import argparse
import csv
import json
import logging
import threading
import time
from datetime import datetime
from generate_device_data import generate_device_data
from assign_nodes import assign_nodes
from generate_tasks import generate_tasks
from data_loader import DataLoader
from network_topology import NetworkTopology
from task_scheduler import TaskScheduler
from resource_monitor import ResourceMonitor

if __name__ == "__main__":
    # 生成设备数据

    # device_df = generate_device_data()
    #
    # # 分配节点并更新数据
    # updated_df = assign_nodes(
    #     device_df,
    #     cloud_edge_path="云边位置.csv",
    #     connections_path="节点连接关系表.csv"
    # )
    #
    # # 保存更新后的设备数据
    # updated_df.to_csv("终端设备数据.csv", index=False, encoding='utf_8_sig')
    # print("模拟终端已生成完毕")
    # # 生成任务数据（新增部分）
    # generate_tasks(
    #     updated_df,
    #     duration=10,  # 模拟时长，单位s
    #     output_path="生成任务记录.csv"
    # )
    print("模拟任务已生成完毕")
    # 初始化组件
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # 加载数据
    resources_path = '云边资源.csv'
    location_path = '云边位置.csv'
    ip_path = '节点ip表.csv'
    links_path = '节点连接关系表.csv'
    tasks_path = '生成任务记录.csv'
    data_loader = DataLoader(resources_path, location_path, ip_path, links_path, tasks_path)

    # 创建网络拓扑结构
    topology = NetworkTopology(data_loader.nodes, data_loader.links)

    # 初始化资源监控器
    monitor = ResourceMonitor(data_loader.nodes, data_loader.links)

    # 初始化任务调度器，并传递资源监控器实例
    scheduler = TaskScheduler(topology, data_loader, monitor)

    try:
        # 启动资源监控器
        monitor.start_monitoring()

        # 运行任务调度器
        scheduler.run_scheduler()

    except KeyboardInterrupt:
        logging.info("手动停止仿真")
    finally:
        # 停止资源监控
        monitor.stop_monitoring()
        # 关闭 CSV 文件
        scheduler.close_csv()