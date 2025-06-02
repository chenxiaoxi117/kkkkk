import os
import time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import sys
import pandas as pd
from tools import *
from to_json import *
from trade_off import trade_off
import xml.etree.ElementTree as ET
import random

seed = 14
np.random.seed(seed)
random.seed(seed)

# 读取全局禁忌表
def read_tabu_table():
    tabu_table_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tabu_table.csv')
    if os.path.exists(tabu_table_path):
        tabu_table = pd.read_csv(tabu_table_path)
        return tabu_table
    return None

# 检查路径是否在禁忌表中
def is_path_tabu(tabu_table, app_type, net_device_id, cloud_id, link_map):
    if tabu_table is None:
        return False
    relevant_tabu = tabu_table[tabu_table['AppType'] == app_type]
    for _, row in relevant_tabu.iterrows():
        source_id = row['source_id']
        dest_id = row['dest_id']
        if source_id == net_device_id and dest_id == cloud_id:
            return True
    return False

# 计算适应度函数，返回多目标值（任务成功率，负资源负载不均衡度）
def calculate_fitness(tasks, device_location, link, resource, solution, link_bandwidth, tabu_table):
    total_tasks_completed = 0
    initial_total_ram = np.sum(resource[:, 7])
    initial_total_storage = np.sum(resource[:, 8])

    resource_index = {int(row[0]): idx for idx, row in enumerate(resource)}
    device_map = {int(row[0]): row for row in device_location}
    link_map = {(row[0], row[3]): row for row in link}

    resource_copy = np.copy(resource)
    bandwidth_copy = np.copy(link_bandwidth)

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

        device_row = device_map.get(device_id)
        if device_row is None:
            results.append([task_id, device_id, "No Device Found", "N/A", False, "No Device Found", "N/A", task_type])
            continue

        net_device_id = device_row[4]
        net_device_latency = device_row[6]

        # 检查路径是否在禁忌表中
        if is_path_tabu(tabu_table, task_type, net_device_id, cloud_id, link_map):
            results.append([task_id, device_id, net_device_id, cloud_id, False, "Path in Tabu Table", "N/A", task_type])
            continue

        link_row = link_map.get((net_device_id, cloud_id))
        if link_row is None:
            results.append([task_id, device_id, net_device_id, "No Link Found", False, "No Link Found", "N/A", task_type])
            continue

        transmission_latency, path, sub_path = link_row[4:7]
        bandwidth_sufficient = True
        insufficient_segment = None
        segments = sub_path.strip('[]').split('],[')
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

        cloud_idx = resource_index.get(cloud_id)
        if cloud_idx is None:
            results.append([task_id, device_id, net_device_id, cloud_id, False, "No Cloud Found", "N/A", task_type])
            continue

        cloud = resource_copy[cloud_idx]

        computation_latency = task_length / cloud[6]
        total_latency = transmission_latency + computation_latency + net_device_latency

        if cloud[7] >= request_size and cloud[8] >= request_size and total_latency <= max_latency:
            resource_copy[cloud_idx, 7] -= request_size
            resource_copy[cloud_idx, 8] -= request_size
            for segment in segments:
                bandwidth_copy[bandwidth_copy[:, 0] == segment, 3] -= bandwidth_size

            results.append([task_id, device_id, net_device_id, cloud_id, True, path, total_latency, task_type])
            total_tasks_completed += 1
        else:
            reason = "Insufficient Resources" if cloud[7] < request_size or cloud[8] < request_size else "Latency Exceeded"
            results.append([task_id, device_id, net_device_id, cloud_id, False, reason, "N/A", task_type])

    safe_initial_total_ram = max(1, initial_total_ram)
    safe_initial_total_storage = max(1, initial_total_storage)
    task_success_rate = (total_tasks_completed / len(tasks)) * 100

    resource_float = resource[:, 7:].astype(float)
    resource_copy_float = resource_copy[:, 7:].astype(float)
    ram_load_rates = np.ones(len(resource), dtype=float)
    storage_load_rates = np.ones(len(resource), dtype=float)
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
    load_imbalance = (np.std(ram_load_rates) + np.std(storage_load_rates)) / 2

    fitness = (task_success_rate, -load_imbalance)  # 负值表示最小化负载不均衡
    return fitness, np.array(results, dtype=object), bandwidth_copy, resource_copy

# 非支配排序
def non_dominated_sorting(population, fitness_values):
    domination_count = [0] * len(population)
    dominated_solutions = [[] for _ in range(len(population))]
    fronts = [[]]

    for i in range(len(population)):
        for j in range(i + 1, len(population)):
            if dominates(fitness_values[i], fitness_values[j]):
                dominated_solutions[i].append(j)
                domination_count[j] += 1
            elif dominates(fitness_values[j], fitness_values[i]):
                dominated_solutions[j].append(i)
                domination_count[i] += 1

    for i in range(len(population)):
        if domination_count[i] == 0:
            fronts[0].append(i)

    current_front = 0
    while fronts[current_front]:
        next_front = []
        for i in fronts[current_front]:
            for j in dominated_solutions[i]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    next_front.append(j)
        current_front += 1
        fronts.append(next_front)

    return fronts[:-1]

# 判断支配关系
def dominates(fitness1, fitness2):
    return (fitness1[0] >= fitness2[0] and fitness1[1] >= fitness2[1] and
            (fitness1[0] > fitness2[0] or fitness1[1] > fitness2[1]))

# 计算拥挤度距离
def crowding_distance(fitness_values, front):
    distances = [0] * len(fitness_values)
    num_objectives = len(fitness_values[0])

    for m in range(num_objectives):
        sorted_indices = sorted(front, key=lambda x: fitness_values[x][m])
        distances[sorted_indices[0]] = float('inf')
        distances[sorted_indices[-1]] = float('inf')
        min_val = min(fitness_values[i][m] for i in front)
        max_val = max(fitness_values[i][m] for i in front)
        if max_val == min_val:
            continue
        for i in range(1, len(sorted_indices) - 1):
            distances[sorted_indices[i]] += (fitness_values[sorted_indices[i+1]][m] -
                                             fitness_values[sorted_indices[i-1]][m]) / (max_val - min_val)

    return distances

# 初始化种群（保持原函数）
def initialize_population_with_heuristics(task_count, cloud_count, population_size, device_location, link, tasks, resource, history_map, tabu_table):
    population = []
    cloud_ids = resource[:, 0].astype(int)
    id_to_index = {cloud_id: idx for idx, cloud_id in enumerate(cloud_ids)}
    max_ram = resource[:, 7].copy()
    max_storage = resource[:, 8].copy()

    device_map = {int(row[0]): row for row in device_location}
    link_map = {}
    for row in link:
        src, dest = row[0], int(row[3])
        if src not in link_map:
            link_map[src] = []
        link_map[src].append(row)
    order = []
    for _ in range(population_size):
        solution = [None] * task_count
        used_ram = np.zeros(len(cloud_ids))
        used_storage = np.zeros(len(cloud_ids))

        if population_size > 3:
            order_type = np.random.choice(['forward', 'backward', 'middle'])
        else:
            order_type = 'forward'
        if order_type == 'forward':
            task_indices = list(range(task_count))
        elif order_type == 'backward':
            task_indices = list(range(task_count - 1, -1, -1))
        else:
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
            task_type = task[1]

            device_row = device_map.get(device_id)
            if device_row is None:
                solution[task_idx] = np.random.choice(cloud_ids)
                continue

            net_device_id = device_row[4]
            net_device_latency = device_row[6]
            links = link_map.get(net_device_id, [])
            valid_clouds = []

            for link_row in links:
                destination_id = int(link_row[3])
                if destination_id not in id_to_index:
                    continue
                cloud_index = id_to_index[destination_id]
                transmission_latency = link_row[4]
                if used_ram[cloud_index] + request_size <= max_ram[cloud_index] and \
                        used_storage[cloud_index] + request_size <= max_storage[cloud_index]:
                    computation_latency = task_length / resource[cloud_index, 6]
                    total_latency = transmission_latency + computation_latency + net_device_latency
                    if total_latency <= max_latency:
                        # 检查路径是否在禁忌表中
                        if not is_path_tabu(tabu_table, task_type, net_device_id, destination_id, link_map):
                            valid_clouds.append((destination_id, cloud_index, total_latency))

            if valid_clouds:
                selected_cloud, selected_index, best_total_latency = min(
                    valid_clouds,
                    key=lambda x: (history_map[x[1]] + 1) * (x[2])
                )
            else:
                # 如果没有有效云，随机选择一个不在禁忌表中的云
                available_clouds = []
                for cloud_id in cloud_ids:
                    if not is_path_tabu(tabu_table, task_type, net_device_id, cloud_id, link_map):
                        available_clouds.append(cloud_id)
                if available_clouds:
                    selected_index = id_to_index[np.random.choice(available_clouds)]
                    selected_cloud = cloud_ids[selected_index]
                else:
                    selected_index = np.argmax(max_ram - used_ram)
                    selected_cloud = cloud_ids[selected_index]
            used_ram[selected_index] += request_size
            used_storage[selected_index] += request_size
            history_map[selected_index] += 1
            solution[task_idx] = selected_cloud
        population.append(solution)

    return np.array(population)

# 选择、交叉、变异（保持原函数）
def selection(population, fitnesses):
    probabilities = fitnesses[:, 0] / fitnesses[:, 0].sum()
    selected_idx = np.random.choice(len(population), size=len(population), p=probabilities)
    return population[selected_idx]

def crossover(parent1, parent2):
    crossover_point = np.random.randint(0, len(parent1))
    child1 = np.concatenate((parent1[:crossover_point], parent2[crossover_point:]))
    child2 = np.concatenate((parent2[:crossover_point], parent1[crossover_point:]))
    return child1, child2

def mutate(individual, mutation_rate, cloud_count):
    for i in range(len(individual)):
        if np.random.rand() < mutation_rate:
            individual[i] = np.random.randint(0, cloud_count)
    return individual

# 并行计算适应度
def parallel_calculate_fitness(individual, tasks, device_location, link, resource, link_band, tabu_table):
    return calculate_fitness(tasks, device_location, link, resource, individual, link_band, tabu_table)[0]

# 多目标遗传算法（NSGA-II）
def genetic_algorithm(tasks, device_location, link, resource, link_band, generations=1, population_size=4, mutation_rate=0.01, tabu_table=None):
    task_count = len(tasks)
    cloud_count = len(resource)
    initial_time_start = time.time()
    history_map = np.zeros(len(resource), dtype=int)

    population = initialize_population_with_heuristics(task_count, cloud_count, population_size, device_location, link,
                                                       tasks, resource, history_map, tabu_table)
    initial_time_end = time.time()
    print(f'initial_time:{initial_time_end - initial_time_start}')

    for generation in range(generations):
        with ProcessPoolExecutor() as executor:
            fitnesses = list(executor.map(parallel_calculate_fitness, population, [tasks] * population_size,
                                          [device_location] * population_size, [link] * population_size,
                                          [resource] * population_size, [link_band] * population_size, [tabu_table] * population_size))
        fitnesses = np.array(fitnesses)

        fronts = non_dominated_sorting(population, fitnesses)
        next_population = []
        for front in fronts:
            if len(next_population) + len(front) <= population_size:
                next_population.extend(front)
            else:
                distances = crowding_distance(fitnesses, front)
                sorted_front = sorted(front, key=lambda x: distances[front.index(x)], reverse=True)
                next_population.extend(sorted_front[:population_size - len(next_population)])
                break

        offspring = []
        while len(offspring) < population_size:
            parent1 = random.choice(next_population)
            parent2 = random.choice(next_population)
            child1, child2 = crossover(population[parent1], population[parent2])
            offspring.extend([mutate(child1, mutation_rate, cloud_count), mutate(child2, mutation_rate, cloud_count)])

        population = [population[i] for i in next_population] + offspring[:population_size - len(next_population)]

    fitness_values = [calculate_fitness(tasks, device_location, link, resource, ind, link_band, tabu_table)[0] for ind in population]
    fronts = non_dominated_sorting(population, fitness_values)
    pareto_solutions = [population[i] for i in fronts[0]]
    pareto_results = [calculate_fitness(tasks, device_location, link, resource, sol, link_band, tabu_table) for sol in pareto_solutions]
    return [(sol, res[1], res[2], res[3]) for sol, res in zip(pareto_solutions, pareto_results)]

# 重试失败任务（稍作调整以适应多目标）
def retry_failed_tasks(failed_tasks, device_location, link, resource, link_band, max_retries=3, tabu_table=None):
    retry_results = []
    retry_count = 0
    history_map = np.zeros(len(resource), dtype=int)

    while retry_count < max_retries and len(failed_tasks) > 0:
        pareto_results = genetic_algorithm(failed_tasks, device_location, link, resource, link_band, tabu_table=tabu_table)
        for _, tasks_with_results, _, _ in pareto_results:
            tasks_with_results = np.array(tasks_with_results, dtype=object)
            tasks_with_results = np.insert(tasks_with_results, 8, f"Retry-{retry_count + 1}", axis=1)
            success_mask = tasks_with_results[:, 4] == True
            successful_tasks = tasks_with_results[success_mask]
            failed_tasks = failed_tasks[~success_mask]
            retry_results.append(successful_tasks)
        retry_count += 1

    return np.vstack(retry_results) if retry_results else np.array([], dtype=object), retry_count

if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    start_time = time.time()
    data_dir = os.path.join(current_dir, 'data')
    result_dir = os.path.join(current_dir, 'result')
    os.makedirs(result_dir, exist_ok=True)

    log_file = os.path.join(result_dir, 'GA_log.txt')
    resource_consumption_file = os.path.join(result_dir, "resource_consumption.csv")
    updated_resource_file = os.path.join(result_dir, "updated_resource.csv")
    results_file = os.path.join(result_dir, "GA_results.csv")
    retry_results_file = os.path.join(result_dir, "ga_retry_results.csv")
    link_band_consumption_file = os.path.join(result_dir, "link_band_consumption.csv")

    link_path = os.path.join(data_dir, 'resource/Link.csv')
    link_band_path = os.path.join(data_dir, 'resource/link_band_new.csv')
    resource_path = os.path.join(data_dir, 'resource/resource_10w_1000.csv')
    device_location_path = os.path.join(data_dir, 'task/Device_location_100w_new.csv')
    tasks_path = os.path.join(data_dir, 'task/task_data_100w.csv')

    device_location = pd.read_csv(device_location_path).to_numpy()
    link = pd.read_csv(link_path).to_numpy()
    resource = pd.read_csv(resource_path).to_numpy()
    tasks = pd.read_csv(tasks_path).to_numpy()
    link_band = pd.read_csv(link_band_path).to_numpy()

    # 读取禁忌表
    tabu_table = read_tabu_table()

    long_term_begin_time = time.time()
    tasks_after_long, resource_after_long, link_band_after_long, long_term_tasks_results \
        = process_long_term_tasks(tasks, device_location, link, resource, link_band)
    long_term_end_time = time.time()
    print(f'long term tasks scheduling {long_term_end_time - long_term_begin_time}')

    print('start GA')
    ga_begin_time = time.time()
    pareto_results = genetic_algorithm(tasks_after_long, device_location, link, resource_after_long, link_band_after_long, tabu_table=tabu_table)
    ga_end_time = time.time()
    print(f'ga time {ga_end_time - ga_begin_time}')

    print('start get failed tasks')
    get_failed_tasks_begin_time = time.time()
    failed_tasks = tasks_after_long[pareto_results[0][1][:, 4] == False]
    get_failed_tasks_end_time = time.time()
    print(f'get failed tasks {get_failed_tasks_end_time - get_failed_tasks_begin_time}')

    retry_results, scheudingRounds = retry_failed_tasks(failed_tasks, device_location, link, resource_after_long,
                                                        link_band_after_long, tabu_table=tabu_table)

    combined_results = []
    for _, tasks_with_results, _, _ in pareto_results:
        tasks_with_results = np.hstack([tasks_with_results, np.full((len(tasks_with_results), 1), None)])
        tasks_with_results = np.insert(tasks_with_results, 9, "GA", axis=1)
        combined_results.append(tasks_with_results)

    if len(long_term_tasks_results) > 0:
        long_term_tasks_results = np.array(long_term_tasks_results, dtype=object)
        long_term_tasks_results = np.hstack(
            [long_term_tasks_results, np.full((len(long_term_tasks_results), 1), "Long-Term")])
    else:
        long_term_tasks_results = np.empty((0, combined_results[0].shape[1]), dtype=object)

    combined_results = np.vstack([long_term_tasks_results] + combined_results)

    successful_tasks_first = np.sum(combined_results[:, 4] == True)
    success_rate = (successful_tasks_first / len(combined_results)) * 100
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"任务成功率: {success_rate:.2f}%")
    print(f"程序运行时间: {elapsed_time:.2f} 秒")

    initial_resource = resource.copy()
    initial_link_band = link_band.copy()
    utilization, ram_usage_rate, storage_usage_rate = calculate_resource_utilization(initial_resource, pareto_results[0][3])
    write_log(log_file, "GA", success_rate, elapsed_time, utilization)

    link_band_utilization = calculate_link_band_utilization_GA(initial_link_band, pareto_results[0][2])
    save_link_band(link_band_utilization, filename=link_band_consumption_file)
    save_resource_consumption(initial_resource, pareto_results[0][3], filename=resource_consumption_file)
    save_updated_resource(pareto_results[0][3], filename=updated_resource_file)
    save_to_csv(combined_results, filename=results_file, success_rate=success_rate, elapsed_time=elapsed_time)
    save_to_csv(retry_results, filename=retry_results_file, success_rate=success_rate, elapsed_time=elapsed_time)

    for i, (sol, tasks_with_results, _, _) in enumerate(pareto_results):
        fitness = calculate_fitness(tasks_after_long, device_location, link, resource_after_long, sol, link_band_after_long, tabu_table)[0]
        print(f"Pareto Solution {i+1}: Task Success Rate = {fitness[0]:.2f}%, Load Imbalance = {-fitness[1]:.4f}")