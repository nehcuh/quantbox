# 交易日期功能重构需求文档

## 1. 背景

当前系统中的交易日期相关功能分散在多个模块中，需要进行重构以提高代码的可维护性、可测试性和可扩展性。通过分析现有代码，发现以下问题：

1. 交易日期相关的功能分散在多个模块中，如 fetchers、validators、savers 等
2. 数据结构和接口不够统一，增加了维护成本
3. 缺乏统一的交易日期管理机制
4. 测试覆盖不够全面

## 2. 目标

1. 统一交易日期的数据结构和接口
2. 提供更完善的交易日期管理功能
3. 提高代码的可维护性和可测试性
4. 优化性能和资源利用

## 3. 功能需求

### 3.1 核心功能

1. 交易日期数据结构统一
   - 统一使用 `trade_date` 作为交易日期字段名
   - 日期格式统一为 `YYYY-MM-DD` 字符串格式
   - 必须包含 exchange、trade_date、pre_trade_date、datestamp 字段

2. 交易日期查询功能
   - 支持按交易所查询交易日期
   - 支持日期范围查询
   - 支持查询前/后 N 个交易日
   - 支持判断是否为交易日

3. 交易日期数据同步
   - 支持从不同数据源获取交易日期数据
   - 支持增量更新
   - 支持数据一致性校验

### 3.2 接口设计

```python
class TradeDateManager:
    def get_trade_dates(
        self,
        exchanges: Union[str, List[str]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """获取交易日期数据"""
        pass

    def get_prev_trade_date(
        self,
        exchange: str,
        reference_date: str,
        n: int = 1,
        include_reference: bool = False
    ) -> Dict[str, str]:
        """获取前N个交易日"""
        pass

    def get_next_trade_date(
        self,
        exchange: str,
        reference_date: str,
        n: int = 1,
        include_reference: bool = False
    ) -> Dict[str, str]:
        """获取后N个交易日"""
        pass

    def is_trade_date(
        self,
        exchange: str,
        date: str
    ) -> bool:
        """判断是否为交易日"""
        pass

    def sync_trade_dates(
        self,
        engine: str = "ts",
        start_date: Optional[str] = None
    ) -> None:
        """同步交易日期数据"""
        pass
```

## 4. 技术实现

### 4.1 代码结构

```
quantbox/
  ├── trade_dates/
  │   ├── __init__.py
  │   ├── manager.py      # 交易日期管理器
  │   ├── fetcher.py      # 数据获取接口
  │   ├── validator.py    # 数据验证
  │   └── storage.py      # 数据存储
  └── tests/
      └── trade_dates/    # 测试用例
```

### 4.2 数据结构

交易日期数据格式：
```python
class TradeDate(TypedDict):
    exchange: str         # 交易所代码
    trade_date: str       # 交易日期 YYYY-MM-DD
    pre_trade_date: str   # 前一交易日 YYYY-MM-DD
    datestamp: int        # 时间戳
```

### 4.3 性能优化

1. 数据缓存
   - 使用内存缓存常用交易日期数据
   - 实现 LRU 缓存机制

2. 数据库索引
   - 为 exchange 和 trade_date 字段建立复合索引
   - 优化查询性能

3. 批量操作
   - 支持批量查询和更新
   - 减少数据库访问次数

## 5. 测试计划

### 5.1 单元测试

1. 数据结构测试
   - 验证数据格式和字段类型
   - 测试日期格式转换

2. 接口功能测试
   - 测试所有公开接口
   - 测试边界条件和异常情况

3. 数据一致性测试
   - 测试不同数据源的数据一致性
   - 测试数据同步功能

### 5.2 集成测试

1. 功能集成测试
   - 测试与其他模块的集成
   - 测试数据流程完整性

2. 性能测试
   - 测试大数据量下的性能
   - 测试并发访问性能

## 6. 迁移计划

1. 代码迁移
   - 创建新的交易日期模块
   - 逐步迁移现有功能
   - 保持向后兼容

2. 数据迁移
   - 验证现有数据
   - 转换数据格式
   - 建立新的索引

## 7. 验收标准

1. 功能完整性
   - 所有功能需求实现完成
   - 接口文档完善

2. 代码质量
   - 测试覆盖率达到 90% 以上
   - 符合代码规范
   - 无严重 bug

3. 性能指标
   - 单次查询响应时间 < 100ms
   - 批量查询响应时间 < 1s
   - 内存占用合理

## 8. 时间计划

1. 设计阶段（1周）
   - 详细设计文档
   - 接口定义
   - 代码结构规划

2. 开发阶段（2周）
   - 核心功能实现
   - 单元测试编写
   - 文档编写

3. 测试阶段（1周）
   - 集成测试
   - 性能测试
   - Bug修复

4. 上线阶段（1周）
   - 代码审查
   - 数据迁移
   - 灰度发布