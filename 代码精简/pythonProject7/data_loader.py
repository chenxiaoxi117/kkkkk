# -*- coding: utf-8 -*-
import pandas as pd
import re
import logging

class DataLoader:
    def __init__(self, resources_path, location_path, ip_path, links_path, tasks_path):
        self.nodes = self.load_nodes(resources_path, location_path, ip_path)
        self.links = self.load_links(links_path)
        self.tasks = self.load_tasks(tasks_path)
        self.all_tasks = self.tasks.copy()  # 存储所有原始任务

    @staticmethod
    def parse_time(t_str):
        """修正后的时间解析逻辑"""
        try:
            # 匹配时分秒结构，支持小数点
            pattern = r'(?:(\d+)分)?(?:(\d+\.?\d*)秒)?(?:([0-9.]+)毫秒)?'
            matches = re.search(pattern, t_str)

            if not matches:
                return 0.0

            minutes = float(matches.group(1) or 0)
            seconds = float(matches.group(2) or 0)
            milliseconds = float(matches.group(3) or 0) / 1000

            total = minutes * 60 + seconds + milliseconds
            return round(total, 3)  # 保留3位小数精度
        except:
            return 0.0

    def load_nodes(self, resources_path, location_path, ip_path):
        """加载并标准化云边节点数据（修复列引用错误）"""
        nodes = {}

        # 加载云边资源
        resources_df = pd.read_csv(resources_path)
        for _, row in resources_df.iterrows():
            clean_name = row["name"].replace('_', '-')
            node_id = clean_name
            nodes[node_id] = {
                "type": int(row["type"]),
                "core_capacity": int(row["cores"]),
                "ram_capacity": int(row["ram"]),
                "storage_capacity": int(row["storage"]),
                "core_available": int(row["cores"]),
                "ram_available": int(row["ram"]),
                "storage_available": int(row["storage"]),
                "location": (float(row["longitude"]), float(row["latitude"])),
                "flops": int(row["flops"])
            }
            logging.info(
                f"加载节点 {node_id}，核心容量: {nodes[node_id]['core_capacity']}，内存容量: {nodes[node_id]['ram_capacity']}，存储容量: {nodes[node_id]['storage_capacity']}")
            # 验证资源容量合理性
            if nodes[node_id]["core_capacity"] <= 0:
                raise ValueError(f"节点 {node_id} 核心容量无效")
            if nodes[node_id]["ram_capacity"] <= 0:
                raise ValueError(f"节点 {node_id} 内存容量无效")
            if nodes[node_id]["storage_capacity"] <= 0:
                raise ValueError(f"节点 {node_id} 存储容量无效")

        # 加载节点IP表
        try:
            ip_df = pd.read_csv(ip_path, encoding='gbk')  # 尝试使用 gbk 编码
        except UnicodeDecodeError:
            try:
                ip_df = pd.read_csv(ip_path, encoding='gb2312')  # 尝试使用 gb2312 编码
            except UnicodeDecodeError:
                logging.error(f"无法解码文件 {ip_path}，请检查文件编码格式")
                return nodes

        for _, row in ip_df.iterrows():
            node_id = row["节点名称"].replace('_', '-')
            if node_id not in nodes:
                nodes[node_id] = {
                    "type": None,
                    "core_capacity": 0,
                    "ram_capacity": 0,
                    "storage_capacity": 0,
                    "core_available": 0,
                    "ram_available": 0,
                    "storage_available": 0,
                    "location": (0, 0),
                    "flops": 0
                }

        return nodes

    def load_links(self, path):
        """加载并标准化链路数据（增强格式校验）"""
        links = {}
        df = pd.read_csv(path)

        for _, row in df.iterrows():
            try:
                # 验证节点ID格式（不允许包含连字符）
                src = row["source_id"].replace('_', '-')
                dst = row["destination_id"].replace('_', '-')

                # 生成标准化链路ID（强制小写连字符）
                link_id = f"{src}-{dst}"

                # 处理数值转换（兼容带逗号的格式）
                def clean_value(value):
                    try:
                        return int(value.replace(',', ''))
                    except:
                        return 0.0

                links[link_id] = {
                    "bandwidth": clean_value(row["bandwidth"])/1000,
                    "latency": float(row["lantency"]/1000),
                    "used_bandwidth": 0,
                    "reverse_bandwidth": clean_value(row["bandwidth"])/1000,
                    "reverse_latency": float(row["lantency"])
                }
                # logging.info(f"加载链路 {link_id}，带宽: {links[link_id]['bandwidth']}，延迟: {links[link_id]['latency']}")
            except KeyError as e:
                logging.error(f"链路数据缺失必要字段: {str(e)}")
                continue

        return links

    def load_tasks(self, path):
        """加载并标准化任务数据"""
        df = pd.read_csv(path)
        tasks = []
        Magnification = 28  # 任务数量倍率
        for _, row in df.iterrows():
            # 标准化接入节点ID格式
            access_node = row["接入节点"].strip().lower().replace('_', '-')
            task = {
                "TaskID": row["TaskID"],
                "AppType": row["AppType"].lower(),
                "DeviceID": row["DeviceID"],
                "RequestSizeGB": Magnification * row["RequestSize"]/1024,  # Mbps转Gbps
                "MaxLatencySec": row["Max Latency"],
                "DataLengthGB": Magnification * row["Length"] / (1024 * 1024 * 1024),  # bps转Gbps
                "CoreRequirement": int(Magnification * int(row["core"])),
                "AccessNode": access_node,
                "GenTime": self.parse_time(row["任务生成时间"]),
                "SendTime": self.parse_time(row["任务发送时间"]),
                "Status": "待调度",
                "AssignedNode": None,
                "StartTime": None,
                "EndTime": None
            }
            # logging.info(f"加载任务 {task['TaskID']}，请求大小: {task['RequestSizeGB']} Gbps，核心需求: {task['CoreRequirement']} 核")
            tasks.append(task)

        # 按发送时间排序（仿真准备）
        tasks.sort(key=lambda x: x['SendTime'])
        return tasks