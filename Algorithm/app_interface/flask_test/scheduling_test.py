import requests
import time

# 定义测试的API URL
url = 'http://127.0.0.1:5000/api/v1/scheduling/task/start'  # 替换为实际的服务器地址
data = {
    "scenario": 1,  # 调度任务场景
    "appInfo": [  # 任务应用信息
        {"name": "Low latency", "category": 1, "value": 40},
        {"name": "High computing power", "category": 2, "value": 40},
        {"name": "High bandwidth", "category": 3, "value": 14},
        {"name": "Low latency + High computing power", "category": 4, "value": 1},
        {"name": "Low latency + High computing power (Dedicated line for large customers)", "category": 5, "value": 1},
        {"name": "Low latency + High computing power + High bandwidth", "category": 6, "value": 1},
        {"name": "Apply for virtual machine", "category": 7, "value": 1},
        {"name": "Long-term occupation of network resources", "category": 8, "value": 1},
        {"name": "Less sensitive tasks", "category": 9, "value": 1}
        
    ],
    "deviceTotal": 200000,  # 终端设备总数
    "deviceInfo": [  # 各城市设备信息
        {"city": "北京", "value": 0.19975},
        {"city": "天津", "value": 0.12465},
        {"city": "石家庄", "value": 0.10266},
        {"city": "衡水", "value": 0.03799},
        {"city": "唐山", "value": 0.07054},
        {"city": "邯郸", "value": 0.08383},
        {"city": "秦皇岛", "value": 0.02840},
        {"city": "保定", "value": 0.10498},
        {"city": "张家口", "value": 0.037012},
        {"city": "承德", "value": 0.030177},
        {"city": "廊坊", "value": 0.05006},
        {"city": "沧州", "value": 0.066387},
        {"city": "邢台", "value": 0.063562}
    ],
    "algorithm": 3,  # 调度算法
    "other": "测试附加信息"  # 其他必要信息
}

    
try:
    response = requests.post(url, json=data)
    print(f"Task Start Response: {response.status_code}, {response.json()}")
except Exception as e:
    print(f"Task Start Error: {e}")

