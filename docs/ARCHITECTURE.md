# Quantbox 架构文档

## 概述

Quantbox 采用清晰的**三层架构**设计，将系统职责明确分离，提高可维护性和可扩展性。本文档详细说明了系统架构、设计模式和各层职责。

## 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
│            (CLI, GUI, User Scripts, Jupyter)            │
│                                                          │
│  用户直接交互的层，调用服务层提供的高级接口              │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Services Layer                        │
│  ┌───────────────────┐      ┌─────────────────────┐    │
│  │ MarketDataService │      │ DataSaverService    │    │
│  │                   │      │                     │    │
│  │ • 智能数据源选择   │      │ • 批量数据保存      │    │
│  │ • 统一查询接口     │      │ • 数据验证清洗      │    │
│  │ • 缓存管理         │      │ • 错误处理         │    │
│  └───────────────────┘      └─────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Adapters Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │LocalAdapter  │  │ TSAdapter    │  │ GMAdapter    │  │
│  │              │  │              │  │              │  │
│  │MongoDB数据源 │  │Tushare数据源 │  │掘金数据源    │  │
│  │• 本地查询     │  │• 远程API     │  │• 远程API     │  │
│  │• 高速访问     │  │• 标准化处理  │  │• 实时数据    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│       统一接口：BaseDataAdapter (IDataAdapter)           │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     Utils Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ date_utils   │  │exchange_utils│  │contract_utils│  │
│  │              │  │              │  │              │  │
│  │日期转换工具   │  │交易所代码     │  │合约代码解析  │  │
│  │类型统一处理   │  │格式转换       │  │多格式支持    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│              纯函数，无状态，可独立使用                  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│              External Systems / Storage                  │
│                                                          │
│    MongoDB        Tushare API      GoldMiner API        │
└─────────────────────────────────────────────────────────┘
```

## 层级职责

### 1. Utils Layer（工具层）

**职责**：提供纯函数工具，处理数据格式转换和验证

**特点**：
- 无状态
- 纯函数
- 可独立使用
- 无外部依赖

**核心模块**：

#### date_utils.py
```python
# 日期格式转换
date_to_int(date) -> int          # 任意格式 → 20240131
int_to_date_str(date_int) -> str  # 20240131 → "2024-01-31"
date_to_str(date, format) -> str  # 自定义格式转换
```

#### exchange_utils.py
```python
# 交易所代码标准化
normalize_exchange(code) -> str     # SSE/SHSE → SHSE
denormalize_exchange(code, target)  # SHSE → SH (for Tushare)
validate_exchanges(codes) -> list   # 批量验证和标准化
```

#### contract_utils.py
```python
# 合约代码解析和转换
parse_contract(code) -> ContractInfo    # 解析合约信息
format_contract(code, format) -> str    # 格式转换
normalize_contracts(codes) -> list      # 批量标准化
```

### 2. Adapters Layer（适配器层）

**职责**：封装不同数据源的访问逻辑，提供统一接口

**设计模式**：适配器模式（Adapter Pattern）

**核心接口**：

```python
class BaseDataAdapter(ABC):
    """所有适配器的基类"""
    
    @abstractmethod
    def get_trade_calendar(...) -> pd.DataFrame:
        """获取交易日历"""
        pass
    
    @abstractmethod
    def get_future_contracts(...) -> pd.DataFrame:
        """获取期货合约"""
        pass
    
    @abstractmethod
    def get_future_daily(...) -> pd.DataFrame:
        """获取日线数据"""
        pass
    
    @abstractmethod
    def get_future_holdings(...) -> pd.DataFrame:
        """获取持仓数据"""
        pass
```

**适配器实现**：

#### LocalAdapter (690行)
- **数据源**：MongoDB
- **特点**：快速、免费、离线可用
- **使用场景**：常规数据查询、回测
- **性能**：< 10ms 查询时间

#### TSAdapter (460行)
- **数据源**：Tushare API
- **特点**：数据全面、更新及时
- **使用场景**：数据更新、补充本地数据
- **性能**：< 500ms API 调用

#### GMAdapter (待实现)
- **数据源**：掘金量化 API
- **特点**：实时数据、高频tick
- **使用场景**：实时行情、高频策略

### 3. Services Layer（服务层）

**职责**：提供高级业务逻辑，协调适配器，实现智能功能

**设计模式**：服务模式（Service Pattern）+ 策略模式（Strategy Pattern）

**核心服务**：

#### MarketDataService (218行)

**功能**：
- 智能数据源选择（本地优先）
- 自动数据源切换
- 统一查询接口
- 参数验证和标准化

**工作流程**：
```
用户查询请求
    ↓
参数验证和标准化
    ↓
选择数据源 (prefer_local?)
    ↓
LocalAdapter 可用? → Yes → 查询并返回
    ↓ No
TSAdapter 查询 → 返回结果
```

**使用示例**：
```python
service = MarketDataService()

# 自动选择：本地优先
data = service.get_trade_calendar()

# 强制远程
data = service.get_trade_calendar(use_local=False)
```

#### DataSaverService (418行)

**功能**：
- 从远程获取数据
- 批量 upsert 操作
- 自动索引创建
- 数据去重
- 错误追踪

**工作流程**：
```
用户保存请求
    ↓
从 Remote Adapter 获取数据
    ↓
数据验证和清洗
    ↓
转换为字典列表
    ↓
创建/检查索引
    ↓
批量 upsert (UpdateOne with upsert=True)
    ↓
返回 SaveResult (inserted_count, modified_count)
```

**使用示例**：
```python
saver = DataSaverService()

result = saver.save_trade_calendar(
    exchanges=["SHSE", "SZSE"],
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print(f"新增: {result.inserted_count}")
print(f"更新: {result.modified_count}")
```

## 数据流

### 查询流程

```
┌──────────┐
│  用户请求  │
└─────┬────┘
      │
      ▼
┌──────────────────┐
│ MarketDataService │
│  • 验证参数       │
│  • 选择数据源     │
└─────┬───────────┘
      │
      ├─→ prefer_local=True ?
      │
      ▼ Yes
┌──────────────────┐
│  LocalAdapter    │
│  • 查询 MongoDB   │
│  • 数据完整? Yes  │ ──→ 返回结果
└─────┬───────────┘
      │ No / 不可用
      ▼
┌──────────────────┐
│   TSAdapter      │
│  • 调用API       │
│  • 格式转换       │ ──→ 返回结果
└──────────────────┘
```

### 保存流程

```
┌──────────┐
│  用户请求  │
└─────┬────┘
      │
      ▼
┌──────────────────┐
│ DataSaverService │
│  • 验证参数       │
└─────┬───────────┘
      │
      ▼
┌──────────────────┐
│  TSAdapter       │
│  • 调用API       │
│  • 获取原始数据   │
└─────┬───────────┘
      │
      ▼
┌──────────────────┐
│  数据处理         │
│  • DataFrame→Dict │
│  • 字段验证       │
└─────┬───────────┘
      │
      ▼
┌──────────────────┐
│  MongoDB         │
│  • 创建索引       │
│  • Bulk Upsert   │
│  • 去重处理       │
└─────┬───────────┘
      │
      ▼
┌──────────────────┐
│  SaveResult      │
│  • 统计结果       │
│  • 错误信息       │
└──────────────────┘
```

## 设计模式

### 1. 适配器模式（Adapter Pattern）

**目的**：统一不同数据源的接口

**实现**：
```python
# 所有适配器继承同一基类
class LocalAdapter(BaseDataAdapter):
    def get_trade_calendar(...):
        # MongoDB 实现
        
class TSAdapter(BaseDataAdapter):
    def get_trade_calendar(...):
        # Tushare API 实现
```

### 2. 服务模式（Service Pattern）

**目的**：封装业务逻辑，提供高级接口

**实现**：
```python
class MarketDataService:
    def __init__(self, local_adapter, remote_adapter):
        self.local = local_adapter
        self.remote = remote_adapter
    
    def get_xxx(self):
        # 协调多个适配器
```

### 3. 策略模式（Strategy Pattern）

**目的**：动态选择数据源

**实现**：
```python
def _get_adapter(self, use_local: bool):
    if use_local and self.local.check_availability():
        return self.local
    return self.remote
```

### 4. 工厂模式（Factory Pattern）

**目的**：创建合适的适配器实例

**实现**：
```python
class AdapterFactory:
    @staticmethod
    def create_adapter(type: str):
        if type == "local":
            return LocalAdapter()
        elif type == "tushare":
            return TSAdapter()
```

## 模块依赖图

```
services
  ├── market_data_service
  │   ├── adapters.local_adapter
  │   ├── adapters.ts_adapter
  │   └── util.date_utils
  │
  └── data_saver_service
      ├── adapters.local_adapter
      ├── adapters.ts_adapter
      └── util.date_utils

adapters
  ├── local_adapter
  │   ├── util.date_utils
  │   ├── util.exchange_utils
  │   └── util.contract_utils
  │
  └── ts_adapter
      ├── util.date_utils
      ├── util.exchange_utils
      └── util.contract_utils

util
  ├── date_utils (独立)
  ├── exchange_utils (独立)
  └── contract_utils
      └── util.exchange_utils
```

## 扩展性

### 添加新的数据源

1. **创建新适配器**：
```python
class NewAdapter(BaseDataAdapter):
    def __init__(self, api_key):
        super().__init__("NewAdapter")
        self.api = SomeAPI(api_key)
    
    def get_trade_calendar(...):
        # 实现获取逻辑
```

2. **在服务中使用**：
```python
service = MarketDataService(
    local_adapter=LocalAdapter(),
    remote_adapter=NewAdapter()  # 使用新适配器
)
```

### 添加新的数据类型

1. **在适配器基类添加方法**：
```python
class BaseDataAdapter:
    def get_option_data(...):
        raise NotImplementedError()
```

2. **各适配器实现**：
```python
class LocalAdapter:
    def get_option_data(...):
        # MongoDB 实现

class TSAdapter:
    def get_option_data(...):
        # Tushare 实现
```

3. **服务层暴露接口**：
```python
class MarketDataService:
    def get_option_data(...):
        adapter = self._get_adapter()
        return adapter.get_option_data(...)
```

## 性能优化

### 查询优化
- **本地优先**：减少API调用
- **索引优化**：MongoDB 自动创建合适索引
- **批量操作**：使用 bulk_write

### 内存优化
- **流式处理**：大数据集使用 iterator
- **延迟加载**：按需加载数据
- **连接池**：复用数据库连接

### 并发支持
- **线程安全**：适配器无状态设计
- **连接管理**：每线程独立连接
- **锁机制**：写操作使用合适的锁

## 最佳实践

### 1. 使用服务层而非直接调用适配器

```python
# ✅ 推荐
from quantbox.services import MarketDataService
service = MarketDataService()
data = service.get_trade_calendar()

# ❌ 不推荐
from quantbox.adapters import TSAdapter
adapter = TSAdapter()
data = adapter.get_trade_calendar()
```

### 2. 合理选择数据源

```python
# 日常查询：使用本地
data = service.get_trade_calendar()  # 本地优先

# 数据更新：强制远程
data = service.get_trade_calendar(use_local=False)

# 离线使用：只用本地
data = service.get_trade_calendar(use_local=True)
```

### 3. 错误处理

```python
try:
    result = saver.save_trade_calendar(...)
    if result.success:
        print(f"成功: {result.inserted_count}")
    else:
        print(f"失败: {result.errors}")
except Exception as e:
    print(f"异常: {e}")
```

## 总结

Quantbox 的三层架构设计具有以下优势：

1. **职责清晰**：每层专注自己的职责
2. **易于扩展**：添加新数据源或新功能很简单
3. **易于测试**：每层可独立测试
4. **易于维护**：修改一层不影响其他层
5. **代码复用**：工具层和适配器可独立使用

这种架构使 Quantbox 成为一个可靠、高效、易用的金融数据框架。
