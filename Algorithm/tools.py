import csv
import ipaddress
import json
import os
import time
import numpy as np
import pandas as pd
import random

cloud_ip_ranges = [
    {'cloud_id': 5, 'start_ip': '123.112.0.0', 'end_ip': '123.112.255.255', 'current_ip': '123.112.0.0'},
    {'cloud_id': 6, 'start_ip': '123.114.0.0', 'end_ip': '123.114.255.255', 'current_ip': '123.114.0.0'},
    {'cloud_id': 15, 'start_ip': '124.112.0.0', 'end_ip': '124.112.255.255', 'current_ip': '124.112.0.0'},
    {'cloud_id': 16, 'start_ip': '124.114.0.0', 'end_ip': '124.114.255.255', 'current_ip': '124.114.0.0'},
    {'cloud_id': 24, 'start_ip': '128.112.0.0', 'end_ip': '128.112.255.255', 'current_ip': '128.112.0.0'},
    {'cloud_id': 36, 'start_ip': '129.112.0.0', 'end_ip': '129.112.255.255', 'current_ip': '129.112.0.0'},
    {'cloud_id': 39, 'start_ip': '130.112.0.0', 'end_ip': '130.112.255.255', 'current_ip': '130.112.0.0'},
]


def ip_to_int(ip):
    return int(ipaddress.IPv4Address(ip))


def int_to_ip(num):
    return str(ipaddress.IPv4Address(num))


def process_long_term_tasks(tasks, device_location, link, resource, link_bandwidth):
    """
    找到所有任务类型为长期占用资源的任务，调度到最近且资源充足的中心云，并保存调度结果。

    :param tasks: 任务表，包含任务的ID、设备ID、请求大小、核心需求等。
    :param device_location: 设备位置表，包含设备ID及其接入的网络设备ID。
    :param link: 网络链接表，包含源节点、目的节点及其时延。
    :param resource: 资源表，包含每个云的资源信息（RAM、存储、核心等），以及云的类型（中心云或边缘云）。
    :param link_bandwidth: 链路带宽表，包含链路ID及其可用带宽。
    :return: 更新后的任务表、资源表、带宽表和调度结果。
    """
    # 找出长期占用资源类型的任务
    long_term_types = {7, 8}
    long_term_task_mask = np.isin(tasks[:, 1], list(long_term_types))
    # long_term_task_mask = (tasks[:, 1] == 0)  # 第2列为 AppType
    type1_tasks = tasks[long_term_task_mask]
    results = np.empty((len(type1_tasks), 9), dtype=object)  # 增加1列记录失败原因或路径状态
    tasks = tasks[~long_term_task_mask]

    device_map = {row[0]: (row[4], row[6]) for row in device_location}  # device_id - (net_device_id, latency)
    link_map = {(row[0], row[3]): row[4:7] for row in link}  # (source_id, dest_id) - (trans_latency, path, sub_path)
    bandwidth_map = {row[0]: row[3] for row in link_bandwidth}  # segment -> bandwidth
    # 负载信息
    history_map = np.zeros(len(resource), dtype=int)

    for idx, task in enumerate(type1_tasks):
        task_id, task_type = task[0], task[1]
        device_id, request_size, bandwidth_size, max_latency, task_length, core_demand = task[2:8]
        bandwidth_sufficient = True
        min_weight = float('inf')
        selected = -1
        best_path, best_sub_path, best_total_latency = None, None, None
        insufficient_segment = None

        # 查找设备的网络 ID（可以直接从字典中获取）
        if device_id not in device_map:
            results[idx] = [task_id, device_id, 'No Device Found', 'N/A', False, 'N/A', 'N/A', task_type, 'N/A']
            continue
        net_device_id, net_device_latency = device_map[device_id]

        for i, cloud in enumerate(resource):
            if cloud[2] != 0:  # 确保是中心云
                continue
            dest_id = cloud[0]
            if (net_device_id, dest_id) not in link_map:
                continue  # 无法找到链路
            transmission_latency, path, sub_path = link_map[(net_device_id, dest_id)]
            computation_latency = task_length / cloud[6]
            total_latency = transmission_latency + computation_latency + net_device_latency

            # 检查资源和带宽是否足够
            if cloud[7] >= request_size and cloud[8] >= request_size and total_latency <= max_latency:
                # 检查路径带宽
                # 提取并解析 sub_path成 ['beijing_man1-beijing_core1', 'beijing_core1-beijing_cloud1']
                segments = sub_path.strip('[]').split('],[')
                for segment in segments:
                    if bandwidth_map.get(segment, 0) < bandwidth_size:
                        bandwidth_sufficient = False
                        insufficient_segment = segment
                        break
                if not bandwidth_sufficient:
                    continue  # 带宽不足，跳过该节点
                score = (history_map[i] + 1) * total_latency
                if score < min_weight:
                    min_weight = score
                    selected = i
                    best_path, best_sub_path = path, sub_path
                    best_total_latency = total_latency

        if selected != -1 and bandwidth_sufficient:
            allocated_ip = None
            # 分配公网 ip
            for ip_range in cloud_ip_ranges:
                if ip_range['cloud_id'] == resource[selected, 0]:  # 匹配到对应的云
                    start_ip = ip_to_int(ip_range['start_ip'])
                    end_ip = ip_to_int(ip_range['end_ip'])
                    # 随机挑选一个IP
                    allocated_ip = int_to_ip(random.randint(start_ip, end_ip))
                    # current_ip = ip_to_int(ip_range['current_ip'])
                    # end_ip = ip_to_int(ip_range['end_ip'])
                    # if current_ip <= end_ip:
                    #     allocated_ip = int_to_ip(current_ip)
                    #     ip_range['current_ip'] = int_to_ip(current_ip + 1)  # 更新下一个可用 IP
            # 更新历史负载表
            history_map[selected] += 1
            # 更新资源表
            resource[selected, 7] -= request_size
            resource[selected, 8] -= request_size
            resource[selected, 5] -= core_demand
            # 更新带宽表
            for segment in best_sub_path.strip('[]').split('],['):  # 遍历路径上的每段链路
                link_bandwidth[link_bandwidth[:, 0] == segment, 3] -= bandwidth_size

            results[idx] = [task_id, device_id, net_device_id, resource[selected, 0],
                            True, best_path, best_total_latency, task_type, allocated_ip]
        else:
            failure_reason = f'Bandwidth Insufficient on Segment {insufficient_segment}' if not bandwidth_sufficient else 'No Suitable Node'
            results[idx] = [task_id, device_id, net_device_id, failure_reason,
                            False, 'N/A', 'N/A', task_type, 'N/A']

    return tasks, resource, link_bandwidth, results


def save_to_csv(results, filename=None, success_rate=None, elapsed_time=None):
    headers = ["Task ID", "Device ID", "Source Node", "Destination Node",
               "Success", "Path", "Latency", "Task type", "IP Allocation "]

    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerow(headers)
        writer.writerows(results)

        # 添加任务成功率和运行时间到最后
        if success_rate is not None and elapsed_time is not None:
            writer.writerow([])
            writer.writerow(["Task Success Rate", f"{success_rate:.2%}"])
            writer.writerow(["Elapsed Time", f"{elapsed_time:.2f} seconds"])


def write_log(log_file, algorithm, success_rate, elapsed_time, utilization):
    """
    将运行结果和资源利用率写入日志文件。
    """
    with open(log_file, mode='a') as f:
        log_entry = (
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Algorithm: {algorithm}\n"
            f"Task Success Rate: {success_rate:.2%}\n"
            f"Elapsed Time: {elapsed_time:.2f} seconds\n"
        )
        f.write(log_entry)

        # 写入每个节点的资源利用率
        f.write("Resource Utilization:\n")
        for node in utilization:
            f.write(
                f"  ID: {node['ID']}, Name: {node['Name']}, Type: {node['Type']}, "
                f"RAM Utilization: {node['RAM Utilization']:.2%}, "
                f"Storage Utilization: {node['Storage Utilization']:.2%}\n"
            )
        f.write("\n")
    # print(f"运行结果和资源利用率已记录到日志文件: {log_file}")


def calculate_resource_utilization_GA(resource, ram_utilization, storage_utilization):
    """
    计算每个云节点的资源利用率（内存和存储）。
    """
    utilization = []
    for i in range(len(resource)):
        utilization.append({
            "ID": resource[i, 0],
            "Name": resource[i, 1],
            "Type": resource[i, 2],
            "RAM Utilization": ram_utilization[i],
            "Storage Utilization": storage_utilization[i]
        })
    return utilization


def calculate_resource_utilization(initial_resource, resource):
    """
    计算每个云节点的资源利用率（内存和存储）。
    """
    utilization = []
    total_ram_use = 0
    total_storage_use = 0
    initial_total_ram = np.sum(initial_resource[:, 7])  # 初始总RAM
    initial_total_storage = np.sum(initial_resource[:, 8])  # 初始总Storage
    for i in range(len(resource)):
        initial_ram = initial_resource[i, 7]
        remaining_ram = resource[i, 7]
        ram_utilization = (initial_ram - remaining_ram) / initial_ram if initial_ram > 0 else 0
        initial_storage = initial_resource[i, 8]
        remaining_storage = resource[i, 8]
        storage_utilization = (initial_storage - remaining_storage) / initial_storage if initial_storage > 0 else 0
        total_ram_use += (initial_ram - remaining_ram)
        total_storage_use += (initial_storage - remaining_storage)
        utilization.append({
            "ID": resource[i, 0],
            "Name": resource[i, 1],
            "Type": resource[i, 2],
            "RAM Utilization": ram_utilization,
            "Storage Utilization": storage_utilization,
        })
    ram_usage_rate = total_ram_use / initial_total_ram
    storage_usage_rate = total_storage_use / initial_total_storage
    return utilization, ram_usage_rate, storage_usage_rate


def calculate_link_band_utilization(initial_link_band, link_band, link_band_finish_first):
    """
    计算每个云节点的带宽利用率。
    """
    for i, connection in enumerate(link_band):
        # 构建连接名称的键
        key = connection[0]
        if key in link_band_finish_first:
            link_band[i, 3] = link_band_finish_first[key]
    utilization = []
    for i in range(len(link_band)):
        initial_linkband = initial_link_band[i, 3]
        remaining_linkband = link_band[i, 3]
        link_band_utilization = (initial_linkband - remaining_linkband) / initial_linkband if initial_linkband > 0 else 0
        utilization.append({
            "id": int(i + 1),
            "aNodeId": link_band[i, 1],
            "zNodeId": link_band[i, 2],
            "link_band_utilization": link_band_utilization,
        })
    return utilization


def calculate_link_band_utilization_GA(initial_link_band, link_band):
    """
    GA计算每个云节点的带宽利用率。
    """
    utilization = []
    for i in range(len(link_band)):
        initial_linkband = initial_link_band[i, 3]
        remaining_linkband = link_band[i, 3]
        link_band_utilization = (initial_linkband - remaining_linkband) / initial_linkband if initial_linkband > 0 else 0
        utilization.append({
            "id": int(i + 1),
            "aNodeId": link_band[i, 1],
            "zNodeId": link_band[i, 2],
            "link_band_utilization": link_band_utilization,
        })
    return utilization


def save_link_band(results, filename):
    """
    将带宽利用率结果保存为CSV文件。

    :param results: list，每个元素是一个包含链路带宽利用率信息的字典。
    :param filename: str，保存的CSV文件名，默认为'link_band_utilization.csv'。
    """
    # 提取字典的键作为CSV的表头
    headers = results[0].keys() if results else ["id", "aNodeId", "zNodeId", "link_band_utilization"]

    # 写入CSV文件
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)

        # 写入表头
        writer.writeheader()
        # 写入数据
        writer.writerows(results)

    # print(f"Results successfully saved to {filename}")

def save_resource_consumption(initial_resource, resource, filename):
    """
    保存每个云节点的资源消耗统计到 CSV 文件。
    """
    ram_consumed = initial_resource[:, 7] - resource[:, 7]  # RAM 消耗
    storage_consumed = initial_resource[:, 8] - resource[:, 8]  # 存储消耗

    consumption_df = pd.DataFrame({
        "ID": resource[:, 0],
        "Name": resource[:, 1],
        "Type": resource[:, 2],
        "Initial RAM": initial_resource[:, 7],
        "Remaining RAM": resource[:, 7],
        "RAM Consumed": ram_consumed,
        "Initial Storage": initial_resource[:, 8],
        "Remaining Storage": resource[:, 8],
        "Storage Consumed": storage_consumed,
    })

    consumption_df.to_csv(filename, index=False)
    # print(f"资源消耗统计已保存为 {filename}")


def save_updated_resource(resource, filename):
    """
    保存更新后的资源表为 CSV 文件。
    """
    columns = ["ID", "name", "type", "longitude", "latitude", "cores", "flops", "ram", "storage"]
    updated_df = pd.DataFrame(resource, columns=columns)
    updated_df.to_csv(filename, index=False)
    # print(f"更新后的资源表已保存为 {filename}")


def scheduling_message_to_json(utilization, link_band_list, scheduling_message):
    # 模拟生成调度结果信息
    sch_uuid = "default_uuid"
    # 将 numpy 数组转换为列表
    # 处理链路数据，计算带宽利用率
    mapping = read_mapping_from_excel()
    # 使用顺序生成链路 ID
    for idx, link in enumerate(link_band_list):  # 从1开始计数
        id, a_node, z_node, bandwidth_utilization = link['id'], link['aNodeId'], link['zNodeId'], link[
            'link_band_utilization']
        # 计算带宽利用率
        # 获取中文名称
        a_node_name = mapping.get(a_node, a_node)  # 如果没找到则保留原ID
        z_node_name = mapping.get(z_node, z_node)  # 如果没找到则保留原ID
        # 生成链路指标
        link_band_list[idx]["aNodeName"] = a_node_name
        link_band_list[idx]["zNodeName"] = z_node_name
        link_band_list[idx]["link_band_utilization"] = round(bandwidth_utilization * 100, 2)

    message = {
        sch_uuid: {
            "schedulingTime": round(scheduling_message[2]),  # 转换为秒
            "indicators": {
                "totalLoadCapacity": scheduling_message[0],  # 任务长度
                "initialSuccessRate": round(scheduling_message[1] * 100, 2),  # 成功率百分比
                "schedulingRounds": scheduling_message[3],  # 调度次数
                "cpuUtilization": min(round(scheduling_message[4] * 100 + 0.5, 2), 100),
                "memoryUtilization": round(scheduling_message[4] * 100, 2),
                "storageUtilization": round(scheduling_message[5] * 100, 2)
            },
            "nodeMetrics": [
                {
                    "id": node["Name"],
                    "name": mapping.get(node["Name"], node["Name"]),  # 替换 assigned,
                    "cpuUtilization": min(round(node["RAM Utilization"] * 100 + 0.5, 3), 100),
                    "memoryUtilization": round(node["RAM Utilization"] * 100, 3),
                    "storageUtilization": round(node["Storage Utilization"] * 100, 3),
                    "maxLoadCapacity": 1000  # 假设值
                }
                for node in utilization
            ],
            "linkMetrics": link_band_list  # 使用动态生成的链路带宽数据
        }
    }

    # 将结果转为 JSON 格式并返回
    json_data = json.dumps(message, ensure_ascii=False, indent=4)
    return json_data


# 替换拼音为中文的映射字典
def read_mapping_from_excel():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if 'app_interface' in current_dir:
        file_path = os.path.join(current_dir, 'node_link.xlsx')
    else:
        file_path = os.path.join(current_dir, 'app_interface', 'data', 'node_link.xlsx')
    df = pd.read_excel(file_path, sheet_name='node')
    mapping = dict(zip(df['名称'], df['节点']))
    return mapping


# 路径扩展函数
def expand_path(path):
    expanded_path = []
    if len(path) == 2:
        expanded_path.append(path[0])
        expanded_path.append(path[0] + "_rand")
        expanded_path.append(path[0])
        expanded_path.append(path[-1])
    else:
        for i in range(len(path) - 1):  # 2 0.1 ABC a-a_rand-b_rand-b-c
            expanded_path.append(path[i])  # 添加当前节点
            if path[i + 1] != path[-1]:
                expanded_path.append(path[i] + "_rand")  # 添加第一个 rand
                expanded_path.append(path[i + 1] + "_rand")  # 添加第二个 rand
        expanded_path.append(path[-1])  # 最后一个节点不扩展，直接添加
    return expanded_path


# 修改 task_results_to_json 函数，加入拼音替换
def task_results_to_json(data):
    # 将每一行数据转换为所需的字典格式
    result = {}
    mapping = read_mapping_from_excel()
    data = data[data[:, 1].argsort()]  # 根据第二列进行一下排序
    task_type_chinese = ["低时延", "大带宽", "高算力", "低时延+高算力", "低时延+大带宽", "低时延+高算力+大带宽",
                         "申请虚拟机", "长时间占用网络资源", "服务型任务"]
    for row in data:
        # 提取相关字段
        task_type = int(row[7])
        device_id = int(row[1])
        origin = row[5].split('-')[0]
        assigned = row[5].split('-')[-1]
        path = row[5].split('-')  # A-A_rand-B_rand-B-B_rand-C_rand-C-D
        path = expand_path(path)
        latency = row[6]
        status = 1 if row[4] else 0

        # 替换拼音为中文
        origin = mapping.get(origin, origin)  # 替换 origin
        assigned = mapping.get(assigned, assigned)  # 替换 assigned
        path = [mapping.get(item, item) for item in path]  # 替换 path 中的每个节点

        # 创建设备数据字典
        device_data = {
            "deviceId": device_id,
            "attribute": task_type_chinese[task_type - 1],
            "origin": origin,
            "assigned": assigned,
            "path": path,
            "latency": latency,
            "status": status
        }

        # 使用 sch_uuid 作为 key
        sch_uuid = "default_uuid"
        if sch_uuid not in result:
            result[sch_uuid] = []
        result[sch_uuid].append(device_data)

    # 将结果转换为 JSON 字符串
    json_data = json.dumps(result, ensure_ascii=False, indent=4)
    return json_data
