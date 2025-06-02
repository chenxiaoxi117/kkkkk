import pandas as pd

# 定义 AppType 及其对应的时延阈值
app_type_thresholds = {
    1: 50,
    2: 60,
    3: 100,
    4: 100,
    5: 100,
    6: 100,
    7: 100,
    8: 100,
    9: 100
}

# 读取 link.csv 文件
link_path = 'data/resource/link.csv'
link_data = pd.read_csv(link_path)

# 假设 link.csv 文件中时延列名为 'lantency'，你可以根据实际情况修改
if 'lantency' not in link_data.columns:
    raise ValueError("link.csv 文件中未找到 'lantency' 列，请检查列名。")

# 筛选出大于各 AppType 时延阈值的数据，并添加 AppType 列
tabu_rows = []
for app_type, threshold in app_type_thresholds.items():
    filtered_rows = link_data[link_data['lantency'] > threshold].copy()
    filtered_rows['AppType'] = app_type
    tabu_rows.append(filtered_rows)

# 合并所有筛选结果
tabu_table = pd.concat(tabu_rows, ignore_index=True)

# 导出为禁忌表
file_name = 'tabu_table.csv'
tabu_table.to_csv(file_name, index=False)
print(f"已导出禁忌表到 {file_name}")