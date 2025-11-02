# Quantbox API 参考

本参考覆盖公开 API（Python 与 CLI）以及数据模型约定。示例以 pandas DataFrame 为返回类型。

- 目标读者：开发者与数据工程师
- 返回类型：默认 pandas.DataFrame；保存接口返回 SaveResult
- 日期约定：支持 YYYY-MM-DD 字符串或 int(YYYYMMDD)，内部统一为 int
- 交易所代码：统一为 SHFE, DCE, CZCE, INE, SHSE, SZSE
- 合约代码：统一为如 `RB2405.SHF`（品种+到期月.交易所）

---

## 1. Python API

### 1.1 Services

#### MarketDataService

构造函数
```python
MarketDataService(
    local_adapter: BaseDataAdapter | None = None,
    remote_adapter: BaseDataAdapter | None = None,
    prefer_local: bool = True,
)
```

- prefer_local：是否本地优先；`use_local` 参数可在方法级别覆盖

方法

```python
get_trade_calendar(
    exchanges: list[str] | None = None,
    start_date: str | int | None = None,
    end_date: str | int | None = None,
    use_local: bool | None = None,
) -> pd.DataFrame
```
- 列：`cal_date(int), exchange(str), is_open(int), pretrade_date(int)`

```python
get_future_contracts(
    exchanges: list[str] | None = None,
    symbols: list[str] | None = None,    # 品种根，如 ["RB", "HC"]
    active_only: bool | None = None,     # 仅活跃/未到期
    include_delisted: bool = False,
    use_local: bool | None = None,
) -> pd.DataFrame
```
- 列：`ts_code, symbol, exchange, name, list_date, delist_date, is_main?`

```python
get_future_daily(
    contracts: list[str] | None = None,  # 完整 ts_code，如 ["RB2405.SHF"]
    symbols: list[str] | None = None,    # 或品种根，如 ["RB"]
    exchanges: list[str] | None = None,
    is_main: bool | None = None,         # 主力合约
    start_date: str | int | None = None,
    end_date: str | int | None = None,
    fields: list[str] | None = None,     # 选列
    adjust: str | None = None,           # 前复权/不复权等（如有）
    use_local: bool | None = None,
    limit: int | None = None,
) -> pd.DataFrame
```
- 典型列：`trade_date, ts_code, open, high, low, close, preclose, change, pct_chg, vol, amount, oi?`

```python
get_future_holdings(
    contracts: list[str] | None = None,
    symbols: list[str] | None = None,
    start_date: str | int | None = None,
    end_date: str | int | None = None,
    top_n: int | None = 20,
    brokers: list[str] | None = None,
    use_local: bool | None = None,
) -> pd.DataFrame
```
- 典型列：`trade_date, ts_code, broker, rank, vol, vol_chg, long_hld, short_hld`

示例
```python
from quantbox.services import MarketDataService
svc = MarketDataService()
cal = svc.get_trade_calendar(["SHFE"], "2024-01-01", "2024-12-31")
daily = svc.get_future_daily(contracts=["RB2405.SHF"], start_date=20240101, end_date=20240131)
```

#### DataSaverService

构造函数
```python
DataSaverService(
    local_adapter: BaseDataAdapter | None = None,
    remote_adapter: BaseDataAdapter | None = None,
    batch_size: int = 1000,
)
```

方法
```python
save_trade_calendar(
    exchanges: list[str],
    start_date: str | int,
    end_date: str | int,
    source: str | None = None,
) -> SaveResult
```

```python
save_future_contracts(
    exchanges: list[str],
    source: str | None = None,
) -> SaveResult
```

```python
save_future_daily(
    contracts: list[str] | None = None,
    symbols: list[str] | None = None,
    exchanges: list[str] | None = None,
    is_main: bool | None = None,
    start_date: str | int | None = None,
    end_date: str | int | None = None,
    adjust: str | None = None,
) -> SaveResult
```

返回类型
```python
@dataclass
class SaveResult:
    success: bool
    inserted_count: int
    modified_count: int
    errors: list[str] = field(default_factory=list)
```

示例
```python
from quantbox.services import DataSaverService
saver = DataSaverService()
res = saver.save_future_daily(contracts=["RB2405.SHF"], start_date=20240101, end_date=20241231)
assert res.success
```

---

### 1.2 适配器接口

```python
class BaseDataAdapter(ABC):
    def get_trade_calendar(...): ...
    def get_future_contracts(...): ...
    def get_future_daily(...): ...
    def get_future_holdings(...): ...
```
- 适配器需返回 DataFrame，并确保列名符合上文约定
- 推荐实现 `check_availability()` 以供服务层探测

---

## 2. CLI

可通过 `quantbox` 命令行调用。

查询
```bash
quantbox query calendar   --exchange SHFE --start 2024-01-01 --end 2024-01-31
quantbox query contracts  --exchange SHFE --symbol RB
quantbox query daily      --contract RB2405.SHF --start 2024-01-01 --end 2024-01-31
quantbox query holdings   --contract RB2405.SHF --date 2024-01-15
```

保存
```bash
quantbox save calendar   --exchange SHFE DCE CZCE INE --start 2020-01-01 --end 2024-12-31
quantbox save contracts  --exchange SHFE DCE CZCE INE
quantbox save daily      --contract RB2405.SHF --start 2024-01-01 --end 2024-12-31
```

GUI
```bash
quantbox gui
```

---

## 3. 数据模型与列定义

### 3.1 trade_calendar
- cal_date int YYYYMMDD
- exchange str one of [SHFE, DCE, CZCE, INE, SHSE, SZSE]
- is_open int {0,1}
- pretrade_date int YYYYMMDD

### 3.2 future_contracts
- ts_code str 如 RB2405.SHF
- symbol str 如 RB
- exchange str
- name str
- list_date int YYYYMMDD
- delist_date int YYYYMMDD | 0
- is_main int 可选

### 3.3 future_daily
- trade_date int
- ts_code str
- open, high, low, close float
- preclose, change, pct_chg float 可选
- vol float/int
- amount float 可选
- oi int 可选

### 3.4 future_holdings
- trade_date int
- ts_code str
- broker str
- rank int
- vol int
- vol_chg int
- long_hld int
- short_hld int

---

## 4. 错误与异常

- ValidationError：参数不合法（日期、交易所、合约）
- DataSourceUnavailableError：本地或远程数据源不可用
- SaveError：保存失败（索引/连接/批处理异常）

建议捕获
```python
try:
    svc.get_future_daily(symbols=["RB"], is_main=True)
except (ValidationError, DataSourceUnavailableError) as e:
    ...
```

---

## 5. 配置

优先级：方法参数 > Service 构造参数 > 环境变量 > 配置文件

- 环境变量：`TUSHARE_TOKEN`, `MONGO_HOST`, `MONGO_PORT`, `MONGO_DB`, `MONGO_USER`, `MONGO_PASSWORD`
- 配置文件：`~/.quantbox/config.yml` 或 `quantbox/config/config.yml`

---

## 6. 版本兼容

- 旧 API 将在小版本内保持软兼容（触发 DeprecationWarning）
- 破坏性变更详见 MIGRATION_GUIDE.md
