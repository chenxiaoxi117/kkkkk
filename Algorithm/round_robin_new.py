import csv
import os
import time
import numpy as np
import pandas as pd
from app_interface.data.to_json import task_results_to_json, scheduling_message_to_json
from tools import *


def round_robin(tasks, device_location, link, resource, history_map, link_bandwidth):
    """
    轮询算法：按序号遍历任务，每个任务首先找到对应的 Net_device_id，
    然后筛选出可行的链路，找到负载最小的云节点，并检查时延和算力要求，
    满足要求的情况下，将任务分配给该云节点。
    """
    num_tasks = len(tasks)
    resource_copy = np.copy(resource)

    results = np.empty((num_tasks, 8), dtype=object)  # 初始化结果矩阵，7列分别对应每个字段
    device_map = {row[0]: (row[4], row[6]) for row in device_location}  # device_id - (net_device_id, latency)
    link_map = {(row[0], row[3]): row[4:7] for row in link}  # (source_id, dest_id) - (trans_latency, path, sub_path)
    bandwidth_map = {row[0]: row[3] for row in link_bandwidth}  # segment -> bandwidth

    for idx, task in enumerate(tasks):
        task_type = task[1]
        task_id = task[0]
        device_id = task[2]
        request_size = task[3]
        task_length = task[6]
        max_latency = task[5]
        bandwidth_size = task[4]
        selected = -1
        best_path, best_sub_path, best_total_latency = None, None, None
        best_total_latency = None
        bandwidth_sufficient = True
        insufficient_segment = None

        # 查找设备的网络 ID（可以直接从字典中获取）
        if device_id not in device_map:
            results[idx] = [task_id, device_id, 'No Device Found', 'N/A', False, 'N/A', 'N/A', task_type]
            continue
        net_device_id, net_device_latency = device_map[device_id]

        # 遍历所有资源节点，寻找符合条件的节点
        for i, cloud in enumerate(resource_copy):
            dest_id = cloud[0]
            if (net_device_id, dest_id) not in link_map:
                continue  # 无法找到链路

            # 提取链路信息
            transmission_latency, path, sub_path = link_map[(net_device_id, dest_id)]
            computation_latency = task_length / cloud[6]
            total_latency = transmission_latency + computation_latency + net_device_latency
            # 获取传输延迟和路径信息

            # 检查资源需求和总时延是否满足要求
            if cloud[7] >= request_size and cloud[8] >= request_size:
                if total_latency <= max_latency:
                    # 检查路径带宽
                    bandwidth_sufficient = True
                    segments = sub_path.strip('[]').split('],[')
                    for segment in segments:
                        if bandwidth_map.get(segment, 0) < bandwidth_size:
                            bandwidth_sufficient = False
                            insufficient_segment = segment
                            break
                    if not bandwidth_sufficient:
                        continue  # 带宽不足，跳过该节点
                    selected = i
                    best_path, best_sub_path = path, sub_path
                    best_total_latency = total_latency

        # 记录任务分配结果
        if selected != -1:
            history_map[selected] += 1
            success = True
            source_name = net_device_id
            destination_name = resource[selected, 0]
            resource_copy[selected, 7] -= request_size  # 更新已使用的资源
            resource_copy[selected, 8] -= request_size

            # 更新带宽表
            for segment in best_sub_path.strip('[]').split('],['):  # 遍历路径上的每段链路
                bandwidth_map[segment] -= bandwidth_size
            results[idx] = [task_id, device_id, net_device_id, resource_copy[selected, 0],
                            True, best_path, best_total_latency, task_type]
        else:
            failure_reason = f'Bandwidth Insufficient on Segment {insufficient_segment}' if not bandwidth_sufficient else 'No Suitable Node'
            results[idx] = [task_id, device_id, net_device_id, failure_reason, False, 'N/A', 'N/A', task_type]
    return results, resource_copy, bandwidth_map


def calculate_success_rate(results):
    """
    计算任务分配的成功率。
    """
    total_tasks = len(results)
    successful_tasks = sum(1 for result in results if result[4] is True)
    success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0
    return success_rate


def retry_failed_tasks(failed_tasks, device_location, link, resource, link_band, max_retries=3):
    """
    对失败任务进行重发调度，尝试最大重发次数。

    :param failed_tasks: 上一次调度失败的任务列表
    :param device_location: 设备位置表
    :param link: 链路表
    :param resource: 资源表
    :param max_retries: 最大重发次数
    :return: 所有重发后的调度结果
    """
    retry_results = []
    retry_count = 0

    while retry_count < max_retries and len(failed_tasks) > 0:
        # print(f"Retry Attempt {retry_count + 1} - Remaining Tasks: {len(failed_tasks)}")

        # 调用遗传算法对失败任务重新调度
        retry_result, _, _ = round_robin(failed_tasks, device_location, link, resource, history_map, link_band)
        # 将结果标记重发次数
        retry_result = np.array(retry_result, dtype=object)
        retry_result = np.insert(retry_result, 8, f"Retry-{retry_count + 1}", axis=1)

        # 分离成功和失败的任务
        success_mask = retry_result[:, 4] == True
        successful_tasks = retry_result[success_mask]
        failed_tasks = retry_result[~success_mask]
        # 合并成功结果
        retry_results.append(successful_tasks)
        retry_count += 1

    # 合并所有重试结果
    return np.vstack(retry_results) if retry_results else np.array([], dtype=object), retry_count


if __name__ == '__main__':
    start_time = time.time()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, 'data')
    result_dir = os.path.join(current_dir, 'result')
    os.makedirs(result_dir, exist_ok=True)

    # 文件路径
    log_file = os.path.join(result_dir, "log.txt")
    results_file = os.path.join(result_dir, "round_robin_results.csv")
    updated_resource_file = os.path.join(result_dir, "updated_resource.csv")
    resource_consumption_file = os.path.join(result_dir, "resource_consumption.csv")
    retry_results_file = os.path.join(result_dir, "round_robin_retry_results.csv")
    link_band_consumption_file = os.path.join(result_dir, "link_band_consumption.csv")

    # # 数据文件路径
    link_path = os.path.join(data_dir, 'resource/Link.csv')
    link_band_path = os.path.join(data_dir, 'resource/link_band_new.csv')
    resource_path = os.path.join(data_dir, 'resource/resource_10w_1000.csv')
    # device_location_path = os.path.join(data_dir, 'task/Device_location_10w_new.csv')
    # tasks_path = os.path.join(data_dir, 'task/task_data_10w.csv')
    # device_location_path = os.path.join(data_dir, 'task/Device_location_15w_new.csv')
    # tasks_path = os.path.join(data_dir, 'task/task_data_15w_new.csv')
    device_location_path = os.path.join(data_dir, 'task/Device_location_100w_new.csv')
    # tasks_path = os.path.join(data_dir, 'task/task_data_100w.csv')

    tasks_path = os.path.join(data_dir, 'task/task_data_100w.csv')

    # 加载数据
    device_location = pd.read_csv(device_location_path).to_numpy()
    link = pd.read_csv(link_path).to_numpy()
    resource = pd.read_csv(resource_path).to_numpy()
    tasks = pd.read_csv(tasks_path).to_numpy()
    link_band = pd.read_csv(link_band_path).to_numpy()
    initial_link_band = link_band.copy()
    initial_resource = resource.copy()
    # tasks = tasks[:1000]
    history_map = np.zeros(len(resource), dtype=int)
    # 处理长期占用资源类型任务：判断任务类型-调度任务分配到最近中心云-更新资源
    long_term_begin_time = time.time()
    tasks_after_long, resource_after_long, link_band_after_long, long_term_tasks_results = (
        process_long_term_tasks(tasks, device_location, link, resource, link_band))
    long_term_end_time = time.time()

    tasks_with_results, resource_finish_first, link_band_finish_first = round_robin(tasks_after_long, device_location,
                                                                                    link, resource_after_long,
                                                                                    history_map,
                                                                                    link_band_after_long)

    get_failed_tasks_begin_time = time.time()
    # failed_tasks_index = tasks_with_results[tasks_with_results[:, 4] == False, 0]
    # failed_tasks = tasks[np.isin(tasks[:, 0], failed_tasks_index)]
    failed_tasks = tasks_after_long[tasks_with_results[:, 4] == False]
    get_failed_tasks_end_time = time.time()

    # 对失败的任务重新调度
    retry_results, scheudingRounds = retry_failed_tasks(failed_tasks, device_location, link, resource_after_long,
                                                        link_band_after_long)
    empty_col = np.empty((tasks_with_results.shape[0], 1), dtype=object)
    empty_col[:] = None
    tasks_with_results = np.hstack([tasks_with_results, empty_col])
    if len(long_term_tasks_results) > 0:
        long_term_tasks_results = np.array(long_term_tasks_results, dtype=object)
        # 添加来源标记
        long_term_tasks_results = np.hstack(
            [long_term_tasks_results, np.full((len(long_term_tasks_results), 1), "Long-Term")])
    else:
        # 如果没有长期任务，创建一个空数组以便后续合并
        long_term_tasks_results = np.empty((0, tasks_with_results.shape[1] + 1), dtype=object)
    tasks_with_results = np.array(tasks_with_results, dtype=object)
    # 添加来源标记
    tasks_off_results = np.insert(tasks_with_results, 9, "round_robin", axis=1)
    combined_results = np.vstack([long_term_tasks_results, tasks_off_results])
    end_time = time.time()

    # 计算任务成功率和运行时间
    success_rate = calculate_success_rate(combined_results)
    elapsed_time = end_time - start_time
    # print(f"任务成功率: {success_rate:.2%}")
    # print(f"程序运行时间: {elapsed_time:.2f} 秒")

    save_to_csv(combined_results, results_file, success_rate, elapsed_time)
    save_updated_resource(resource_finish_first, updated_resource_file)
    save_resource_consumption(initial_resource, resource_finish_first, resource_consumption_file)
    save_to_csv(retry_results, filename=retry_results_file, success_rate=success_rate, elapsed_time=elapsed_time)

    utilization, ram_usage_rate, storage_usage_rate = calculate_resource_utilization(initial_resource,
                                                                                     resource_finish_first)
    link_band_utilization = calculate_link_band_utilization(initial_link_band, link_band, link_band_finish_first)
    save_link_band(link_band_utilization, filename=link_band_consumption_file)
    write_log(log_file, "round_robin", success_rate, elapsed_time, utilization)
    #
    # # 获取数据
    # scheduling_message = [len(tasks), success_rate, elapsed_time, 1 + scheudingRounds,
    #                       ram_usage_rate, storage_usage_rate]
    # task_results_to_json = task_results_to_json(combined_results)
    # # print(task_results_to_json)
    # # print("__SEPARATOR__")  # 在两个 JSON 之间添加分隔符
    # scheduling_message_to_josn = scheduling_message_to_json(utilization, link_band, scheduling_message)
    # # print(scheduling_message_to_josn)
