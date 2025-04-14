import requests
import json

# API 地址和文件保存路径
api_url = "http://127.0.0.1:5000/api/v1/scheduling/result/device/export"
uuid_file_path = "../uuid.txt"
local_save_path_template = "device_results_{sch_uuid}.csv"

try:
    # 从文件中读取 schUuid
    with open(uuid_file_path, "r") as file:
        sch_uuid = file.readline().strip()  # 去掉换行符和多余空格
    # 构造请求
    payload = {'schUuid': sch_uuid}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(api_url, json=payload, headers=headers)  # 使用 json 参数自动序列化
    # 检查响应状态码
    if response.status_code == 200 and "text/csv" in response.headers.get("Content-Type", ""):
        # 解码内容，移除多余空行
        text_data = "\n".join(line for line in response.text.splitlines() if line.strip())
        # text_data =  response.text
        # 保存到本地文件
        local_save_path = local_save_path_template.format(sch_uuid=sch_uuid)
        with open(local_save_path, 'w', encoding='utf-8') as file:
            file.write(text_data)
        print(f"文件已成功下载并保存至：{local_save_path}")
    else:
        # 处理错误响应
        error_msg = response.json().get("errorMsg", "未知错误")
        print(f"请求失败，状态码：{response.status_code}, 错误信息：{error_msg}")
except Exception as e:
    print(f"请求出错：{e}")
