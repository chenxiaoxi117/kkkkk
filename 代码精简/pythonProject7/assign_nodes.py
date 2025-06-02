# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2

## 本文件负责分配终端任务的接入节点，按照就近原则分配，同时计算任务接入延迟

def haversine(lon1, lat1, lon2, lat2):
    # 计算两个经纬度点间的距离（公里）
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return 6371 * c  # 地球半径公里

def find_nearest_node(device_lon, device_lat, nodes_df, node_type):
    # 筛选指定类型节点并计算距离
    filtered_nodes = nodes_df[nodes_df['类型'] == node_type]
    distances = filtered_nodes.apply(
        lambda row: haversine(device_lon, device_lat, row['经度'], row['纬度']),
        axis=1
    )
    if distances.empty:
        return None
    nearest_idx = distances.idxmin()
    return filtered_nodes.loc[nearest_idx, '名称']

def get_lowest_latency_man(node_name, connections_df):
    # 查找直接连接的城域网节点中时延最小的
    direct_links = connections_df[
        (connections_df['destination_id'] == node_name) &
        (connections_df['source_id'].str.contains('man'))
    ]
    if direct_links.empty:
        return None
    return direct_links.nsmallest(1, 'lantency').iloc[0]

def assign_nodes(device_df, cloud_edge_path, connections_path):
    cloud_edge_df = pd.read_csv(cloud_edge_path)
    connections_df = pd.read_csv(connections_path)

    # 计算最近节点（内部使用，不保留在最终输出）
    device_df['_tmp_cloud'] = device_df.apply(
        lambda row: find_nearest_node(row['经度'], row['纬度'], cloud_edge_df, '中心云'),
        axis=1
    )
    device_df['_tmp_edge'] = device_df.apply(
        lambda row: find_nearest_node(row['经度'], row['纬度'], cloud_edge_df, '边缘云'),
        axis=1
    )

    # 计算接入节点
    def choose_access_node(row):
        cloud_man = get_lowest_latency_man(row['_tmp_cloud'], connections_df) if row['_tmp_cloud'] else None
        edge_man = get_lowest_latency_man(row['_tmp_edge'], connections_df) if row['_tmp_edge'] else None

        candidates = []
        if cloud_man is not None:
            candidates.append(cloud_man)
        if edge_man is not None:
            candidates.append(edge_man)

        if not candidates:
            return (None, np.nan)

        # 选择时延最小的节点
        best = min(candidates, key=lambda x: x['lantency'])
        return (best['source_id'], best['lantency'])

    # 应用选择逻辑
    access_info = device_df.apply(choose_access_node, axis=1, result_type='expand')
    device_df['接入节点'], device_df['接入时延'] = access_info[0], access_info[1]

    # 删除临时列
    device_df.drop(columns=['_tmp_cloud', '_tmp_edge'], inplace=True)

    # 根据接入方式生成时延（保留原有逻辑）
    latency_ranges = {'Cellular': (1, 8), 'Wifi': (1, 5), 'Ethernet': (1, 2)}
    device_df['接入时延'] = device_df.apply(
        lambda row: np.random.uniform(*latency_ranges[row['接入方式']]),
        axis=1
    )

    return device_df