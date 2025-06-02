import matplotlib.pyplot as plt
import networkx as nx
# 设置中文字体支持
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False
# 创建图对象
G = nx.Graph()

# 添加节点（1-14）
nodes = [f"地点{i}" for i in range(1, 15)]
G.add_nodes_from(nodes)

# 添加边（根据之前的连接列表）
edges = [
    ("地点1", "地点2"), ("地点1", "地点3"), ("地点1", "地点6"), ("地点1", "地点14"),
    ("地点2", "地点1"), ("地点2", "地点4"), ("地点2", "地点8"),
    ("地点3", "地点1"), ("地点3", "地点4"), ("地点3", "地点5"),
    ("地点4", "地点2"), ("地点4", "地点3"), ("地点4", "地点7"),
    ("地点5", "地点3"), ("地点5", "地点6"), ("地点5", "地点9"),
    ("地点6", "地点1"), ("地点6", "地点5"), ("地点6", "地点7"), ("地点6", "地点10"),
    ("地点7", "地点4"), ("地点7", "地点6"), ("地点7", "地点8"),
    ("地点8", "地点2"), ("地点8", "地点7"), ("地点8", "地点9"),
    ("地点9", "地点5"), ("地点9", "地点8"), ("地点9", "地点10"),
    ("地点10", "地点6"), ("地点10", "地点9"), ("地点10", "地点11"),
    ("地点11", "地点10"), ("地点11", "地点12"), ("地点11", "地点13"),
    ("地点12", "地点11"), ("地点12", "地点13"), ("地点12", "地点14"),
    ("地点13", "地点11"), ("地点13", "地点12"), ("地点13", "地点14"),
    ("地点14", "地点1"), ("地点14", "地点12"), ("地点14", "地点13")
]
G.add_edges_from(edges)

# 使用spring_layout算法自动计算节点位置
pos = nx.spring_layout(G, k=0.3, iterations=50)

# 为不同区域的节点设置不同颜色
special_group = {"地点4", "地点9", "地点5"}  # 特殊组节点
node_colors = []
for node in G.nodes():
    if node in special_group:
        node_colors.append('lightcoral')  # 特殊组颜色
    elif int(node.replace("地点", "")) <= 10:
        node_colors.append('lightblue')  # 左侧区域节点
    else:
        node_colors.append('lightgreen')  # 右侧区域节点

# 计算节点连接数，用于设置节点大小
degrees = dict(G.degree())
max_degree = max(degrees.values())
node_sizes = [v * 500 / max_degree + 300 for v in degrees.values()]

# 绘制图形
plt.figure(figsize=(10, 8))

# 绘制节点
nx.draw_networkx_nodes(G, pos, node_size=node_sizes,
                       node_color=node_colors, alpha=0.8,
                       edgecolors='black', linewidths=1.5)

# 绘制边，根据连接数设置边的粗细
edge_widths = [d['weight']/2 if 'weight' in d else 1.0 for _, _, d in G.edges(data=True)]
nx.draw_networkx_edges(G, pos, width=edge_widths,
                       edge_color='gray', alpha=0.6)

# 绘制节点标签
nx.draw_networkx_labels(G, pos, font_size=6,
                        font_family='SimHei', font_weight='bold')

# 添加标题
plt.title("地点网络拓扑图", fontsize=16, fontweight='bold')

# 添加图例
#plt.scatter([], [], c='lightblue', alpha=0.8, s=50, edgecolor='black', label='区域1')
#plt.scatter([], [], c='lightgreen', alpha=0.8, s=50, edgecolor='black', label='区域2')
#plt.scatter([], [], c='lightcoral', alpha=0.8, s=50, edgecolor='black', label='区域3')
#plt.legend(scatterpoints=1, frameon=False, labelspacing=1, loc='upper right')

# 优化布局
plt.axis('off')
plt.tight_layout()

# 显示图形
plt.show()