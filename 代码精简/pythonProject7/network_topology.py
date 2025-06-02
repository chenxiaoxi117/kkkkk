# -*- coding: utf-8 -*-
import heapq


class NetworkTopology:
    def __init__(self, nodes, links):
        self.nodes = nodes
        self.links = {}
        for link_id, link in links.items():
            # 找到第二个 - 的位置
            dash_count = 0
            second_dash_index = -1
            for i, char in enumerate(link_id):
                if char == '-':
                    dash_count += 1
                    if dash_count == 2:
                        second_dash_index = i
                        break

            if second_dash_index == -1:
                print(f"警告: 链路 ID {link_id} 格式不正确，跳过该链路。")
                continue

            src = link_id[:second_dash_index]
            dst = link_id[second_dash_index + 1:]

            if src not in self.links:
                self.links[src] = {}
            if dst not in self.links:
                self.links[dst] = {}
            self.links[src][dst] = link
            self.links[dst][src] = {
                "bandwidth": link["reverse_bandwidth"],
                "latency": link["reverse_latency"],
                "used_bandwidth": 0
            }

    def find_best_path(self, start, end, request_size):
        """使用综合考虑带宽利用率和时延的算法查找最佳路径"""
        distances = {node: float('inf') for node in self.nodes}
        distances[start] = 0
        priority_queue = [(0, start)]
        previous_nodes = {node: None for node in self.nodes}

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_node == end:
                path = []
                while current_node is not None:
                    path.insert(0, current_node)
                    current_node = previous_nodes[current_node]
                link_path = []
                for i in range(len(path) - 1):
                    src = path[i]
                    dst = path[i + 1]
                    link_path.append({
                        "from": src,
                        "to": dst,
                        "latency": self.links[src][dst]["latency"],
                        "bandwidth": self.links[src][dst]["bandwidth"]
                    })
                return link_path

            if current_distance > distances[current_node]:
                continue

            for neighbor, link in self.links.get(current_node, {}).items():
                # 检查链路是否有足够的带宽
                if link["used_bandwidth"] + request_size <= link["bandwidth"]:
                    # 计算综合评分，这里简单地将时延和带宽利用率相加
                    utilization = link["used_bandwidth"] / link["bandwidth"]
                    score = current_distance + link["latency"] + utilization
                    if score < distances[neighbor]:
                        distances[neighbor] = score
                        previous_nodes[neighbor] = current_node
                        heapq.heappush(priority_queue, (score, neighbor))

        return None

    # def find_shortest_path(self, start, end):
    #     """使用 Dijkstra 算法查找最短路径"""
    #     distances = {node: float('inf') for node in self.nodes}
    #     distances[start] = 0
    #     priority_queue = [(0, start)]
    #     previous_nodes = {node: None for node in self.nodes}
    #
    #     while priority_queue:
    #         current_distance, current_node = heapq.heappop(priority_queue)
    #
    #         if current_node == end:
    #             path = []
    #             while current_node is not None:
    #                 path.insert(0, current_node)
    #                 current_node = previous_nodes[current_node]
    #             link_path = []
    #             for i in range(len(path) - 1):
    #                 src = path[i]
    #                 dst = path[i + 1]
    #                 link_path.append({
    #                     "from": src,
    #                     "to": dst,
    #                     "latency": self.links[src][dst]["latency"],
    #                     "bandwidth": self.links[src][dst]["bandwidth"]
    #                 })
    #             return link_path
    #
    #         if current_distance > distances[current_node]:
    #             continue
    #
    #         for neighbor, link in self.links.get(current_node, {}).items():
    #             distance = current_distance + link["latency"]
    #             if distance < distances[neighbor]:
    #                 distances[neighbor] = distance
    #                 previous_nodes[neighbor] = current_node
    #                 heapq.heappush(priority_queue, (distance, neighbor))
    #
    #     return None
