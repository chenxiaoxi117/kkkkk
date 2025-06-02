# -*- coding: utf-8 -*-
import threading
import time
import logging
import csv


class ResourceMonitor:
    def __init__(self, nodes, links):
        self.nodes = nodes
        self.links = links
        self.monitoring = False
        self.monitor_thread = None
        self.node_stats = []
        self.link_stats = []

    def start_monitoring(self):
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        self._output_stats()

    def _monitor(self):
        while self.monitoring:
            # 监控节点资源
            node_stats = self._collect_node_stats()
            self.node_stats.append(node_stats)

            # 监控链路资源
            link_stats = self._collect_link_stats()
            self.link_stats.append(link_stats)

            time.sleep(1)  # 每秒监控一次

    def _collect_node_stats(self):
        stats = []
        for node_id, node in self.nodes.items():
            if node["type"] == 0 or node["type"] == 1:
                if node["core_capacity"] == 0:
                    core_usage = 0
                else:
                    core_usage = (node["core_capacity"] - node["core_available"]) / node["core_capacity"]
                if node["ram_capacity"] == 0:
                    ram_usage = 0
                else:
                    ram_usage = (node["ram_capacity"] - node["ram_available"]) / node["ram_capacity"]
                if node["storage_capacity"] == 0:
                    storage_usage = 0
                else:
                    storage_usage = (node["storage_capacity"] - node["storage_available"]) / node["storage_capacity"]
                stats.append({
                    "node_id": node_id,
                    "core_usage": core_usage,
                    "ram_usage": ram_usage,
                    "storage_usage": storage_usage
                })
        return stats

    def _collect_link_stats(self):
        stats = []
        for link_id, link in self.links.items():
            bandwidth_usage = link["used_bandwidth"] / link["bandwidth"]
            stats.append({
                "link_id": link_id,
                "bandwidth_usage": bandwidth_usage
            })
        return stats

    def _output_stats(self):
        # 输出节点资源统计信息
        with open('节点状态信息.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['node_id', 'core_avg_usage', 'core_max_usage',
                          # 'core_min_usage',
                          'ram_avg_usage', 'ram_max_usage',
                          # 'ram_min_usage',
                          # 'storage_avg_usage', 'storage_max_usage',
                          # 'storage_min_usage'
                          ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # 筛选出类型为0或1的节点ID
            valid_node_ids = [node_id for node_id, node in self.nodes.items() if node["type"] in [0, 1]]
            for node_id in valid_node_ids:
                core_usages = [stat["core_usage"] for node_stats in self.node_stats for stat in node_stats if
                               stat["node_id"] == node_id]
                ram_usages = [stat["ram_usage"] for node_stats in self.node_stats for stat in node_stats if
                              stat["node_id"] == node_id]
                storage_usages = [stat["storage_usage"] for node_stats in self.node_stats for stat in node_stats if
                                  stat["node_id"] == node_id]

                core_avg = sum(core_usages) / len(core_usages) if core_usages else 0
                core_max = max(core_usages) if core_usages else 0
                # core_min = min(core_usages) if core_usages else 0

                ram_avg = sum(ram_usages) / len(ram_usages) if ram_usages else 0
                ram_max = max(ram_usages) if ram_usages else 0
                # ram_min = min(ram_usages) if ram_usages else 0

                storage_avg = sum(storage_usages) / len(storage_usages) if storage_usages else 0
                storage_max = max(storage_usages) if storage_usages else 0
                # storage_min = min(storage_usages) if storage_usages else 0

                writer.writerow({
                    "node_id": node_id,
                    "core_avg_usage": "{:.2%}".format(core_avg),
                    "core_max_usage": "{:.2%}".format(core_max),
                    # "core_min_usage": "{:.2%}".format(core_min),
                    "ram_avg_usage": "{:.2%}".format(ram_avg),
                    "ram_max_usage": "{:.2%}".format(ram_max),
                    # "ram_min_usage": "{:.2%}".format(ram_min),
                    # "storage_avg_usage": "{:.2%}".format(storage_avg),
                    # "storage_max_usage": "{:.2%}".format(storage_max),
                    # "storage_min_usage": "{:.2%}".format(storage_min)
                })

        # 输出链路资源统计信息
        with open('带宽状态信息.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['link_id', 'bandwidth_avg_usage', 'bandwidth_max_usage',
                          # 'bandwidth_min_usage'
                          ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            link_ids = list(self.links.keys())
            for link_id in link_ids:
                bandwidth_usages = [stat["bandwidth_usage"] for link_stats in self.link_stats for stat in link_stats if
                                    stat["link_id"] == link_id]

                bandwidth_avg = sum(bandwidth_usages) / len(bandwidth_usages) if bandwidth_usages else 0
                bandwidth_max = max(bandwidth_usages) if bandwidth_usages else 0
                # bandwidth_min = min(bandwidth_usages) if bandwidth_usages else 0

                writer.writerow({
                    "link_id": link_id,
                    "bandwidth_avg_usage": "{:.2%}".format(bandwidth_avg),
                    "bandwidth_max_usage": "{:.2%}".format(bandwidth_max),
                    # "bandwidth_min_usage": "{:.2%}".format(bandwidth_min)
                })