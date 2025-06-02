# -*- coding: utf-8 -*-

import numpy as np
import math
import pandas as pd

## 本文件为终端设备生成逻辑（地理位置和终端类型）

def generate_random_lat_lon(lat0, lon0, radius_km, n_samples, alpha=3):
    """ 生成符合幂律分布的经纬度坐标 """
    earth_radius = 6371.0  ##地球半径
    lat0_rad = math.radians(lat0)
    lon0_rad = math.radians(lon0)

    lats, lons = [], []
    for _ in range(n_samples):
        angle = np.random.uniform(0, 2 * np.pi)
        u = np.random.uniform(0, 1)
        distance = (u ** alpha) * radius_km
        angular_distance = distance / earth_radius

        new_lat = math.asin(
            math.sin(lat0_rad) * math.cos(angular_distance) +
            math.cos(lat0_rad) * math.sin(angular_distance) * math.cos(angle)
        )
        new_lon = lon0_rad + math.atan2(
            math.sin(angle) * math.sin(angular_distance) * math.cos(lat0_rad),
            math.cos(angular_distance) - math.sin(lat0_rad) * math.sin(new_lat)
        )
        lats.append(math.degrees(new_lat))
        lons.append(math.degrees(new_lon))
    return np.array(lats), np.array(lons)

def generate_device_data(output_path="终端设备数据.csv"):
    # 区域配置（含城市元数据）
    regions = [
        {"city": "北京市", "center": (39.90, 116.40), "radius": 60, "percentage": 0.1998},
        {"city": "天津市", "center": (39.10, 117.10), "radius": 50, "percentage": 0.1247},
        {"city": "石家庄市", "center": (38.08, 114.45), "radius": 60, "percentage": 0.1027},
        {"city": "唐山市", "center": (39.63, 118.18), "radius": 40, "percentage": 0.0706},
        {"city": "廊坊市", "center": (39.57, 116.74), "radius": 30, "percentage": 0.0501},
        {"city": "保定市", "center": (38.87, 115.46), "radius": 50, "percentage": 0.1046},
        {"city": "衡水市", "center": (37.74, 115.67), "radius": 30, "percentage": 0.038},
        {"city": "秦皇岛市", "center": (40.01, 119.75), "radius": 40, "percentage": 0.0839},
        {"city": "邯郸市", "center": (36.625, 114.54), "radius": 30, "percentage": 0.0284},
        {"city": "邢台市", "center": (37.06, 114.49), "radius": 40, "percentage": 0.0636},
        {"city": "张家口市", "center": (40.77, 114.885), "radius": 50, "percentage": 0.037},
        {"city": "承德市", "center": (40.95, 117.96), "radius": 50, "percentage": 0.0302},
        {"city": "沧州市", "center": (38.30, 116.84), "radius": 40, "percentage": 0.0664}
    ]
    # 参数验证
    assert np.isclose(sum(r["percentage"] for r in regions), 1.0, atol=1e-9), "百分比总和需为1"

    # 设备类型及接入方式
    DEVICE_TYPES = ['手机', '传感器', 'PC', 'laptop']
    ACCESS_METHODS = ['Cellular', 'Wifi', 'Ethernet']

    total_samples = 5000  # 总样本数
    device_data = []
    city_counters = {r['city']: 0 for r in regions}

    for region in regions:
        n_samples = int(round(total_samples * region["percentage"]))
        lats, lons = generate_random_lat_lon(*region["center"], region["radius"], n_samples)

        for i in range(n_samples):
            city = region['city']
            city_counters[city] += 1

            device_data.append({
                "设备ID": f"{city[:2]}-{city_counters[city]:04d}",
                "经度": round(lons[i], 6),
                "纬度": round(lats[i], 6),
                "所在城市": city,
                "设备类型": np.random.choice(DEVICE_TYPES),
                "接入方式": np.random.choice(ACCESS_METHODS)
            })

    device_df = pd.DataFrame(device_data)
    device_df.to_csv(output_path, index=False, encoding='utf_8_sig')
    return device_df