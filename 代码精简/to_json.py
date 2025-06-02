import json
import pandas as pd
import os


def scheduling_message_to_json(utilization, link_band, scheduling_message):
    # 模拟生成调度结果信息
    sch_uuid = "default_uuid"
    # 将 numpy 数组转换为列表
    link_band_list = link_band.tolist()
    # 处理链路数据，计算带宽利用率
    link_metrics = []
    mapping = read_mapping_from_excel()
    # 使用顺序生成链路 ID
    for idx, link in enumerate(link_band_list, start=1):  # 从1开始计数
        link_path, a_node, z_node, remaining_bandwidth, latency = link
        # 计算带宽利用率
        bandwidth_utilization = (100000 - remaining_bandwidth) / 100000 * 100  # 转换为百分比
        # 获取中文名称
        a_node_name = mapping.get(a_node, a_node)  # 如果没找到则保留原ID
        z_node_name = mapping.get(z_node, z_node)  # 如果没找到则保留原
        # 生成链路指标
        link_metrics.append({
            "id": int(idx),  # 确保链路ID是整数
            "aNodeId": a_node,  # 源节点
            "aNodeName": a_node_name,  # 源节点中文名称
            "zNodeId": z_node,  # 目的节点
            "zNodeName": z_node_name,  # 目的节点中文名称
            "bandwidthUtilization": round(bandwidth_utilization, 5)  # 带宽利用率，保留2位小数
        })

    message = {
        sch_uuid: {
            "schedulingTime": round(scheduling_message[2]),  # 转换为秒
            "indicators": {
                "totalLoadCapacity": scheduling_message[0],  # 任务长度
                "initialSuccessRate": round(scheduling_message[1] * 100, 4),  # 成功率百分比
                "schedulingRounds": scheduling_message[3],  # 调度次数
                "cpuUtilization": round(scheduling_message[4] * 100, 4),
                "memoryUtilization": round(scheduling_message[4] * 100, 4),
                "storageUtilization": round(scheduling_message[5] * 100, 4)
            },
            "nodeMetrics": [
                {
                    "id": node["Name"],
                    "name": mapping.get(node["Name"], node["Name"]),  # 替换 assigned,
                    "cpuUtilization": round(node["RAM Utilization"] * 100, 4),
                    "memoryUtilization": round(node["RAM Utilization"] * 100, 4),
                    "storageUtilization": round(node["Storage Utilization"] * 100, 4),
                    "maxLoadCapacity": 1000  # 假设值
                }
                for node in utilization
            ],
            "linkMetrics": link_metrics  # 使用动态生成的链路带宽数据
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
        file_path = os.path.join(current_dir, '..', 'data', 'node_link.xlsx')
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
    task_type_chinese = ["低时延", "大带宽", "高算力", "低时延+高算力", "低时延+高算力（大客户专线）",
                         "低时延+高算力+大带宽", "申请虚拟机（占用CPU、内存、存储）", "长时间占用网络资源", "需求不敏感任务（门禁卡、人脸验证等）"]
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
