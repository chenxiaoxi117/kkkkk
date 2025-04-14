import csv
import os
import time
import argparse
import numpy as np
import pandas as pd
import json
from concurrent.futures import ProcessPoolExecutor
import torch
import torch.nn as nn
from app_interface.data.to_json import *
import joblib
from tools import save_resource_consumption, save_updated_resource, save_to_csv, calculate_resource_utilization, \
    write_log


# 定义神经网络模型结构（与训练时的结构相同）
class SimpleNN(nn.Module):
    def __init__(self):
        super(SimpleNN, self).__init__()
        self.fc1 = nn.Linear(5, 64)  # 输入层到隐藏层（5个特征）
        self.fc2 = nn.Linear(64, 32)  # 隐藏层
        self.fc3 = nn.Linear(32, 1)  # 输出层（1个延迟裕度）

    def forward(self, x):
        x = torch.relu(self.fc1(x))  # ReLU 激活函数
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)  # 不加激活函数，回归问题
        return x


# # 加载训练好的模型
# model = SimpleNN()
# model.load_state_dict(torch.load('deep_learning/decision_tree_model.pt'))
# model.eval()  # 切换到评估模式


def trade_off(tasks, device_location, link, resource, history_map, link_bandwidth):
    """
    折衷算法：根据节点类型和资源负载选择最优节点分配任务，同时检查路径带宽是否满足需求。
    """
    print("Trade-off Algorithm Start")
    time_start = time.time()
    net_device_encoder = joblib.load('deep_learning/net_device_encoder.pkl')

    model = SimpleNN()  # 加载模型
    model.load_state_dict(torch.load('deep_learning/simple_nn_model.pt'))
    model.eval()  # 切换到评估模式

    num_tasks = len(tasks)
    results = np.empty((num_tasks, 8), dtype=object)  # 增加1列记录失败原因或路径状态

    # 提前构建链路索引以优化查找
    link_index = {}
    for row in link:
        source_id, dest_id = row[0], row[3]
        if source_id not in link_index:
            link_index[source_id] = {}
        link_index[source_id][dest_id] = row[4:7]  # 存储传输延迟、路径信息（包括sub_path）

    # 进行批量预测
    input_features = []
    for task in tasks:
        task_type = task[1]
        task_id, device_id, request_size, task_length, max_latency = task[0], task[2], task[3], task[6], task[5]

        device_row = device_location[device_location[:, 0] == device_id]
        # if device_row.size == 0:
        #     results[idx] = [task_id, device_id, 'No Device Found', 'N/A', False, 'N/A', 'N/A', task_type]
        #     continue

        net_device_id = device_row[0, 4]
        net_device_id_encoded = net_device_encoder.transform([str(net_device_id)])[0]
        input_features.append([net_device_id_encoded, request_size, task_length, max_latency, task_type])

    input_features_tensor = torch.tensor(input_features, dtype=torch.float32)
    with torch.no_grad():
        predicted_delay_margins = model(input_features_tensor).numpy()
    task_priority = []
    task_priority = [(predicted_delay_margin, request_size, idx, task) for idx, (predicted_delay_margin, task) in
                     enumerate(zip(predicted_delay_margins, tasks))]
    task_priority.sort(key=lambda x: (x[1], x[0]))  # 排序依据：延迟裕度越小，request_size越小优先级越高

    sorted_tasks = [task[3] for task in task_priority]
    print("任务排序已完成")
    time_end = time.time()
    print("排序时间, Time Cost:", time_end - time_start)

    # for idx, task in enumerate(tasks):
    #     task_type = task[1]
    #     task_id, device_id, request_size, task_length, max_latency = task[0], task[2], task[3], task[6], task[5]

    #     # 查找设备的网络 ID
    #     device_row = device_location[device_location[:, 0] == device_id]
    #     if device_row.size == 0:
    #         results[idx] = [task_id, device_id, 'No Device Found', 'N/A', False, 'N/A', 'N/A', task_type]
    #         continue
    #     net_device_id = device_row[0, 4]
    #     net_device_latency = device_row[0, 6]
    #     # 进行编码：将任务的输入特征编码为数字

    #     net_device_id_encoded = net_device_encoder.transform([str(net_device_id)])[0]
    #     input_features = torch.tensor([[net_device_id_encoded, request_size, task_length, max_latency, task_type]], dtype=torch.float32)

    # # 遍历所有节点资源，找到满足时延条件的云节点
    # best_total_latency = float('inf')
    # best_path = None
    # for i, cloud in enumerate(resource):
    #     destination_id = cloud[0]
    #     if net_device_id not in link_index or destination_id not in link_index[net_device_id]:
    #         continue  # 无法找到链路

    #     # 提取链路信息
    #     transmission_latency, path, sub_path = link_index[net_device_id][destination_id]
    #     computation_latency = task_length / cloud[6]
    #     total_latency = transmission_latency + computation_latency + net_device_latency

    #     if total_latency <= max_latency:
    #         # 选取当前链路作为最优链路（最小时延）
    #         if total_latency < best_total_latency:
    #             best_total_latency = total_latency
    #             best_path = path  # 记录最佳路径

    # if best_total_latency == float('inf'):
    #     results[idx] = [task_id, device_id, 'No Suitable Link', 'N/A', False, 'N/A', 'N/A', task_type]
    #     continue

    # # 计算延迟裕度
    # delay_margin = max_latency - best_total_latency
    # task_priority.append((delay_margin, request_size, idx, task))  # 存储任务的延迟裕度、请求大小、任务索引和任务信息
    # input_features = torch.tensor([[net_device_id, request_size, task_length, max_latency, task_type]], dtype=torch.float32)

    # 进行预测
    # with torch.no_grad():  # 关闭梯度计算，提高效率
    #     predicted_delay_margin = model(input_features).item()  # 获取预测的延迟裕度

    # task_priority.append((predicted_delay_margin, request_size, idx, task))
    # 按延迟裕度和请求大小排序任务
    # task_priority.sort(key=lambda x: (x[1], x[0]))  # 排序依据：延迟裕度越小，request_size越小优先级越高

    # 重新排序任务
    # sorted_tasks = [task[3] for task in task_priority]
    def save_sorted_tasks_to_csv(sorted_tasks, filename="sorted_tasks_deep_learning.csv"):
        """
        将排序后的任务导出到 CSV 文件。
        :param sorted_tasks: 排序后的任务列表
        :param filename: 要保存的文件名
        """
        # 定义 CSV 列头
        headers = ["Task ID", "Device ID", "Request Size", "Task Length", "Max Latency", "Task Type"]

        # 打开 CSV 文件并写入
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file, lineterminator='\n')
            writer.writerow(headers)

            # 遍历排序后的任务列表并写入任务信息
            for task in sorted_tasks:
                task_id, device_id, request_size, task_length, max_latency = task[0], task[2], task[3], task[6], task[5]
                task_type = task[1]
                writer.writerow([task_id, device_id, request_size, task_length, max_latency, task_type])

        print(f"排序后的任务已保存为 {filename}")

    # save_sorted_tasks_to_csv(sorted_tasks, filename="sorted_tasks_deep_learning.csv")

    for idx, task in enumerate(sorted_tasks):
        task_type = task[1]
        task_id, device_id, request_size, task_length, max_latency = task[0], task[2], task[3], task[6], task[5]
        selected = -1
        min_weight = float('inf')
        best_path, best_total_latency = None, None
        bandwidth_sufficient = True
        insufficient_segment = None

        # 查找设备的网络 ID
        device_row = device_location[device_location[:, 0] == device_id]
        if device_row.size == 0:
            results[idx] = [task_id, device_id, 'No Device Found', 'N/A', False, 'N/A', 'N/A', task_type]
            continue
        net_device_id = device_row[0, 4]
        net_device_latency = device_row[0, 6]

        # 遍历所有节点资源
        for i, cloud in enumerate(resource):
            destination_id = cloud[0]
            if net_device_id not in link_index or destination_id not in link_index[net_device_id]:
                continue  # 无法找到链路

            # 提取链路信息
            transmission_latency, path, sub_path = link_index[net_device_id][destination_id]
            computation_latency = task_length / cloud[6]
            total_latency = transmission_latency + computation_latency + net_device_latency

            # 检查资源和带宽是否足够
            if cloud[7] >= request_size and cloud[8] >= request_size and total_latency <= max_latency:
                # 检查路径带宽
                bandwidth_sufficient = True
                # 提取并解析 sub_path
                segments = sub_path.strip('[]').split(
                    '],[')  # 解析成 ['beijing_man1-beijing_core1', 'beijing_core1-beijing_cloud1']
                for segment in segments:
                    bandwidth_row = link_bandwidth[link_bandwidth[:, 0] == segment]
                    if bandwidth_row.size == 0 or bandwidth_row[0, 3] < request_size:
                        bandwidth_sufficient = False
                        insufficient_segment = segment
                        break
                if not bandwidth_sufficient:
                    continue  # 带宽不足，跳过该节点

                # 确定权重
                weight = 1.8 if cloud[2] == 0 else 1.2
                score = (history_map[i] + 1) * weight * total_latency
                if score < min_weight:
                    min_weight = score
                    selected = i
                    best_path = path
                    best_total_latency = total_latency

        # 更新任务分配结果
        if selected != -1 and bandwidth_sufficient:
            history_map[selected] += 1
            resource[selected, 7] -= request_size
            resource[selected, 8] -= request_size

            # 更新带宽表
            for segment in best_path.strip('[]').split('],['):  # 遍历路径上的每段链路
                link_bandwidth[link_bandwidth[:, 0] == segment, 3] -= request_size

            results[idx] = [task_id, device_id, net_device_id, resource[selected, 0],
                            True, best_path, best_total_latency, task_type]
        else:
            failure_reason = f'Bandwidth Insufficient on Segment {insufficient_segment}' if not bandwidth_sufficient else 'No Suitable Node'
            results[idx] = [task_id, device_id, net_device_id, failure_reason,
                            False, 'N/A', 'N/A', task_type]

    return results


def calculate_success_rate(results):
    """
    计算任务分配的成功率。
    :param results: 调度结果矩阵，每行表示一个任务的分配结果，第 4 列（索引 4）为 Success 字段。
    :return: 成功率 (成功任务数 / 总任务数)
    """
    total_tasks = len(results)
    successful_tasks = sum(1 for result in results if result[4] is True)  # 统计 Success 为 True 的任务数
    success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0
    return success_rate


if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 定义数据文件夹和结果文件夹
    data_dir = os.path.join(current_dir, 'data')
    result_dir = os.path.join(current_dir, 'result')
    os.makedirs(result_dir, exist_ok=True)  # 如果结果文件夹不存在，创建它

    device_location_path = os.path.join(data_dir, 'task/Device_location_zhongduanfuneng.csv')
    link_path = os.path.join(data_dir, 'resource/Link.csv')
    resource_path = os.path.join(data_dir, 'resource/resource_10w_1000.csv')
    tasks_path = os.path.join(data_dir, 'task/task_data_10w_1.csv')
    link_band_path = os.path.join(data_dir, 'resource/link_band.csv')

    # 结果文件路径
    log_file = os.path.join(result_dir, "log.txt")
    resource_consumption_file = os.path.join(result_dir, "resource_consumption.csv")
    updated_resource_file = os.path.join(result_dir, "updated_resource.csv")
    results_file = os.path.join(result_dir, "tradeoff_results.csv")

    # 加载数据文件
    device_location = pd.read_csv(device_location_path).to_numpy()
    link = pd.read_csv(link_path).to_numpy()
    resource = pd.read_csv(resource_path).to_numpy()
    tasks = pd.read_csv(tasks_path).to_numpy()

    link_band = pd.read_csv(link_band_path).to_numpy()

    initial_resource = resource.copy()
    history_map = np.zeros(len(resource), dtype=int)

    # 执行调度算法
    start_time = time.time()
    # tasks_with_results = trade_off(tasks, device_location, link, resource, history_map)
    tasks_with_results = trade_off(tasks, device_location, link, resource, history_map, link_band)
    end_time = time.time()
    # 计算任务成功率和运行时间
    success_rate = calculate_success_rate(tasks_with_results)
    elapsed_time = end_time - start_time

    # print(f"任务成功率: {success_rate:.2%}")
    # print(f"程序运行时间: {elapsed_time:.2f} 秒")

    # 保存结果
    save_updated_resource(resource, filename=updated_resource_file)
    save_resource_consumption(initial_resource, resource, filename=resource_consumption_file)
    save_to_csv(tasks_with_results, filename=results_file, success_rate=success_rate, elapsed_time=elapsed_time)
    # 计算资源利用率并写日志
    utilization = calculate_resource_utilization(initial_resource, resource)
    write_log(log_file, "trade_off_improved", success_rate, elapsed_time, utilization)

    # """这个方法可以把这些json输出存到内存缓冲区里面，而不会直接出现在控制台上"""
    # # 创建一个内存缓冲区
    # output_buffer = io.StringIO()
    # # 将标准输出重定向到内存缓冲区
    # sys.stdout = output_buffer

    # # 获取数据
    # task_results_to_json = task_results_to_json(tasks_with_results)
    # print(task_results_to_json)
    # print("__SEPARATOR__")  # 在两个 JSON 之间添加分隔符
    # scheduling_message_to_josn = scheduling_message_to_json(len(tasks), success_rate, elapsed_time, utilization, link_band)
    # print(scheduling_message_to_josn)
