# Quantbox 重构设计文档

## 1. 重构背景与目标

### 1.1 重构背景

当前 quantbox 项目存在以下问题：

1. **接口设计复杂**：多个数据获取器（TSFetcher, GMFetcher, LocalFetcher, RemoteFetcher），接口不统一
2. **命名不一致**：如 `fetch_get_trade_dates` 和 `fetch_trade_dates` 混用
3. **交易所代码混乱**：SSE/SHSE 混用，需要频繁转换
4. **日期格式多样**：整数、字符串、datetime 对象混用
5. **代码重复**：各个 fetcher 有大量重复的参数验证和转换逻辑
6. **缺乏统一标准**：没有明确的编码规范文档

### 1.2 重构目标

1. **简化接口设计**：统一数据获取接口，减少类的数量和复杂度
2. **规范命名**：统一函数、变量、参数命名
3. **标准化数据格式**：明确日期、交易所代码、合约代码的标准格式
4. **提升可维护性**：减少代码重复，提高代码质量
5. **保证期货数据能力**：优先确保期货行情查询和本地化功能正常

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│                  (CLI, GUI, Scripts)                     │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     Service Layer                        │
│  ┌───────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │ MarketData    │  │ DataSaver   │  │ Validators   │  │
│  │ Service       │  │ Service     │  │              │  │
│  └───────────────┘  └─────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                      Data Layer                          │
│  ┌───────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │ LocalAdapter  │  │ TSAdapter   │  │ GMAdapter    │  │
│  │ (MongoDB)     │  │ (TuShare)   │  │ (GoldMiner)  │  │
│  └───────────────┘  └─────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    Storage/External API                  │
│              (MongoDB, TuShare API, GM API)              │
└─────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

#### 2.2.1 Service Layer

**MarketDataService**：提供统一的市场数据查询接口
- 自动选择合适的数据适配器（LocalAdapter 优先）
- 处理数据缓存和性能监控
- 统一的错误处理和日志记录

**DataSaverService**：负责数据的持久化
- 从远程数据源获取数据
- 数据清洗和验证
- 保存到本地数据库

#### 2.2.2 Data Layer

**Adapters（适配器模式）**：
- `LocalAdapter`：从 MongoDB 读取数据
- `TSAdapter`：从 TuShare 获取数据
- `GMAdapter`：从掘金量化获取数据

所有适配器实现统一的接口 `IDataAdapter`

## 3. 接口设计

### 3.1 核心接口

#### 3.1.1 MarketDataService

```python
class MarketDataService:
    """市场数据服务 - 统一的数据查询接口"""
    
    def get_trade_calendar(
        self,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, int, datetime.date, None] = None,
        end_date: Union[str, int, datetime.date, None] = None,
    ) -> pd.DataFrame:
        """获取交易日历"""
        pass
    
    def get_future_contracts(
        self,
        exchanges: Union[str, List[str], None] = None,
        symbols: Union[str, List[str], None] = None,
        spec_names: Union[str, List[str], None] = None,
        date: Union[str, int, datetime.date, None] = None,
    ) -> pd.DataFrame:
        """获取期货合约信息"""
        pass
    
    def get_future_daily(
        self,
        symbols: Union[str, List[str], None] = None,
        exchanges: Union[str, List[str], None] = None,
        start_date: Union[str, int, datetime.date, None] = None,
        end_date: Union[str, int, datetime.date, None] = None,
        date: Union[str, int, datetime.date, None] = None,
    ) -> pd.DataFrame:
        """获取期货日线数据"""
        pass
    
    def get_future_holdings(
        self,
        symbols: Union[str, List[str], None] = None,
        exchanges: Union[str, List[str], None] = None,
        spec_names: Union[str, List[str], None] = None,
        start_date: Union[str, int, datetime.date, None] = None,
        end_date: Union[str, int, datetime.date, None] = None,
        date: Union[str, int, datetime.date, None] = None,
    ) -> pd.DataFrame:
        """获取期货持仓数据"""
        pass
```

### 3.2 接口变化说明

#### 3.2.1 函数命名变化

**变化理由：简化命名，去除冗余的 "fetch_get_" 前缀**

| 旧接口 | 新接口 | 说明 |
|--------|--------|------|
| `fetch_get_trade_dates` | `get_trade_calendar` | 更语义化的名称 |
| `fetch_get_future_contracts` | `get_future_contracts` | 去除冗余前缀 |
| `fetch_get_future_daily` | `get_future_daily` | 去除冗余前缀 |
| `fetch_get_holdings` | `get_future_holdings` | 更明确的命名 |

#### 3.2.2 参数命名变化

**变化理由：统一参数命名规范**

| 旧参数名 | 新参数名 | 变化说明 |
|---------|----------|---------|
| `cursor_date` | `date` | 简化单日查询参数名 |
| `spec_name` | `spec_names` | 统一使用复数形式 |
| `engine` | 移除 | 自动选择数据源，不需要用户指定 |

#### 3.2.3 新增功能

1. **智能数据源选择**：自动优先从本地数据库查询，缺失时才请求远程API
2. **自动数据更新**：当本地数据过期时，自动从远程更新
3. **统一的缓存机制**：对频繁查询的数据进行缓存
4. **更好的错误处理**：提供更明确的错误信息

## 4. 数据流设计

### 4.1 查询流程

```
用户请求
   │
   ▼
MarketDataService.get_xxx()
   │
   ├─→ 参数验证和标准化
   │   (DateValidator, ExchangeValidator)
   │
   ├─→ 检查缓存
   │   (Cache Hit → 直接返回)
   │
   ├─→ LocalAdapter 查询
   │   (数据完整 → 返回)
   │
   ├─→ 检测数据缺失
   │
   └─→ RemoteAdapter 获取
       (TSAdapter/GMAdapter)
       │
       ├─→ 数据验证
       │
       ├─→ 保存到本地
       │
       └─→ 返回结果
```

### 4.2 保存流程

```
用户调用 save_xxx()
   │
   ▼
DataSaverService.save_xxx()
   │
   ├─→ 检查已有数据
   │
   ├─→ 确定需要更新的日期范围
   │
   ├─→ RemoteAdapter 批量获取
   │   (支持并发请求)
   │
   ├─→ 数据验证和清洗
   │
   ├─→ 数据完整性检查
   │
   └─→ 批量保存到 MongoDB
       (使用 bulk_write 优化性能)
```

## 5. 实施计划

### 5.1 第一阶段：基础重构（Week 1）

**目标：建立标准和基础工具**

1. ✅ 创建编码规范文档
2. ✅ 创建重构设计文档
3. 重构日期工具模块
   - 统一日期转换函数
   - 添加完整的类型注解
4. 重构交易所代码工具
   - 统一交易所代码映射
   - 添加验证函数
5. 创建数据适配器接口
   - 定义 IDataAdapter 接口
   - 实现基础适配器抽象类

### 5.2 第二阶段：适配器实现（Week 2）

**目标：实现统一的数据适配器**

1. 实现 LocalAdapter
   - 封装 MongoDB 查询逻辑
   - 优化查询性能
2. 重构 TSAdapter
   - 简化接口
   - 统一参数处理
3. 重构 GMAdapter
   - 简化接口
   - 统一参数处理
4. 单元测试
   - 测试各个适配器功能

### 5.3 第三阶段：服务层实现（Week 3）

**目标：实现统一的服务接口**

1. 实现 MarketDataService
   - 期货合约查询
   - 期货日线查询
   - 期货持仓查询
   - 交易日历查询
2. 实现 DataSaverService
   - 期货合约保存
   - 期货日线保存
   - 期货持仓保存
   - 交易日历保存
3. 集成测试
   - 端到端测试
   - 性能测试

### 5.4 第四阶段：迁移和优化（Week 4）

**目标：迁移现有代码并优化**

1. 更新 CLI 工具
   - 使用新的服务接口
2. 更新示例代码
   - 提供迁移指南
3. 性能优化
   - 查询优化
   - 缓存优化
4. 文档更新
   - API 文档
   - 使用指南

## 6. 向后兼容

### 6.1 兼容性策略

为了保证平滑过渡，我们将：

1. **保留旧接口**（标记为 deprecated）
   ```python
   @deprecated("使用 MarketDataService.get_trade_calendar 替代")
   def fetch_get_trade_dates(...):
       # 内部调用新接口
       service = MarketDataService()
       return service.get_trade_calendar(...)
   ```

2. **提供迁移工具**
   - 自动化脚本检测使用旧接口的代码
   - 提供迁移建议

3. **文档说明**
   - 详细的迁移指南
   - 新旧接口对照表

### 6.2 废弃时间表

- **v0.2.0**：引入新接口，旧接口标记为 deprecated
- **v0.3.0**：旧接口发出 DeprecationWarning
- **v0.4.0**：完全移除旧接口

## 7. 测试策略

### 7.1 单元测试

每个模块都需要完整的单元测试：

```python
# test_adapters.py
class TestLocalAdapter:
    def test_get_trade_calendar(self):
        """测试交易日历查询"""
        pass
    
    def test_get_future_contracts(self):
        """测试期货合约查询"""
        pass

# test_services.py
class TestMarketDataService:
    def test_smart_data_source_selection(self):
        """测试智能数据源选择"""
        pass
    
    def test_cache_mechanism(self):
        """测试缓存机制"""
        pass
```

### 7.2 集成测试

测试完整的数据流：

```python
def test_end_to_end_future_daily():
    """测试期货日线数据的完整流程"""
    # 1. 保存数据
    saver = DataSaverService()
    saver.save_future_daily(...)
    
    # 2. 查询数据
    service = MarketDataService()
    df = service.get_future_daily(...)
    
    # 3. 验证数据
    assert not df.empty
    assert set(df.columns) == expected_columns
```

### 7.3 性能测试

```python
def test_query_performance():
    """测试查询性能"""
    import time
    
    start = time.time()
    service.get_future_daily(start_date="2024-01-01", end_date="2024-12-31")
    duration = time.time() - start
    
    # 应该在 1 秒内完成
    assert duration < 1.0
```

## 8. 风险评估

### 8.1 潜在风险

1. **API 变化导致的兼容性问题**
   - 风险等级：中
   - 缓解措施：保留旧接口，提供迁移期

2. **性能下降**
   - 风险等级：低
   - 缓解措施：充分的性能测试，必要时回滚

3. **数据一致性问题**
   - 风险等级：中
   - 缓解措施：数据验证，完整性检查

### 8.2 回滚计划

如果重构出现严重问题：

1. 使用 Git 回滚到重构前的版本
2. 分析问题原因
3. 在新分支上修复问题
4. 重新测试后再次合并

## 9. 成功标准

重构成功的标准：

1. **功能完整性**
   - 所有现有功能正常工作
   - 期货数据查询和保存功能正常

2. **代码质量**
   - 代码覆盖率 > 80%
   - 所有单元测试通过
   - 所有集成测试通过

3. **性能指标**
   - 查询性能不低于重构前
   - 内存使用不超过重构前的 120%

4. **文档完整性**
   - API 文档完整
   - 迁移指南清晰
   - 编码规范明确

## 10. 后续优化方向

重构完成后，可以考虑以下优化：

1. **异步支持**：添加异步查询接口，提升并发性能
2. **分布式缓存**：使用 Redis 等分布式缓存
3. **数据流处理**：支持流式处理大量数据
4. **机器学习集成**：添加数据预处理和特征工程工具
5. **Web API**：提供 RESTful API 接口

## 11. 参考资料

- [编码规范文档](./coding_standards.md)
- [Python 类型注解](https://docs.python.org/3/library/typing.html)
- [设计模式：适配器模式](https://refactoring.guru/design-patterns/adapter)
- [MongoDB 性能优化](https://docs.mongodb.com/manual/administration/analyzing-mongodb-performance/)
