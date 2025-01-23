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
   - 日期格式统一为整数格式，如 20240123
   - 必须包含 exchange、trade_date、pretrade_date、datestamp 字段

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
from typing import Union, Optional, List, Dict
from datetime import datetime, date
import pandas as pd

DateType = Union[str, int, date, datetime, pd.Timestamp]

class TradeDateManager:
    def get_trade_dates(
        self,
        exchanges: Union[str, List[str]],
        start_date: Optional[DateType] = None,
        end_date: Optional[DateType] = None
    ) -> pd.DataFrame:
        """获取交易日期数据
        
        Args:
            exchanges: 单个交易所代码或交易所代码列表
            start_date: 开始日期，支持以下格式：
                - str: '2024-01-23' 或 '20240123'
                - int: 20240123
                - date: datetime.date(2024, 1, 23)
                - datetime: datetime.datetime(2024, 1, 23)
                - pd.Timestamp: pd.Timestamp('2024-01-23')
            end_date: 结束日期，格式同 start_date
        """
        pass

    def get_prev_trade_date(
        self,
        exchange: str,
        reference_date: DateType,
        n: int = 1,
        include_reference: bool = False
    ) -> Dict[str, int]:
        """获取前N个交易日
        
        Args:
            exchange: 交易所代码
            reference_date: 参考日期，支持多种格式
            n: 向前获取的天数
            include_reference: 是否包含参考日期
        """
        pass

    def get_next_trade_date(
        self,
        exchange: str,
        reference_date: DateType,
        n: int = 1,
        include_reference: bool = False
    ) -> Dict[str, int]:
        """获取后N个交易日
        
        Args:
            exchange: 交易所代码
            reference_date: 参考日期，支持多种格式
            n: 向后获取的天数
            include_reference: 是否包含参考日期
        """
        pass

    def is_trade_date(
        self,
        exchange: str,
        date: DateType
    ) -> bool:
        """判断是否为交易日
        
        Args:
            exchange: 交易所代码
            date: 日期，支持多种格式
        """
        pass

    def sync_trade_dates(
        self,
        engine: str = "ts",
        start_date: Optional[DateType] = None
    ) -> None:
        """同步交易日期数据
        
        Args:
            engine: 数据源引擎
            start_date: 开始日期，支持多种格式
        """
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

### 4.2 数据库设计

```sql
CREATE TABLE trade_calendar (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    exchange VARCHAR(10) NOT NULL COMMENT '交易所代码',
    trade_date INT NOT NULL COMMENT '交易日期，格式：20240123',
    pretrade_date INT NOT NULL COMMENT '前一交易日，格式：20240122',
    datestamp BIGINT NOT NULL COMMENT '纳秒级时间戳',
    is_open BOOLEAN NOT NULL COMMENT '是否开市',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_exchange_date (exchange, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易日历表';
```

### 4.3 示例数据

```python
# 交易日期数据示例
trade_dates = {
    'SSE': [
        {
            'trade_date': 20240123,
            'pretrade_date': 20240122,
            'datestamp': 1705968000000000000,  # 纳秒级时间戳
            'is_open': True
        },
        {
            'trade_date': 20240124,
            'pretrade_date': 20240123,
            'datestamp': 1706054400000000000,  # 纳秒级时间戳
            'is_open': True
        }
    ]
}

# 交易日历缓存示例
trade_calendar_cache = {
    'SSE': {
        20240123: {
            'pretrade_date': 20240122,
            'next_trade_date': 20240124,
            'is_open': True
        }
    }
}
```

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
   - Bug修复

4. 上线阶段（1周）
   - 代码审查
   - 数据迁移
   - 灰度发布