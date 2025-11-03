# Quantbox 配置指南

## 配置文件位置

用户配置文件位于：`~/.quantbox/settings/config.toml`

### 自动配置

Quantbox 会在首次使用时自动初始化配置，无需手动创建：

- ✅ **自动创建** 配置目录和文件
- ✅ **自动复制** 配置模板
- ✅ **自动显示** 配置说明和下一步操作

### 手动配置（可选）

如需重新初始化配置：

```bash
# 初始化配置
quantbox-config

# 强制覆盖现有配置
quantbox-config --force

# 使用自定义配置目录
quantbox-config --config-dir /path/to/config
```

## 配置文件格式

```toml
# Tushare Pro API 配置
[TSPRO]
token = "your_tushare_token_here"

# 掘金量化 API 配置
[GM]
token = "your_goldminer_token_here"

# MongoDB 数据库配置
[MONGODB]
uri = "mongodb://localhost:27017"
```

## 配置说明

### Tushare Pro Token 配置

1. 访问 https://tushare.pro/register 注册账号
2. 登录后在个人中心获取您的 token
3. 将 token 复制到配置文件的 `token` 字段中

### MongoDB 配置

- **本地 MongoDB**: `mongodb://localhost:27017`
- **远程 MongoDB**: `mongodb://username:password@host:port/database`
- **MongoDB Atlas**: `mongodb+srv://username:password@cluster.mongodb.net/database`

### 掘金量化 Token 配置

1. 访问 https://www.myquant.cn 注册账号
2. 获取 API token
3. 将 token 复制到配置文件中

## 环境变量支持

系统也支持通过环境变量进行配置：

```bash
export TUSHARE_TOKEN="your_tushare_token"
export MONGODB_URI="mongodb://localhost:27017"
```

环境变量的优先级高于配置文件。

## 配置验证

运行以下代码验证配置是否正确：

```python
from quantbox.config.config_loader import get_config_loader

config = get_config_loader()

# 验证 Tushare 配置
token = config.get_tushare_token()
pro = config.get_tushare_pro()
print(f"Tushare 配置: {token is not None and pro is not None}")

# 验证 MongoDB 配置
uri = config.get_mongodb_uri()
client = config.get_mongodb_client()
print(f"MongoDB 配置: {uri is not None}")
```