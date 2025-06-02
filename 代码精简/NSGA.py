import os
import time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import sys
from tools import *
from to_json import *
from trade_off import trade_off
import xml.etree.ElementTree as ET
import random

seed = 14
np.random.seed(seed)
random.seed(seed)

# 计算适应度函数，返回多目标值（任务成功率，负资源负载不均衡度）
def calculate_fitness(tasks, device_location, link, resource, solution, link_bandwidth):
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
def initialize_population_with_heuristics(task_count, cloud_count, population_size, device_location, link, tasks, resource, history_map):
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
                        valid_clouds.append((destination_id, cloud_index, total_latency))

            if valid_clouds:
                # 选择最优的云节点
                best_cloud = min(valid_clouds, key=lambda x: x[2])[0]
                solution[task_idx] = best_cloud
                used_ram[id_to_index[best_cloud]] += request_size
                used_storage[id_to_index[best_cloud]] += request_size
            else:
                solution[task_idx] = np.random.choice(cloud_ids)

        population.append(solution)
    return population

# 交叉操作
def crossover(parent1, parent2):
    crossover_point = random.randint(1, len(parent1) - 1)
    child1 = parent1[:crossover_point] + parent2[crossover_point:]
    child2 = parent2[:crossover_point] + parent1[crossover_point:]
    return child1, child2

# 变异操作，增加禁忌搜索
def mutate(solution, cloud_ids, tabu_list, max_retries=10):
    new_solution = solution.copy()
    retries = 0
    while retries < max_retries:
        index = random.randint(0, len(solution) - 1)
        new_value = random.choice(cloud_ids)
        new_solution[index] = new_value
        if tuple(new_solution) not in tabu_list:
            tabu_list.add(tuple(new_solution))
            return new_solution
        retries += 1
    # 如果达到最大重试次数，返回原解
    return solution

# 主函数
def main():
    # 初始化参数
    task_count = 100
    cloud_count = 10
    population_size = 50
    generations = 100
    mutation_rate = 0.1

    # 初始化种群
    tasks = np.random.rand(task_count, 7)
    device_location = np.random.rand(10, 7)
    link = np.random.rand(20, 7)
    resource = np.random.rand(cloud_count, 9)
    link_bandwidth = np.random.rand(20, 4)
    history_map = np.zeros(cloud_count)

    population = initialize_population_with_heuristics(task_count, cloud_count, population_size, device_location, link, tasks, resource, history_map)

    # 禁忌表
    tabu_list = set()
    max_tabu_size = 100  # 限制禁忌表大小

    for _ in range(generations):
        new_population = []
        fitness_values = []

        # 计算适应度
        for solution in population:
            fitness, _, _, _ = calculate_fitness(tasks, device_location, link, resource, solution, link_bandwidth)
            fitness_values.append(fitness)

        # 选择、交叉、变异
        fronts = non_dominated_sorting(population, fitness_values)
        for front in fronts:
            distances = crowding_distance(fitness_values, front)
            sorted_indices = sorted(front, key=lambda x: distances[x], reverse=True)
            for i in range(0, len(sorted_indices) - 1, 2):
                parent1 = population[sorted_indices[i]]
                parent2 = population[sorted_indices[i + 1]]
                child1, child2 = crossover(parent1, parent2)

                if random.random() < mutation_rate:
                    cloud_ids = resource[:, 0].astype(int)
                    child1 = mutate(child1, cloud_ids, tabu_list)
                    child2 = mutate(child2, cloud_ids, tabu_list)

                new_population.extend([child1, child2])

        # 限制禁忌表大小
        while len(tabu_list) > max_tabu_size:
            tabu_list.pop()

        population = new_population

    # 输出最终结果
    best_solution = max(population, key=lambda x: calculate_fitness(tasks, device_location, link, resource, x, link_bandwidth)[0][0])
    best_fitness, _, _, _ = calculate_fitness(tasks, device_location, link, resource, best_solution, link_bandwidth)
    print("Best solution:", best_solution)
    print("Best fitness:", best_fitness)

if __name__ == "__main__":
    main()