# -*- coding: utf-8 -*-
import csv
import heapq
import logging
import threading
import time
from datetime import datetime, timedelta
import numpy as np
from pymoo.core.problem import Problem
# 导入 NSGA2 算法类
from pymoo.algorithms.moo.nsga2 import NSGA2
# 从优化模块导入 minimize 函数
from pymoo.optimize import minimize
import cvxpy as cp


class TaskScheduler:
    def __init__(self, topology, data_loader, monitor=None):
        self.topology = topology
        self.data_loader = data_loader
        self.resource_monitor = monitor  # 添加 monitor 属性
        self.resources = {
            node_id: {
                "core": data["core_available"],
                "ram": data["ram_available"],
                "storage": data["storage_available"]
            } for node_id, data in self.data_loader.nodes.items()
        }
        self.task_queue = []
        self.current_sim_time = 0.0
        self.lock = threading.Lock()
        self.csv_writer = None
        self.csv_file = None
        self.init_csv()
        self.completed_tasks = []
        self.start_real_time = time.time()
        self.cache_lock = threading.Lock()
        self.path_cache = {}
        self.path_health_cache = {}
        self.timeout_queue = []
        self.task_queue = []
        # 用于统计任务类型的总任务量
        self.task_type_count = {}
        # 用于统计任务类型的成功任务量
        self.task_type_success_count = {}
        # 用于统计任务类型的任务时延
        self.task_type_total_latency = {}
        # 记录总任务量
        self.total_tasks = len(data_loader.tasks)
        for task in data_loader.tasks:
            task["GenTime"] = task.get("GenTime", 0.0)
            # 添加可排序元素（时间戳 + 任务 ID），确保 task_id 是字符串
            heapq.heappush(self.timeout_queue, (task["GenTime"], str(task["TaskID"]), task))

            # 初始化时统一转换时间基准
        for task in data_loader.tasks:
            task["GenTime"] = task.get("GenTime", 0.0)
            task["SendTime"] = task.get("SendTime", 0.0)
            task_id = str(task["TaskID"])  # 确保 task_id 是字符串
            heapq.heappush(self.task_queue, (task["SendTime"], task_id, task))

    def get_cached_path(self, start, end, request_size):
        """获取缓存的路径信息（含健康状态）"""
        with self.cache_lock:
            path = self.path_cache.get((start, end, request_size))
            if not path:
                path = self.topology.find_best_path(start, end, request_size)
                self.path_cache[(start, end, request_size)] = path
            health = self.check_path_health(path) if path else False
            return path, health

    def check_path_health(self, path_info):
        """检查路径健康状态"""
        if not path_info:
            logging.info("路径信息为空，路径不健康")
            return False
        for link in path_info:
            u, v = link['from'], link['to']
            try:
                link_data = self.topology.links[u][v]
                if link_data['used_bandwidth'] / link_data['bandwidth'] > 0.9:
                    logging.info(f"链路 {u}-{v} 带宽利用率超过阈值，路径不健康")
                    return False
            except KeyError:
                logging.info(f"链路 {u}-{v} 信息缺失，路径不健康")
                return False
        return True

    def init_csv(self):
        self.csv_file = open('任务历史记录.csv', 'w', newline='', encoding='utf-8')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            'TaskID', 'AppType', 'DeviceID', 'RequestSizeGB',
            'MaxLatencySec', 'DataLengthGB', 'CoreRequirement',
            'AccessNode', 'StartTime', 'EndTime', 'Status',
            'AssignedNode', 'ExecutionTime', 'TotalLatency', 'IsSuccess'
        ])

    def close_csv(self):
        if self.csv_file:
            self.csv_file.close()
            self.csv_writer = None

    def advance_simulation_time(self, delta_time):
        self.current_sim_time += delta_time
        timeout_threshold = self.current_sim_time - 300
        while self.timeout_queue:
            gen_time, _, task = self.timeout_queue[0]
            if gen_time >= timeout_threshold:
                break
            heapq.heappop(self.timeout_queue)
            if task not in self.completed_tasks:
                self.handle_failure(task, "仿真超时")
                self.completed_tasks.append(task)

    def run_scheduler(self):
        threads = []
        while self.task_queue:
            send_time, task_id, event_data = heapq.heappop(self.task_queue)
            if send_time > self.current_sim_time:
                time.sleep(send_time - self.current_sim_time)
                self.current_sim_time = send_time
            else:
                self.current_sim_time = max(self.current_sim_time, send_time)

            if isinstance(event_data, dict) and event_data.get("type") == "finish":
                self.release_resources(event_data["node"], event_data["task"])
                self.log_task_status(event_data["task"], "完成", self.current_sim_time)
                self.completed_tasks.append(event_data["task"])
                # 检查是否所有任务都已完成
                if len(self.completed_tasks) == self.total_tasks:
                    break
                continue

            task = event_data
            selected_node = self.select_node(task)
            if not selected_node:
                self.handle_failure(task, "无符合条件的节点")
                continue

            path, health = self.get_cached_path(task["AccessNode"], selected_node, task["RequestSizeGB"])
            if not health:
                self.handle_failure(task, "路径不健康")
                continue

            # 处理任务传输
            transmission_time = sum(link["latency"] for link in path) + task["RequestSizeGB"]/min(link["bandwidth"] for link in path)
            arrival_time = self.current_sim_time + transmission_time
            for link in path:
                src, dst = link["from"], link["to"]
                self.allocate_link_bandwidth(src, dst, task["RequestSizeGB"])
                # 更新链路资源信息
                self.update_link_stats(src, dst)

            # 等待节点资源可用，使用线程处理
            resource_thread = threading.Thread(target=self.wait_and_allocate_resources, args=(selected_node, task, arrival_time))
            resource_thread.start()
            threads.append(resource_thread)

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 新增：在调度器运行结束后打印统计信息
        self.print_statistics()

    def wait_and_allocate_resources(self, node_id, task, arrival_time):
        max_latency = task["MaxLatencySec"]
        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > max_latency:
                self.handle_failure(task, "等待节点资源时间超过最大容忍时延")
                return

            with self.lock:
                node = self.data_loader.nodes[node_id]
                required_core = task["CoreRequirement"]
                required_ram = task["DataLengthGB"]
                required_storage = task["DataLengthGB"]
                core_enough = node["core_available"] >= required_core
                ram_enough = node["ram_available"] >= required_ram
                storage_enough = node["storage_available"] >= required_storage

                if core_enough and ram_enough and storage_enough:
                    break
            time.sleep(0.1)

        # 分配节点资源
        try:
            self.allocate_resources(node_id, task)
            task["AssignedNode"] = node_id
            # 更新节点资源信息
            self.update_node_stats(node_id)
        except Exception as e:
            self.handle_failure(task, str(e))
            return

        node = self.data_loader.nodes[node_id]
        execution_time = task["DataLengthGB"] / (node["flops"]*task["CoreRequirement"])
        end_time = arrival_time + execution_time
        finish_event = {"type": "finish", "task": task, "node": node_id}
        task_id = str(task["TaskID"])  # 确保 task_id 是字符串
        with self.lock:
            # 确保 task_id 是字符串
            heapq.heappush(self.task_queue, (end_time, task_id, finish_event))
        task["StartTime"] = task["GenTime"]
        task["EndTime"] = end_time

    def update_node_stats(self, node_id):
        # 调用资源监控器的更新方法
        self.resource_monitor._collect_node_stats()

    def update_link_stats(self, src, dst):
        link_id = f"{src}-{dst}"
        # 调用资源监控器的更新方法
        self.resource_monitor._collect_link_stats()

    # def select_node(self, task):
    #     access_node = task["AccessNode"]
    #     max_latency = task["MaxLatencySec"]
    #     required_core = task["CoreRequirement"]
    #     required_ram = task["DataLengthGB"]
    #     required_storage = task["DataLengthGB"]
    #
    #     # 候选节点列表
    #     candidate_nodes = []
    #     for node_id, data in self.data_loader.nodes.items():
    #         if data["type"] in [0, 1]:  # 只考虑中心云和边缘云节点
    #             path, health = self.get_cached_path(access_node, node_id, task["RequestSizeGB"])
    #             if path and health:
    #                 latency = sum(link["latency"] for link in path)
    #                 if latency <= max_latency:
    #                     candidate_nodes.append(node_id)
    #
    #     if not candidate_nodes:
    #         return None
    #
    #     # 定义变量
    #     x = cp.Variable(len(candidate_nodes), boolean=True)  # 二进制变量，表示是否选择该节点
    #
    #     # 定义目标函数
    #     load_weights = []
    #     latency_weights = []
    #     for i, node_id in enumerate(candidate_nodes):
    #         data = self.data_loader.nodes[node_id]
    #         core_usage = (data["core_capacity"] - data["core_available"]) / data["core_capacity"]
    #         ram_usage = (data["ram_capacity"] - data["ram_available"]) / data["ram_capacity"]
    #         total_load = core_usage + ram_usage
    #         path, _ = self.get_cached_path(access_node, node_id, task["RequestSizeGB"])
    #         latency = sum(link["latency"] for link in path)
    #         load_weights.append(total_load)
    #         latency_weights.append(latency)
    #
    #     load_weight = 0.5  # 负载权重
    #     latency_weight = 0.5  # 延迟权重
    #     objective = cp.Minimize(load_weight * cp.sum(cp.multiply(load_weights, x)) + latency_weight * cp.sum(
    #         cp.multiply(latency_weights, x)))
    #
    #     # 定义约束条件
    #     constraints = []
    #     # 选择一个节点
    #     constraints.append(cp.sum(x) == 1)
    #
    #     # 资源约束
    #     for i, node_id in enumerate(candidate_nodes):
    #         data = self.data_loader.nodes[node_id]
    #         constraints.append(data["core_available"] - required_core * x[i] >= 0)
    #         constraints.append(data["ram_available"] - required_ram * x[i] >= 0)
    #         constraints.append(data["storage_available"] - required_storage * x[i] >= 0)
    #
    #     # 求解优化问题
    #     prob = cp.Problem(objective, constraints)
    #     prob.solve()
    #
    #     # 找到最优节点
    #     if prob.status == cp.OPTIMAL:
    #         for i, node_id in enumerate(candidate_nodes):
    #             if x.value[i] == 1:
    #                 return node_id
    #
    #     return None

    # 基于多目标粒子群算法的资源调度策略
    def select_node(self, task):
        access_node = task["AccessNode"]
        max_latency = task["MaxLatencySec"]

        # 筛选出所有可能的候选节点
        candidate_nodes = []
        for node_id, data in self.data_loader.nodes.items():
            if data["type"] in [0, 1]:  # 只考虑中心云和边缘云节点
                path, health = self.get_cached_path(access_node, node_id, task["RequestSizeGB"])
                if path and health:
                    latency = sum(link["latency"] for link in path)
                    if latency <= max_latency and data["core_available"] > task["CoreRequirement"] and \
                            data["ram_available"] > task["DataLengthGB"]:
                        candidate_nodes.append(node_id)

        if not candidate_nodes:
            # 如果没有符合条件的节点
            logging.error("无符合条件的候选节点")
            return None

        # 定义多目标优化问题
        class NodeSelectionProblem(Problem):
            def __init__(self, data_loader, get_cached_path, access_node, task):
                self.data_loader = data_loader
                self.get_cached_path = get_cached_path
                self.access_node = access_node
                self.task = task
                super().__init__(n_var=len(candidate_nodes), n_obj=2, n_constr=0, xl=0, xu=1)

            def _evaluate(self, X, out, *args, **kwargs):
                f1 = []  # 负载
                f2 = []  # 时延
                max_latency = task["MaxLatencySec"]
                for i in range(X.shape[0]):
                    selected_node_index = np.argmax(X[i])
                    selected_node = candidate_nodes[selected_node_index]
                    node_data = self.data_loader.nodes[selected_node]
                    path, _ = self.get_cached_path(self.access_node, selected_node, self.task["RequestSizeGB"])
                    latency = sum(link["latency"] for link in path)

                    # 计算节点的负载，这里简单地将核心、内存和存储的使用量相加
                    core_usage = (node_data["core_capacity"] - node_data["core_available"]) / node_data["core_capacity"]
                    ram_usage = (node_data["ram_capacity"] - node_data["ram_available"]) / node_data["ram_capacity"]
                    total_load = core_usage + ram_usage

                    f1.append(total_load/2)
                    f2.append(latency/(max_latency))

                out["F"] = np.column_stack([f1, f2])

        problem = NodeSelectionProblem(self.data_loader, self.get_cached_path, access_node, task)
        # 使用 NSGA2 算法
        algorithm = NSGA2(pop_size=10)

        res = minimize(problem,
                       algorithm,
                       ('n_gen', 10),
                       seed=1,
                       verbose=False)

        best_solution_index = np.argmax(res.X[0])
        best_node = candidate_nodes[best_solution_index]

        return best_node

    # 计算适应度的资源调度策略
    # def select_node(self, task):
    #     access_node = task["AccessNode"]
    #     max_latency = task["MaxLatencySec"]
    #     # 优先考虑边缘云节点
    #     edge_candidate_nodes = []
    #     cloud_candidate_nodes = []
    #
    #     for node_id, data in self.data_loader.nodes.items():
    #         if data["type"] == 1:  # 边缘云节点
    #             path, health = self.get_cached_path(access_node, node_id, task["RequestSizeGB"])
    #             if path and health:
    #                 latency = sum(link["latency"] for link in path)
    #                 if latency <= max_latency and data["core_available"] > task["CoreRequirement"] and \
    #                         data["ram_available"] > task["DataLengthGB"]:  # 筛选出符合时延要求的节点
    #                     # 计算节点的负载，这里简单地将核心、内存和存储的使用量相加
    #                     core_usage = (data["core_capacity"] - data["core_available"]) / data["core_capacity"]
    #                     ram_usage = (data["ram_capacity"] - data["ram_available"]) / data["ram_capacity"]
    #                     total_load = core_usage + ram_usage
    #                     edge_candidate_nodes.append((total_load, latency, node_id))
    #         elif data["type"] == 0:  # 中心云节点
    #             path, health = self.get_cached_path(access_node, node_id, task["RequestSizeGB"])
    #             if path and health:
    #                 latency = sum(link["latency"] for link in path)
    #                 if latency <= max_latency and data["core_available"] > task["CoreRequirement"] and \
    #                         data["ram_available"] > task["DataLengthGB"]:  # 筛选出符合时延要求的节点
    #                     # 计算节点的负载，这里简单地将核心、内存和存储的使用量相加
    #                     core_usage = (data["core_capacity"] - data["core_available"]) / data["core_capacity"]
    #                     ram_usage = (data["ram_capacity"] - data["ram_available"]) / data["ram_capacity"]
    #                     total_load = core_usage + ram_usage
    #                     cloud_candidate_nodes.append((total_load, latency, node_id))
    #
    #     # 优先选择边缘云节点
    #     if edge_candidate_nodes:
    #         edge_candidate_nodes.sort(key=lambda x: (x[0], x[1]))
    #         best_node = edge_candidate_nodes[0][2]
    #         return best_node
    #     elif cloud_candidate_nodes:
    #         cloud_candidate_nodes.sort(key=lambda x: (x[0], x[1]))
    #         best_node = cloud_candidate_nodes[0][2]
    #         return best_node
    #     else:
    #         # 如果都没有符合条件的节点
    #         logging.error("无符合条件的候选节点")
    #         return None

    # 基于贪心算法的资源调度策略
    # def select_node(self, task):
    #     access_node = task["AccessNode"]
    #     max_latency = task["MaxLatencySec"]
    #     # 优先考虑边缘云节点
    #     edge_candidate_nodes = []
    #     cloud_candidate_nodes = []
    #
    #     for node_id, data in self.data_loader.nodes.items():
    #         if data["type"] == 1:  # 边缘云节点
    #             path, health = self.get_cached_path(access_node, node_id, task["RequestSizeGB"])
    #             if path and health:
    #                 latency = sum(link["latency"] for link in path)
    #                 if latency <= max_latency and data["core_available"] > task["CoreRequirement"] and \
    #                         data["ram_available"] > task["DataLengthGB"]:  # 筛选出符合时延要求的节点
    #                     # 计算节点的负载，这里简单地将核心、内存的使用量相加
    #                     core_usage = (data["core_capacity"] - data["core_available"]) / data["core_capacity"]
    #                     ram_usage = (data["ram_capacity"] - data["ram_available"]) / data["ram_capacity"]
    #                     total_load = core_usage + ram_usage
    #                     # 贪心策略：计算一个综合评分，这里简单地将负载和时延相加
    #                     max_linklatency = max_latency - task["DataLengthGB"] / (data["flops"] * task["CoreRequirement"])
    #                     score = total_load / 2 + latency / max_linklatency
    #                     edge_candidate_nodes.append((score, total_load, latency, node_id))
    #         elif data["type"] == 0:  # 中心云节点
    #             path, health = self.get_cached_path(access_node, node_id, task["RequestSizeGB"])
    #             if path and health:
    #                 latency = sum(link["latency"] for link in path)
    #                 if latency <= max_latency and data["core_available"] > task["CoreRequirement"] and \
    #                         data["ram_available"] > task["DataLengthGB"]:  # 筛选出符合时延要求的节点
    #                     # 计算节点的负载，这里简单地将核心、内存的使用量相加
    #                     core_usage = (data["core_capacity"] - data["core_available"]) / data["core_capacity"]
    #                     ram_usage = (data["ram_capacity"] - data["ram_available"]) / data["ram_capacity"]
    #                     total_load = core_usage + ram_usage
    #                     # 贪心策略：计算一个综合评分，这里简单地将负载和时延相加
    #                     max_linklatency = max_latency - task["DataLengthGB"] / (data["flops"]*task["CoreRequirement"])
    #                     score = total_load/2 + latency/max_linklatency
    #                     cloud_candidate_nodes.append((score, total_load, latency, node_id))
    #
    #     # 优先选择边缘云节点
    #     if edge_candidate_nodes:
    #         edge_candidate_nodes.sort(key=lambda x: x[0])
    #         best_node = edge_candidate_nodes[0][3]
    #         return best_node
    #     elif cloud_candidate_nodes:
    #         cloud_candidate_nodes.sort(key=lambda x: x[0])
    #         best_node = cloud_candidate_nodes[0][3]
    #         return best_node
    #     else:
    #         logging.error("无符合条件的候选节点")
    #         return None

    def allocate_link_bandwidth(self, src, dst, request_size):
        with self.lock:
            link = self.topology.links[src][dst]
            while link["used_bandwidth"] + request_size > link["bandwidth"]:
                time.sleep(0.1)
            link["used_bandwidth"] += request_size
            # logging.info(f"为链路 {src}-{dst} 分配带宽 {request_size}GB，当前已使用带宽 {link['used_bandwidth']}GB")

    def allocate_resources(self, node_id, task):
        node = self.data_loader.nodes[node_id]
        required_core = task["CoreRequirement"]
        required_ram = task["DataLengthGB"]
        required_storage = task["DataLengthGB"]
        with self.lock:
            node["core_available"] -= required_core
            node["ram_available"] -= required_ram
            node["storage_available"] -= required_storage
            logging.info(
                f"为任务 {task['TaskID']} 分配节点 {node_id} 的资源：核心 {required_core}，内存 {required_ram}GB，存储 {required_storage}GB")

    def release_resources(self, node_id, task):
        node = self.data_loader.nodes[node_id]
        required_core = task["CoreRequirement"]
        required_ram = task["DataLengthGB"]
        required_storage = task["DataLengthGB"]
        with self.lock:
            node["core_available"] += required_core
            node["ram_available"] += required_ram
            node["storage_available"] += required_storage
            logging.info(
                f"为任务 {task['TaskID']} 释放节点 {node_id} 的资源：核心 {required_core}，内存 {required_ram}GB，存储 {required_storage}GB·")
            # 释放链路带宽
        access_node = task["AccessNode"]
        path, _ = self.get_cached_path(access_node, node_id, task["RequestSizeGB"])
        if path:
            for link in path:
                src, dst = link["from"], link["to"]
                self.release_link_bandwidth(src, dst, task["RequestSizeGB"])

    def release_link_bandwidth(self, src, dst, request_size):
        with self.lock:
            link = self.topology.links[src][dst]
            link["used_bandwidth"] -= request_size
            # 确保带宽使用量不会为负数
            link["used_bandwidth"] = max(0, link["used_bandwidth"])
            # logging.info(f"为链路 {src}-{dst} 释放带宽 {request_size}GB，当前已使用带宽 {link['used_bandwidth']}GB")

    def handle_failure(self, task, reason):
        task["Status"] = "失败"
        task["EndTime"] = self.current_sim_time
        task["AssignedNode"] = None
        execution_time = 0
        total_latency = self.current_sim_time - task["GenTime"]
        self.log_task_status(task, "失败", self.current_sim_time, execution_time, total_latency, reason)
        logging.error(f"任务 {task['TaskID']} 失败，原因：{reason}")

    def log_task_status(self, task, status, end_time, execution_time=None, total_latency=None, reason=None):
        if execution_time is None:
            node = self.data_loader.nodes.get(task["AssignedNode"])
            if node:
                execution_time = task["DataLengthGB"] / (node["flops"]*task["CoreRequirement"])
            else:
                execution_time = 0
        if total_latency is None:
            total_latency = end_time - task["GenTime"]

        # 判断任务是否成功
        if status == "完成":
            start_time = task["GenTime"]
            max_latency = task["MaxLatencySec"]
            actual_latency = end_time - start_time
            is_success = actual_latency < max_latency
        else:
            is_success = False

        row = [
            task["TaskID"], task["AppType"], task["DeviceID"], task["RequestSizeGB"],
            task["MaxLatencySec"], task["DataLengthGB"], task["CoreRequirement"],
            task["AccessNode"], task.get("StartTime", ""), end_time, status,
            task.get("AssignedNode", ""), execution_time, total_latency, is_success
        ]
        if reason:
            row.append(reason)
        self.csv_writer.writerow(row)
        self.csv_file.flush()

        # 只统计完成或失败状态的任务
        if status in ["完成", "失败"]:
            task_type = task["AppType"]
            self.task_type_count[task_type] = self.task_type_count.get(task_type, 0) + 1
            if is_success:
                self.task_type_success_count[task_type] = self.task_type_success_count.get(task_type, 0) + 1
                self.task_type_total_latency[task_type] = self.task_type_total_latency.get(task_type,
                                                                                           0) + actual_latency

    # 新增：打印统计信息的方法，并将信息输出到 CSV 文件
    def print_statistics(self):
        total_tasks = 0
        total_success_tasks = 0
        total_latency = 0
        stats = []
        for task_type, count in self.task_type_count.items():
            success_count = self.task_type_success_count.get(task_type, 0)
            success_rate = success_count / count if count > 0 else 0
            avg_latency = self.task_type_total_latency.get(task_type, 0) / success_count if success_count > 0 else 0
            stats.append([task_type, count, success_count, f"{success_rate * 100:.2f}%", f"{avg_latency:.2f}"])
            total_tasks += count
            total_success_tasks += success_count
            total_latency += self.task_type_total_latency.get(task_type, 0)

        total_success_rate = total_success_tasks / total_tasks if total_tasks > 0 else 0
        total_avg_latency = total_latency / total_success_tasks if total_success_tasks > 0 else 0
        stats.append(["总计", total_tasks, total_success_tasks, f"{total_success_rate * 100:.2f}%",
                      f"{total_avg_latency:.2f}"])

        # 将统计信息写入 CSV 文件
        with open('任务统计信息.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['任务类型', '总任务量', '成功任务量', '任务成功率', '平均时延'])
            for row in stats:
                writer.writerow(row)

    def format_time(self):
        return (datetime.min + timedelta(seconds=self.current_sim_time)).strftime('%H:%M:%S.%f')[:-3]

    def format_sim_time(self, sim_seconds):
        return (datetime.min + timedelta(seconds=sim_seconds)).strftime('%H:%M:%S.%f')[:-3]

    def __del__(self):
        self.close_csv()

