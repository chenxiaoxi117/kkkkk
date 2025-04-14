import requests
import json
# 需要替换为实际的时延范围

# 设备属性和路径，这里仅作为示例，根据实际情况填写
filter_criteria = {
     # "deviceId": 756,  # 设备ID（如果需要精确匹配，确保是整数或字符串）
     #"path": ["节点1", "节点2", "节点3"],  # 路径，注意这里是一个列表
      "attribute": "低时延+高算力+大带宽",  # 如果你需要过滤特定的特性
     # "origin": "北京城域2",  # ，如需要匹配
     #"assigned": "天津中心云"  # 设备分配地，如需要匹配
      "min_latency": 0 ,     #对应最小时延
      "max_latency": 100 ,  #对应最大时延
      "status": 1
}
with open("../uuid.txt", "r") as file:
    sch_uuid = file.readline().strip()  # 去掉换行符和多余空格
# POST请求的JSON数据
data = {
    "schUuid": sch_uuid,  # 任务UUID，假设为'request_001'
    "filter": filter_criteria,
    "pageSize": 100,    # 每页条数
    "pageNumber": 1  # 当前页码
}
# 测试后端接口
url = "http://127.0.0.1:5000/api/v1/scheduling/result/device"
response = requests.post(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})

# 检查响应状态码
if response.status_code == 200:
    # 如果成功，则处理响应数据
    response_data = response.json()
    print("返回结果：")
    for result in response_data["message"]:
        print(result)
else:
    print(f"请求失败，状态码：{response.status_code}, 原因：{response.text}")