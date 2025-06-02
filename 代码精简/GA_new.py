import os
import time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import sys
from tools import *
from to_json import *
from trade_off import trade_off
import xml.etree.ElementTree as ET

seed = 14
np.random.seed(seed)
random.seed(seed)


def calculate_fitness(tasks, device_location, link, resource, solution, link_bandwidth):
    # 初始化统计变量
    total_tasks_completed = 0
    initial_total_ram = np.sum(resource[:, 7])  # 初始总RAM
    initial_total_storage = np.sum(resource[:, 8])  # 初始总Storage

    # 创建索引映射
    resource_index = {int(row[0]): idx for idx, row in enumerate(resource)}
    device_map = {int(row[0]): row for row in device_location}
    link_map = {(row[0], row[3]): row for row in link}

    # 备份资源数据
    resource_copy = np.copy(resource)
    bandwidth_copy = np.copy(link_bandwidth)

    # 矢量化处理调度
    task_ids = tasks[:, 0]
    task_types = tasks[:, 1]
    device_ids = tasks[:, 2]
    request_sizes = tasks[:, 3]
    bandwidth_sizes = tasks[:, 4]
    task_lengths = tasks[:, 6]
    max_latencies = tasks[:, 5]
    assigned_clouds = solution

    results = []

    for i in range(len(tasks)):
        task_id = task_ids[i]
        task_type = task_types[i]
        device_id = device_ids[i]
        request_size = request_sizes[i]
        bandwidth_size = bandwidth_sizes[i]
        task_length = task_lengths[i]
        max_latency = max_latencies[i]
        cloud_id = assigned_clouds[i]

        # 查找设备
        device_row = device_map.get(device_id)
        if device_row is None:
            results.append([task_id, device_id, "No Device Found", "N/A", False, "No Device Found", "N/A", task_type])
            continue

        net_device_id = device_row[4]
        net_device_latency = device_row[6]

        # 查找链路
        link_row = link_map.get((net_device_id, cloud_id))
        if link_row is None:
            results.append(
                [task_id, device_id, net_device_id, "No Link Found", False, "No Link Found", "N/A", task_type])
            continue

        transmission_latency, path, sub_path = link_row[4:7]
        # 检查链路带宽
        bandwidth_sufficient = True
        insufficient_segment = None
        segments = sub_path.strip('[]').split('],[')  # 提取路径的各段
        for segment in segments:
            bandwidth_row = bandwidth_copy[bandwidth_copy[:, 0] == segment]
            if bandwidth_row.size == 0 or bandwidth_row[0, 3] < bandwidth_size:
                bandwidth_sufficient = False
                insufficient_segment = segment
                break
        if not bandwidth_sufficient:
            results.append([task_id, device_id, net_device_id, f"Bandwidth Insufficient on {insufficient_segment}",
                            False, "N/A", "N/A", task_type])
            continue

        # 查找目标云资源
        cloud_idx = resource_index.get(cloud_id)
        if cloud_idx is None:
            results.append([task_id, device_id, net_device_id, cloud_id, False, "No Cloud Found", "N/A", task_type])
            continue

        cloud = resource_copy[cloud_idx]

        # 检查资源和时延
        computation_latency = task_length / cloud[6]
        total_latency = transmission_latency + computation_latency + net_device_latency

        if cloud[7] >= request_size and cloud[8] >= request_size and total_latency <= max_latency:
            # 更新资源
            resource_copy[cloud_idx, 7] -= request_size
            resource_copy[cloud_idx, 8] -= request_size
            # 更新带宽资源
            for segment in segments:
                bandwidth_copy[bandwidth_copy[:, 0] == segment, 3] -= bandwidth_size

            results.append([task_id, device_id, net_device_id, cloud_id, True, path, total_latency, task_type])
            total_tasks_completed += 1
        else:
            reason = "Insufficient Resources" if cloud[7] < request_size or cloud[
                8] < request_size else "Latency Exceeded"
            results.append([task_id, device_id, net_device_id, cloud_id, False, reason, "N/A", task_type])

    # 防止初始资源为 0 的情况
    safe_initial_total_ram = max(1, initial_total_ram)  # 确保初始 RAM 总量不为 0
    safe_initial_total_storage = max(1, initial_total_storage)  # 确保初始存储总量不为 0
    # 计算性能指标
    task_success_rate = (total_tasks_completed / len(tasks)) * 100
    ram_usage_rate = (initial_total_ram - np.sum(resource_copy[:, 7])) / safe_initial_total_ram * 100
    storage_usage_rate = (initial_total_storage - np.sum(resource_copy[:, 8])) / safe_initial_total_storage * 100
    # 抽取ram和storage并转化类型（由objict——float）
    resource_float = resource[:, 7:].astype(float)
    resource_copy_float = resource_copy[:, 7:].astype(float)
    ram_load_rates = np.ones(len(resource), dtype=float)
    storage_load_rates = np.ones(len(resource), dtype=float)
    # 计算ram和storage的负载率，避免除以0的情况，并将剩余0的资源利用率置为100%
    np.divide(
        resource_float[:, 0] - resource_copy_float[:, 0],
        resource_float[:, 0],
        out=ram_load_rates,
        where=resource_float[:, 0] != 0)
    np.divide(
        resource_float[:, 1] - resource_copy_float[:, 1],
        resource_float[:, 1],
        out=storage_load_rates,
        where=resource_float[:, 1] != 0)
    max_load_rate = max(np.max(ram_load_rates), np.max(storage_load_rates))

    # 计算适应度
    # fitness = 0.99 * task_success_rate + 0.01 * max_load_rate
    fitness = task_success_rate
    for i in range(len(tasks)):
        # ...
        if link_row is None:
            print(f"Task {task_id} failed to schedule: No Link Found")
            results.append(
                [task_id, device_id, net_device_id, "No Link Found", False, "No Link Found", "N/A", task_type])
            continue
        # ...
        if not bandwidth_sufficient:
            print(f"Task {task_id} failed to schedule: Bandwidth Insufficient on {insufficient_segment}")
            results.append([task_id, device_id, net_device_id, f"Bandwidth Insufficient on {insufficient_segment}",
                            False, "N/A", "N/A", task_type])
            continue
        # ...
        if cloud[7] < request_size or cloud[8] < request_size:
            print(f"Task {task_id} failed to schedule: Insufficient Resources")
        elif total_latency > max_latency:
            print(f"Task {task_id} failed to schedule: Latency Exceeded")
        # ...
    # ...

    return fitness, np.array(results, dtype=object), bandwidth_copy, resource_copy


def initialize_population_with_heuristics(task_count, cloud_count, population_size, device_location, link, tasks,
                                          resource, history_map):
    """
    使用优化的启发式方法初始化种群，确保链路时延满足要求，并且每个云的资源总量不超过限制。
    同时结合历史信息、资源负载和网络延迟选择最优节点，避免过度集中。
    如果种群大小大于3，则任务遍历顺序包括从前向后、从后向前和从中间开始遍历。
    """
    population = []  # 初始化种群为空

    # 提取每个云节点的资源容量，并创建云节点 ID 到索引的映射
    cloud_ids = resource[:, 0].astype(int)
    id_to_index = {cloud_id: idx for idx, cloud_id in enumerate(cloud_ids)}
    max_ram = resource[:, 7].copy()
    max_storage = resource[:, 8].copy()

    # 将 device_location 和 link 转换为字典，加快查找速度
    device_map = {int(row[0]): row for row in device_location}
    # link_map = {(row[0], row[3]): row[4:7] for row in link}
    link_map = {}
    for row in link:
        src, dest = row[0], int(row[3])
        if src not in link_map:
            link_map[src] = []
        link_map[src].append(row)
    order = []
    for _ in range(population_size):
        solution = [None] * task_count  # 单个个体解，初始化为None，长度为任务数
        used_ram = np.zeros(len(cloud_ids))
        used_storage = np.zeros(len(cloud_ids))

        # 根据种群大小和随机选择的遍历顺序，确定任务的遍历顺序
        if population_size > 3:
            order_type = np.random.choice(['forward', 'backward', 'middle'])
        else:
            order_type = 'forward'
        if order_type == 'forward':
            task_indices = list(range(task_count))  # 从前向后遍历任务
        elif order_type == 'backward':
            task_indices = list(range(task_count - 1, -1, -1))  # 从后向前遍历任务
        else:  # 'middle'
            # 从中间开始遍历任务，先从中间向两侧扩展
            task_indices = []
            middle = task_count // 2
            for i in range(middle, task_count):
                task_indices.append(i)
            for i in range(middle - 1, -1, -1):
                task_indices.append(i)
        order.append(order_type)

        for task_idx in task_indices:
            task = tasks[task_idx]
            device_id = task[2]
            request_size = task[3]
            task_length = task[6]
            max_latency = task[5]

            # 查找设备的 Net_device id 和延迟信息
            device_row = device_map.get(device_id)
            if device_row is None:
                # 如果找不到设备信息，回退选择一个随机的云节点
                solution[task_idx] = np.random.choice(cloud_ids)
                continue

            net_device_id = device_row[4]
            net_device_latency = device_row[6]
            # 获取设备连接的链路
            links = link_map.get(net_device_id, [])
            valid_clouds = []

            for link_row in links:
                destination_id = int(link_row[3])
                if destination_id not in id_to_index:
                    continue
                cloud_index = id_to_index[destination_id]
                transmission_latency = link_row[4]
                # 检查资源是否足够
                if used_ram[cloud_index] + request_size <= max_ram[cloud_index] and \
                        used_storage[cloud_index] + request_size <= max_storage[cloud_index]:
                    # 计算总延迟
                    computation_latency = task_length / resource[cloud_index, 6]
                    total_latency = transmission_latency + computation_latency + net_device_latency
                    if total_latency <= max_latency:
                        # 选择满足条件的云节点
                        valid_clouds.append((destination_id, cloud_index, total_latency))

            if valid_clouds:
                # 优先选择权重最低的云节点，考虑历史使用情况和总延迟综合考虑
                selected_cloud, selected_index, best_total_latency = min(
                    valid_clouds,
                    key=lambda x: (history_map[x[1]] + 1) * (x[2])  # 历史使用次数和总延迟综合考虑
                )
            else:
                # 回退策略：随机选择资源充足的云节点
                selected_index = np.argmax(max_ram - used_ram)
                selected_cloud = cloud_ids[selected_index]
            # 更新资源使用情况
            used_ram[selected_index] += request_size
            used_storage[selected_index] += request_size
            history_map[selected_index] += 1  # 更新历史使用情况
            # 更新solution中对应task_idx的位置
            solution[task_idx] = selected_cloud
        population.append(solution)

    return np.array(population)


# 选择操作
def selection(population, fitnesses):
    probabilities = fitnesses / fitnesses.sum()
    selected_idx = np.random.choice(len(population), size=len(population), p=probabilities)
    return population[selected_idx]


# 交叉操作
def crossover(parent1, parent2):
    crossover_point = np.random.randint(0, len(parent1))
    child1 = np.concatenate((parent1[:crossover_point], parent2[crossover_point:]))
    child2 = np.concatenate((parent2[:crossover_point], parent1[crossover_point:]))
    return child1, child2


# 变异操作
def mutate(individual, mutation_rate, cloud_count):
    for i in range(len(individual)):
        if np.random.rand() < mutation_rate:
            individual[i] = np.random.randint(0, cloud_count)
    return individual


# 并行计算适应度函数
def parallel_calculate_fitness(individual, tasks, device_location, link, resource, link_band):
    return calculate_fitness(tasks, device_location, link, resource, individual, link_band)[0]


def genetic_algorithm(tasks, device_location, link, resource, link_band, generations=1, population_size=4,
                      mutation_rate=0.01):
    task_count = len(tasks)
    cloud_count = len(resource)
    # print('start initial population')
    initial_time_start = time.time()
    # 初始化种群，确保设备和云资源之间有链路
    history_map = np.zeros(len(resource), dtype=int)

    population = initialize_population_with_heuristics(task_count, cloud_count, population_size, device_location, link,
                                                       tasks, resource, history_map)
    initial_time_end = time.time()
    print(f'initial_time:{initial_time_end - initial_time_start}')

    # fitness_cache = {}  # 用于缓存适应度值

    best_solution = None
    best_fitness = 0
    # print('start generation')
    # 迭代演化
    for generation in range(generations):
        # 并行计算适应度
        with ProcessPoolExecutor() as executor:
            # 通过 executor 并行化适应度计算
            fitnesses = list(executor.map(parallel_calculate_fitness, population, [tasks] * population_size,
                                          [device_location] * population_size, [link] * population_size,
                                          [resource] * population_size, [link_band] * population_size))
        fitnesses = np.array(fitnesses)
        # 缓存和更新最佳适应度
        if fitnesses.max() > best_fitness:
            best_fitness = fitnesses.max()
            best_solution = population[np.argmax(fitnesses)]

        # 选择操作
        population = selection(population, fitnesses)

        # 交叉操作
        new_population = []
        for i in range(0, len(population), 2):
            parent1, parent2 = population[i], population[i + 1]
            child1, child2 = crossover(parent1, parent2)
            new_population.extend([child1, child2])

        # 变异操作
        population = np.array([mutate(individual, mutation_rate, cloud_count) for individual in new_population])

    # 计算最优解的任务分配结果
    _, tasks_with_results, update_link_band, resource_copy = calculate_fitness(tasks, device_location, link, resource,
                                                                               best_solution, link_band)
    return tasks_with_results, update_link_band, resource_copy


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
    history_map = np.zeros(len(resource), dtype=int)

    while retry_count < max_retries and len(failed_tasks) > 0:
        # print(f"Retry Attempt {retry_count + 1} - Remaining Tasks: {len(failed_tasks)}")

        # 调用遗传算法对失败任务重新调度
        retry_result, _, _ = trade_off(failed_tasks, device_location, link, resource, history_map, link_band)

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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    start_time = time.time()  # 记录开始时间

    data_dir = os.path.join(current_dir, 'data')
    result_dir = os.path.join(current_dir, 'result')
    os.makedirs(result_dir, exist_ok=True)

    # 数据文件路径
    # device_location_path = os.path.join(data_dir, 'task/Device_location_10w.csv')
    # link_path = os.path.join(data_dir, 'resource/Link.csv')
    # resource_path = os.path.join(data_dir, 'resource/resource.csv')
    # tasks_path = os.path.join(data_dir, 'task/task_5000.csv')
    # # tasks_path = os.path.join(data_dir, 'task/task_10w.csv')
    # link_band_path = os.path.join(data_dir, 'resource/link_band.csv')

    # 结果文件路径
    # log_file = os.path.join(result_dir, "log.txt")
    log_file = os.path.join(result_dir, 'GA_log.txt')  # 日志文件路径
    resource_consumption_file = os.path.join(result_dir, "resource_consumption.csv")
    updated_resource_file = os.path.join(result_dir, "updated_resource.csv")
    results_file = os.path.join(result_dir, "GA_results.csv")
    retry_results_file = os.path.join(result_dir, "ga_retry_results.csv")
    link_band_consumption_file = os.path.join(result_dir, "link_band_consumption.csv")

    link_path = os.path.join(data_dir, 'resource/Link.csv')
    link_band_path = os.path.join(data_dir, 'resource/link_band_new.csv')
    resource_path = os.path.join(data_dir, 'resource/resource_10w_1000.csv')
    # device_location_path = os.path.join(data_dir, 'task/Device_location_10w_new.csv')
    # tasks_path = os.path.join(data_dir, 'task/task_data_10w_new.csv')
    # device_location_path = os.path.join(data_dir, 'task/Device_location_15w_new.csv')
    # tasks_path = os.path.join(data_dir, 'task/task_data_15w_new.csv')
    device_location_path = os.path.join(data_dir, 'task/Device_location_100w_new.csv')
    # tasks_path = os.path.join(data_dir, 'task/task_data_100w.csv')

    tasks_path = os.path.join(data_dir, 'task/task_data_100w.csv')

    # device_location_path = os.path.join(data_dir, 'task/Device_location_10w_select.csv')
    # link_path = os.path.join(data_dir, 'resource/Link.csv')
    # resource_path = os.path.join(data_dir, 'resource/resource_10w_select.csv')
    # tasks_path = os.path.join(data_dir, 'task/task_data_10w_select.csv')
    # link_band_path = os.path.join(data_dir, 'resource/link_band.csv')

    # 加载数据文件并转换为 numpy 数组
    device_location = pd.read_csv(device_location_path).to_numpy()
    link = pd.read_csv(link_path).to_numpy()
    resource = pd.read_csv(resource_path).to_numpy()
    tasks = pd.read_csv(tasks_path).to_numpy()
    link_band = pd.read_csv(link_band_path).to_numpy()

    # 处理长期占用资源类型任务：判断任务类型-调度任务分配到最近中心云-更新资源
    long_term_begin_time = time.time()
    tasks_after_long, resource_after_long, link_band_after_long, long_term_tasks_results \
        = process_long_term_tasks(tasks, device_location, link, resource, link_band)
    long_term_end_time = time.time()
    print(f'long term tasks scheduling {long_term_end_time - long_term_begin_time}')

    # 运行遗传算法
    print('start GA')
    ga_begin_time = time.time()
    ga_results, update_link_band, resource_finish_first = genetic_algorithm(tasks_after_long, device_location, link, resource_after_long, link_band_after_long)
    ga_end_time = time.time()
    print(f'ga time {ga_end_time - ga_begin_time}')
    # 获取失败任务集合
    print('start get failed tasks')
    get_failed_tasks_begin_time = time.time()
    # failed_tasks_index = ga_results[ga_results[:, 4] == False, 0]
    # failed_tasks = tasks[np.isin(tasks[:, 0], failed_tasks_index)]
    failed_tasks = tasks_after_long[ga_results[:, 4] == False]
    get_failed_tasks_end_time = time.time()
    print(f'get failed tasks {get_failed_tasks_end_time - get_failed_tasks_begin_time}')

    # 对失败的任务重新调度
    retry_results, scheudingRounds = retry_failed_tasks(failed_tasks, device_location, link, resource_after_long,
                                                        link_band_after_long)
    empty_col = np.empty((ga_results.shape[0], 1), dtype=object)
    empty_col[:] = None
    ga_results = np.hstack([ga_results, empty_col])
    if len(long_term_tasks_results) > 0:
        long_term_tasks_results = np.array(long_term_tasks_results, dtype=object)
        # 添加来源标记
        long_term_tasks_results = np.hstack(
            [long_term_tasks_results, np.full((len(long_term_tasks_results), 1), "Long-Term")])
    else:
        # 如果没有长期任务，创建一个空数组以便后续合并
        long_term_tasks_results = np.empty((0, ga_results.shape[1] + 1), dtype=object)
    # ga_results = np.array(ga_results, dtype=object)
    # 添加来源标记
    ga_results = np.insert(ga_results, 9, "GA", axis=1)
    combined_results = np.vstack([long_term_tasks_results, ga_results])

    # 计算任务成功率
    successful_tasks_first = np.sum(combined_results[:, 4] == True)  # 统计第5列为 "True" 的行数
    success_rate = (successful_tasks_first / len(combined_results))  # 计算成功率
    # 计算并保存运行时间
    end_time = time.time()  # 记录终止时间
    elapsed_time = end_time - start_time  # 计算调度总时间
    print(f"任务成功率: {success_rate:.2f}%")
    print(f"程序运行时间: {elapsed_time:.2f} 秒")

    # 计算资源利用率并写日志
    initial_resource = resource.copy()
    initial_link_band = link_band.copy()
    utilization, ram_usage_rate, storage_usage_rate = calculate_resource_utilization(initial_resource, resource_finish_first)
    write_log(log_file, "GA", success_rate, elapsed_time, utilization)

    link_band_utilization = calculate_link_band_utilization_GA(initial_link_band, update_link_band)
    save_link_band(link_band_utilization, filename=link_band_consumption_file)
    save_resource_consumption(initial_resource, resource_finish_first, filename=resource_consumption_file)
    save_updated_resource(resource_finish_first, filename=updated_resource_file)
    save_to_csv(combined_results, filename=results_file, success_rate=success_rate, elapsed_time=elapsed_time)
    save_to_csv(retry_results, filename=retry_results_file, success_rate=success_rate, elapsed_time=elapsed_time)
