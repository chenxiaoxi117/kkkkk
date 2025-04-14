import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeRegressor
import torch
import torch.nn as nn
import torch.optim as optim
import joblib  # 用于保存编码器

# ----------- 读取数据并准备训练 ----------
df = pd.read_csv("sorted_tasks.csv")

# 将Net Device ID进行数字编码
net_device_encoder = LabelEncoder()
df['Net Device ID'] = net_device_encoder.fit_transform(df['Net Device ID'])

# 将 Task Type 进行数字编码
task_type_encoder = LabelEncoder()
df['Task Type'] = task_type_encoder.fit_transform(df['Task Type'])

# 特征选择
features = ['Net Device ID', 'Request Size', 'Task Length', 'Max Latency', 'Task Type']
X = df[features]  # 特征
y = df['Delay Margin']  # 标签

# ----------- 训练决策树模型 -----------

# 划分训练集和测试集（80%训练，20%测试）
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 初始化并训练sklearn模型（决策树回归模型）
model = DecisionTreeRegressor(random_state=42)
model.fit(X_train, y_train)

# 保存决策树模型
joblib.dump(model, 'decision_tree_model.pkl')

# 进行预测
df['Predictions'] = model.predict(X)  # 用整个数据集进行预测

# 保存新的数据表格
df.to_csv('sorted_tasks_with_predictions.csv', index=False)

# ----------- 训练神经网络模型并保存 -----------

# 将数据转为 PyTorch Tensor
X_tensor = torch.tensor(X.values, dtype=torch.float32)
y_tensor = torch.tensor(y.values, dtype=torch.float32).view(-1, 1)  # 转为二维 tensor

# 创建 PyTorch 数据集
dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
dataloader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)

# 定义一个简单的神经网络模型
class SimpleNN(nn.Module):
    def __init__(self):
        super(SimpleNN, self).__init__()
        self.fc1 = nn.Linear(5, 64)  # 输入层到隐藏层（5个特征）
        self.fc2 = nn.Linear(64, 32)  # 隐藏层
        self.fc3 = nn.Linear(32, 1)   # 输出层（1个延迟裕度）

    def forward(self, x):
        x = torch.relu(self.fc1(x))  # ReLU 激活函数
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)  # 不加激活函数，回归问题
        return x

# 初始化并训练神经网络模型
nn_model = SimpleNN()
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(nn_model.parameters(), lr=0.001)

# 训练模型
epochs = 10
for epoch in range(epochs):
    nn_model.train()
    for inputs, labels in dataloader:
        optimizer.zero_grad()
        outputs = nn_model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

    print(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}")

# 保存神经网络模型
torch.save(nn_model.state_dict(), 'simple_nn_model.pt')

# ----------- 保存编码器 -----------
joblib.dump(net_device_encoder, 'net_device_encoder.pkl')  # 保存 Net Device ID 编码器
joblib.dump(task_type_encoder, 'task_type_encoder.pkl')  # 保存 Task Type 编码器

print("模型、编码器已保存成功！")
