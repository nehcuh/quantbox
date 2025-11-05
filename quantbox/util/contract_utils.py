"""
Contract utilities

该模块提供期货和股票合约代码的标准化、解析、验证和格式转换功能。
支持多种数据源格式（掘金、Tushare等），统一内部表示。

主要优化：
    - 模块化设计，职责分离
    - 统一的编码约定管理
    - 简化的API接口
    - 改进的错误处理
    - 更好的性能和缓存

标准格式说明：
    内部标准格式：EXCHANGE.symbol（例如：SHFE.rb2501, SHSE.600000）
    - 交易所使用标准化代码（SHFE, DCE, CZCE, CFFEX, INE, SHSE, SZSE等）
    - 期货品种代码按交易所规范（上期所等小写，郑商所、中金所大写）
    - 期货合约月份统一4位数字（2501表示2025年1月）

数据源编码约定：
    - 上期所、大商所、上期能源、广期所：期货合约小写（rb2501）
    - 中金所：期货合约大写（IF2401）
    - 郑商所：期货合约大写，年月可能3位或4位（SR2501或SR501）

外部格式：
    - 掘金/GoldMiner: SHFE.rb2501, CZCE.SR2501
    - Tushare: RB2501.SHF, SR2501.ZCE（所有品种代码大写）
    - vnpy: RB2501.SHFE, SR2501.CZCE（所有品种代码大写，交易所使用标准代码）
"""

from typing import Optional, List, Dict, Tuple, Union, Any
from enum import Enum
import re
from functools import lru_cache
import logging
from datetime import datetime

from quantbox.util.exchange_utils import (
    ExchangeType,
    normalize_exchange,
    denormalize_exchange,
    is_futures_exchange,
    is_stock_exchange,
    STANDARD_EXCHANGES,
    STOCK_EXCHANGES,
    FUTURES_EXCHANGES,
)

# 导入配置系统
try:
    from quantbox.config.config_loader import (
        get_config_loader,
        get_exchange_info,
        get_instrument_info,
        get_data_source_mapping,
        get_trading_hours,
        get_fee_config,
        get_margin_config,
    )
    CONFIG_AVAILABLE = True
except ImportError:
    logging.warning("配置系统不可用，将使用硬编码配置")
    CONFIG_AVAILABLE = False


class ContractFormat(str, Enum):
    """合约代码格式枚举"""
    STANDARD = "standard"  # 标准格式: EXCHANGE.symbol
    GOLDMINER = "goldminer"  # 掘金格式: EXCHANGE.symbol
    TUSHARE = "tushare"  # Tushare格式: SYMBOL.EXCHANGE
    VNPy = "vnpy"  # vnpy格式: symbol.EXCHANGE
    PLAIN = "plain"  # 纯代码: symbol (不含交易所)


class AssetType(str, Enum):
    """资产类型枚举"""
    STOCK = "stock"  # 股票
    FUTURES = "futures"  # 期货
    INDEX = "index"  # 指数
    FUND = "fund"  # 基金
    UNKNOWN = "unknown"  # 未知


class ContractType(str, Enum):
    """合约类型枚举"""
    REGULAR = "regular"  # 普通合约（如 rb2501）
    MAIN = "main"  # 主力合约（如 rb888）
    CONTINUOUS = "continuous"  # 连续合约（如 rb000）
    WEIGHTED = "weighted"  # 加权指数（如 rb99）
    CURRENT_MONTH = "current_month"  # 当月合约（如 rb00）
    NEXT_MONTH = "next_month"  # 下月合约（如 rb01）
    NEXT_QUARTER = "next_quarter"  # 下季合约（如 rb02）
    NEXT_NEXT_QUARTER = "next_next_quarter"  # 隔季合约（如 rb03）
    UNKNOWN = "unknown"  # 未知类型


class EncodingConvention:
    """编码约定管理器 - 统一处理不同交易所的编码规则"""

    # 交易所大小写规则（基于实际交易所规范）
    CASE_RULES = {
        'lowercase': {'SHFE', 'DCE', 'INE', 'GFEX'},  # 品种代码小写
        'uppercase': {'CZCE', 'CFFEX'},  # 品种代码大写
    }

    # 特殊合约类型标识
    SPECIAL_CONTRACTS = {
        'main': {'888', '000'},
        'weighted': {'99'},
        'current_month': {'00'},
        'next_month': {'01'},
        'next_quarter': {'02'},
        'next_next_quarter': {'03'},
    }

    @classmethod
    def get_case_rule(cls, exchange: str) -> str:
        """获取交易所的大小写规则"""
        for rule, exchanges in cls.CASE_RULES.items():
            if exchange in exchanges:
                return rule
        return 'lowercase'  # 默认小写

    @classmethod
    def apply_case_rule(cls, symbol: str, exchange: str) -> str:
        """应用大小写规则"""
        rule = cls.get_case_rule(exchange)
        if rule == 'uppercase':
            return symbol.upper()
        return symbol.lower()

    @classmethod
    def detect_contract_type(cls, date_part: str) -> ContractType:
        """检测合约类型"""
        date_part_lower = date_part.lower()

        for contract_type, identifiers in cls.SPECIAL_CONTRACTS.items():
            if date_part_lower in identifiers:
                return ContractType(contract_type)

        # 普通合约判断
        if len(date_part) == 4 or (len(date_part) == 3 and date_part.isdigit()):
            return ContractType.REGULAR

        return ContractType.UNKNOWN

    @classmethod
    def normalize_czce_year(cls, year_part: str) -> int:
        """智能处理郑商所3位年月格式的年份推断"""
        if len(year_part) != 3:
            raise ValueError(f"郑商所年月格式错误: {year_part}")

        year_last_digit = int(year_part[0])
        current_year = datetime.now().year
        current_decade = current_year // 10 * 10

        # 智能推断：基于当前年份判断是哪个十年
        candidate_year = current_decade + year_last_digit

        # 如果推断的年份比当前年份晚超过8年，则认为是上一个十年
        if candidate_year - current_year > 8:
            candidate_year -= 10

        return candidate_year


class ContractInfo:
    """合约信息类，封装解析后的合约信息"""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        asset_type: AssetType = AssetType.UNKNOWN,
        underlying: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        contract_type: ContractType = ContractType.UNKNOWN,
    ):
        self.exchange = exchange
        self.symbol = symbol
        self.asset_type = asset_type
        self.underlying = underlying
        self.year = year
        self.month = month
        self.contract_type = contract_type

    def __repr__(self) -> str:
        return (
            f"ContractInfo(exchange={self.exchange}, symbol={self.symbol}, "
            f"asset_type={self.asset_type.value}, underlying={self.underlying}, "
            f"year={self.year}, month={self.month}, contract_type={self.contract_type.value})"
        )

    def to_standard(self) -> str:
        """转换为标准格式代码"""
        return f"{self.exchange}.{self.symbol}"

    # 便利方法
    def is_futures(self) -> bool:
        return self.asset_type == AssetType.FUTURES

    def is_stock(self) -> bool:
        return self.asset_type == AssetType.STOCK

    def is_regular_contract(self) -> bool:
        return self.contract_type == ContractType.REGULAR

    def is_main_contract(self) -> bool:
        return self.contract_type == ContractType.MAIN

    def is_continuous_contract(self) -> bool:
        return self.contract_type == ContractType.CONTINUOUS

    def is_weighted_contract(self) -> bool:
        return self.contract_type == ContractType.WEIGHTED

    def is_current_month_contract(self) -> bool:
        return self.contract_type == ContractType.CURRENT_MONTH

    def is_next_month_contract(self) -> bool:
        return self.contract_type == ContractType.NEXT_MONTH

    def is_next_quarter_contract(self) -> bool:
        return self.contract_type == ContractType.NEXT_QUARTER

    def is_next_next_quarter_contract(self) -> bool:
        return self.contract_type == ContractType.NEXT_NEXT_QUARTER


# 正则表达式模式（优化编译位置）
_FUTURES_PATTERN = re.compile(r"^([A-Za-z]+)(\d+)$")
_STOCK_PATTERN = re.compile(r"^\d{6}$")

logger = logging.getLogger(__name__)


# ============================================================================
# 核心解析函数模块化
# ============================================================================

def _parse_exchange_and_symbol(contract: str, default_exchange: Optional[str] = None) -> Tuple[str, str]:
    """解析交易所和合约代码部分"""
    if "." in contract:
        parts = contract.split(".")
        if len(parts) != 2:
            raise ValueError(f"合约代码格式无效: {contract}")

        part1, part2 = parts

        # 尝试识别交易所部分
        for candidate_exchange, candidate_symbol in [(part1, part2), (part2, part1)]:
            if candidate_exchange.isalpha() and len(candidate_exchange) <= 6:
                try:
                    exchange = normalize_exchange(candidate_exchange)
                    return exchange, candidate_symbol
                except ValueError:
                    continue

        raise ValueError(f"无法识别交易所: {contract}")
    else:
        # 纯合约代码，需要默认交易所
        if not default_exchange:
            raise ValueError(f"合约代码 '{contract}' 未包含交易所信息，需要提供 default_exchange")
        exchange = normalize_exchange(default_exchange)
        return exchange, contract


def _parse_futures_contract(symbol: str, exchange: str) -> ContractInfo:
    """解析期货合约"""
    match = _FUTURES_PATTERN.match(symbol)
    if not match:
        # 尝试从配置系统验证特殊合约
        return _parse_special_futures_from_config(symbol, exchange)

    underlying = match.group(1)
    date_part = match.group(2)

    # 检测合约类型
    contract_type = EncodingConvention.detect_contract_type(date_part)

    # 特殊合约类型处理
    if contract_type != ContractType.REGULAR:
        symbol_formatted = EncodingConvention.apply_case_rule(underlying, exchange) + date_part.upper()
        return ContractInfo(
            exchange=exchange,
            symbol=symbol_formatted,
            asset_type=AssetType.FUTURES,
            underlying=EncodingConvention.apply_case_rule(underlying, exchange),
            year=None,
            month=None,
            contract_type=contract_type,
        )

    # 普通合约处理
    year, month, symbol_formatted = _parse_contract_year_month(underlying, date_part, exchange)

    return ContractInfo(
        exchange=exchange,
        symbol=symbol_formatted,
        asset_type=AssetType.FUTURES,
        underlying=EncodingConvention.apply_case_rule(underlying, exchange),
        year=year,
        month=month,
        contract_type=ContractType.REGULAR,
    )


def _parse_contract_year_month(underlying: str, date_part: str, exchange: str) -> Tuple[int, int, str]:
    """解析合约年月并格式化"""
    if len(date_part) == 4:
        # 标准年月格式
        year = 2000 + int(date_part[:2])
        month = int(date_part[2:])
    elif len(date_part) == 3 and exchange == "CZCE":
        # 郑商所3位年月格式
        year = EncodingConvention.normalize_czce_year(date_part)
        month = int(date_part[1:])
        # 转换为4位标准格式
        date_part = f"{year % 100:02d}{month:02d}"
    else:
        raise ValueError(f"期货合约日期格式无效: {date_part}")

    # 应用交易所大小写规则
    symbol_formatted = EncodingConvention.apply_case_rule(underlying, exchange) + date_part
    if exchange in ['CZCE', 'CFFEX']:
        symbol_formatted = symbol_formatted.upper()

    return year, month, symbol_formatted


def _parse_special_futures_from_config(symbol: str, exchange: str) -> ContractInfo:
    """从配置系统解析特殊期货合约"""
    if not CONFIG_AVAILABLE:
        raise ValueError(f"期货合约代码格式无效: {symbol}")

    try:
        config = get_config_loader()
        instruments = config.list_instruments(exchange)

        # 检查是否为已知品种
        if symbol in instruments:
            return ContractInfo(
                exchange=exchange,
                symbol=symbol,
                asset_type=AssetType.FUTURES,
                underlying=symbol,
                year=None,
                month=None,
                contract_type=ContractType.MAIN,
            )
        elif len(symbol) > 1 and symbol[:-1] in instruments:
            # Tushare 连续合约
            return ContractInfo(
                exchange=exchange,
                symbol=symbol[:-1],
                asset_type=AssetType.FUTURES,
                underlying=symbol[:-1],
                year=None,
                month=None,
                contract_type=ContractType.CONTINUOUS,
            )
        else:
            raise ValueError(f"期货合约代码格式无效: {symbol}")
    except Exception as e:
        raise ValueError(f"解析特殊期货合约失败: {e}")


def _parse_stock_contract(symbol: str, exchange: str) -> ContractInfo:
    """解析股票合约"""
    if not _STOCK_PATTERN.match(symbol):
        raise ValueError(f"股票代码格式无效: {symbol}")

    asset_type = _detect_stock_asset_type(symbol, exchange)

    return ContractInfo(
        exchange=exchange,
        symbol=symbol,
        asset_type=asset_type,
        contract_type=ContractType.REGULAR,
    )


def _detect_stock_asset_type(symbol: str, exchange: str) -> AssetType:
    """检测股票资产类型（股票/指数）"""
    if CONFIG_AVAILABLE:
        return _detect_stock_with_config(symbol, exchange)
    else:
        return _detect_stock_hardcoded(symbol, exchange)


def _detect_stock_with_config(symbol: str, exchange: str) -> AssetType:
    """使用配置系统检测股票类型"""
    try:
        config = get_config_loader()
        rules = config.load_config('exchanges').get('stock_index_rules', {})

        # 检查指数规则
        if _is_index_by_config(symbol, exchange, rules):
            return AssetType.INDEX

        # 检查股票规则
        if _is_stock_by_config(symbol, exchange, rules):
            return AssetType.STOCK

        return AssetType.UNKNOWN
    except Exception as e:
        # 配置系统失败时回退到硬编码函数
        return _detect_stock_hardcoded(symbol, exchange)


def _detect_stock_hardcoded(symbol: str, exchange: str) -> AssetType:
    """硬编码的股票类型检测（后备方案）"""
    if exchange == "SHSE":
        code_prefix = int(symbol[:3])
        # 主板：600-601，科创板：688
        if 600 <= code_prefix <= 601 or code_prefix == 688:
            return AssetType.STOCK
        # 指数：000开头
        elif symbol.startswith('000'):
            return AssetType.INDEX
    elif exchange == "SZSE":
        code_prefix = int(symbol[:3])
        # 主板：000-002，中小板：003-004，创业板：300
        if 0 <= code_prefix <= 4 or code_prefix == 300:
            return AssetType.STOCK
        # 指数：399开头
        elif code_prefix == 399:
            return AssetType.INDEX

    return AssetType.UNKNOWN


def _is_index_by_config(symbol: str, exchange: str, rules: Dict) -> bool:
    """根据配置判断是否为指数"""
    if exchange == "SHSE":
        indices = rules.get('shse_indices', {})
        if symbol in indices.get('上证指数', []):
            return True
        if symbol == indices.get('沪深300'):
            return True
        return symbol.startswith('000')
    elif exchange == "SZSE":
        indices = rules.get('szse_indices', {})
        return symbol.startswith('399')
    return False


def _is_stock_by_config(symbol: str, exchange: str, rules: Dict) -> bool:
    """根据配置判断是否为股票"""
    code_num = int(symbol)  # 使用完整的6位代码

    if exchange == "SHSE":
        stocks = rules.get('shse_stocks', {})
        # 检查主板和科创板范围
        for market in ['主板', '科创板']:
            range_str = stocks.get(market, '')
            if range_str:
                try:
                    start, end = range_str.split('-')
                    if int(start) <= code_num <= int(end):
                        return True
                except:
                    pass
    elif exchange == "SZSE":
        stocks = rules.get('szse_stocks', {})
        # 检查各板块范围
        for market in ['主板', '中小板', '创业板']:
            range_str = stocks.get(market, '')
            if range_str:
                try:
                    start, end = range_str.split('-')
                    if int(start) <= code_num <= int(end):
                        return True
                except:
                    pass

    return False


# ============================================================================
# 主要API函数
# ============================================================================

def parse_contract(
    contract: str,
    default_exchange: Optional[str] = None,
    asset_type: Optional[AssetType] = None,
) -> ContractInfo:
    """
    解析合约代码，提取交易所、品种、年月等信息

    Args:
        contract: 合约代码
        default_exchange: 默认交易所
        asset_type: 资产类型提示

    Returns:
        ContractInfo: 解析后的合约信息

    Raises:
        ValueError: 合约代码格式无效
    """
    if not contract or not contract.strip():
        raise ValueError("合约代码不能为空")

    contract = contract.strip()

    # 解析交易所和合约代码
    exchange, symbol = _parse_exchange_and_symbol(contract, default_exchange)

    # 检测资产类型
    detected_asset_type = asset_type or _detect_asset_type(symbol, exchange)

    if detected_asset_type == AssetType.FUTURES:
        return _parse_futures_contract(symbol, exchange)
    elif detected_asset_type == AssetType.STOCK:
        return _parse_stock_contract(symbol, exchange)
    else:
        raise ValueError(f"不支持的资产类型: {detected_asset_type}")


def _detect_asset_type(symbol: str, exchange: str) -> AssetType:
    """检测资产类型"""
    if is_futures_exchange(exchange):
        return AssetType.FUTURES
    elif is_stock_exchange(exchange):
        return _detect_stock_asset_type(symbol, exchange)
    else:
        return AssetType.UNKNOWN


@lru_cache(maxsize=32)
def _get_data_source_exchange_mapping(data_source: str) -> Dict[str, str]:
    """
    获取数据源交易所映射

    Args:
        data_source: 数据源名称

    Returns:
        Dict[str, str]: 交易所代码映射
    """
    # 硬编码的映射关系
    mappings = {
        "goldminer": {
            "SHFE": "SHFE",
            "DCE": "DCE",
            "CZCE": "CZCE",
            "CFFEX": "CFFEX",
            "INE": "INE",
            "GFEX": "GFEX",
            "SHSE": "SHSE",
            "SZSE": "SZSE"
        },
        "tushare": {
            "SHFE": "SHF",
            "DCE": "DCE",
            "CZCE": "ZCE",
            "CFFEX": "CFFEX",
            "INE": "INE",
            "GFEX": "GFEX",
            "SHSE": "SH",  # 上交所
            "SZSE": "SZ",  # 深交所
        },
        "vnpy": {
            "SHFE": "SHFE",
            "DCE": "DCE",
            "CZCE": "CZCE",
            "CFFEX": "CFFEX",
            "INE": "INE",
            "GFEX": "GFEX",
            "SSE": "SSE",
            "SZSE": "SZSE",
            "BSE": "BSE"
        }
    }
    return mappings.get(data_source, {})


def format_contract(
    contract: str,
    target_format: Union[ContractFormat, str],
    default_exchange: Optional[str] = None,
    asset_type: Optional[AssetType] = None,
) -> str:
    """
    将合约代码转换为指定格式

    Args:
        contract: 输入合约代码
        target_format: 目标格式
        default_exchange: 默认交易所
        asset_type: 资产类型提示

    Returns:
        str: 转换后的合约代码

    Raises:
        ValueError: 合约代码无效或格式不支持
    """
    # 解析合约代码
    info = parse_contract(contract, default_exchange, asset_type)

    # 转换为枚举
    if isinstance(target_format, str):
        try:
            target_format = ContractFormat(target_format.lower())
        except ValueError:
            raise ValueError(f"不支持的格式: {target_format}")

    # 根据目标格式生成代码
    if target_format == ContractFormat.STANDARD:
        return f"{info.exchange}.{info.symbol}"

    elif target_format == ContractFormat.GOLDMINER:
        mapping = _get_data_source_exchange_mapping("goldminer")
        exchange_gm = mapping.get(info.exchange, info.exchange)

        if info.exchange in ["CFFEX", "CZCE"]:
            # 中金所和郑商所使用大写
            if info.exchange == "CZCE" and info.asset_type == AssetType.FUTURES:
                # 郑商所期货合约使用3位年月格式
                if len(info.symbol) >= 4 and info.symbol[-4:].isdigit():
                    symbol = info.symbol[:-4] + info.symbol[-3:]
                else:
                    symbol = info.symbol
                return f"{exchange_gm}.{symbol.upper()}"
            else:
                return f"{exchange_gm}.{info.symbol.upper()}"
        else:
            # 上期所、大商所、上期能源、广期所使用小写
            return f"{exchange_gm}.{info.symbol.lower()}"

    elif target_format == ContractFormat.TUSHARE:
        mapping = _get_data_source_exchange_mapping("tushare")
        exchange_ts = mapping.get(info.exchange, info.exchange)

        # Tushare 所有合约品种都使用大写
        return f"{info.symbol.upper()}.{exchange_ts}"

    elif target_format == ContractFormat.VNPy:
        mapping = _get_data_source_exchange_mapping("vnpy")
        exchange_vnpy = mapping.get(info.exchange, info.exchange)

        # vnpy也使用大写品种代码
        return f"{info.symbol.upper()}.{exchange_vnpy}"

    elif target_format == ContractFormat.PLAIN:
        return info.symbol

    else:
        raise ValueError(f"不支持的目标格式: {target_format}")


def format_contracts(
    contracts: Union[str, List[str]],
    target_format: Union[ContractFormat, str],
    default_exchange: Optional[str] = None,
    asset_type: Optional[AssetType] = None,
) -> List[str]:
    """
    批量转换合约代码格式

    Args:
        contracts: 合约代码列表
        target_format: 目标格式
        default_exchange: 默认交易所
        asset_type: 资产类型提示

    Returns:
        List[str]: 转换后的合约代码列表
    """
    if isinstance(contracts, str):
        contracts = [c.strip() for c in contracts.split(",") if c.strip()]

    results = []
    for contract in contracts:
        try:
            formatted = format_contract(contract, target_format, default_exchange, asset_type)
            results.append(formatted)
        except ValueError as e:
            raise ValueError(f"转换合约代码 '{contract}' 失败: {str(e)}")

    return results


def validate_contract(
    contract: str,
    exchange: Optional[str] = None,
    asset_type: Optional[AssetType] = None,
) -> bool:
    """
    验证合约代码格式是否有效

    Args:
        contract: 合约代码
        exchange: 期望的交易所
        asset_type: 期望的资产类型

    Returns:
        bool: 是否有效
    """
    try:
        info = parse_contract(contract)

        if exchange is not None:
            expected_exchange = normalize_exchange(exchange)
            if info.exchange != expected_exchange:
                return False

        if asset_type is not None and info.asset_type != asset_type:
            return False

        return True
    except (ValueError, Exception):
        return False


def validate_contracts(
    contracts: Union[str, List[str]],
    exchange: Optional[str] = None,
    asset_type: Optional[AssetType] = None,
    skip_invalid: bool = False,
) -> Union[bool, List[bool]]:
    """
    批量验证合约代码

    Args:
        contracts: 合约代码列表
        exchange: 期望的交易所
        asset_type: 期望的资产类型
        skip_invalid: 是否跳过无效代码

    Returns:
        Union[bool, List[bool]]: 验证结果
    """
    if isinstance(contracts, str):
        contracts = [c.strip() for c in contracts.split(",") if c.strip()]

    results = [validate_contract(c, exchange, asset_type) for c in contracts]

    if skip_invalid:
        return any(results)
    else:
        return results


def split_contract(contract: str) -> Tuple[str, str]:
    """
    分离合约代码的交易所和代码部分

    Args:
        contract: 合约代码

    Returns:
        Tuple[str, str]: (交易所, 代码)
    """
    info = parse_contract(contract)
    return (info.exchange, info.symbol)


def get_underlying(contract: str) -> Optional[str]:
    """
    获取期货合约的标的品种代码

    Args:
        contract: 期货合约代码

    Returns:
        Optional[str]: 品种代码
    """
    try:
        info = parse_contract(contract)
        return info.underlying
    except (ValueError, Exception):
        return None


def get_contract_month(contract: str) -> Optional[Tuple[int, int]]:
    """
    获取期货合约的年月

    Args:
        contract: 期货合约代码

    Returns:
        Optional[Tuple[int, int]]: (年份, 月份)
    """
    try:
        info = parse_contract(contract)
        if info.year is not None and info.month is not None:
            return (info.year, info.month)
        return None
    except (ValueError, Exception):
        return None


def is_main_contract(contract: str) -> bool:
    """
    判断是否为主力合约代码

    Args:
        contract: 合约代码

    Returns:
        bool: 是否为主力合约
    """
    try:
        info = parse_contract(contract)
        if info.asset_type != AssetType.FUTURES:
            return False
        return info.is_main_contract()
    except (ValueError, Exception):
        return False


def normalize_contract(
    contract: str,
    default_exchange: Optional[str] = None,
) -> str:
    """
    标准化合约代码为内部统一格式

    Args:
        contract: 输入合约代码
        default_exchange: 默认交易所

    Returns:
        str: 标准化后的合约代码
    """
    return format_contract(contract, ContractFormat.STANDARD, default_exchange)


def normalize_contracts(
    contracts: Union[str, List[str]],
    default_exchange: Optional[str] = None,
) -> List[str]:
    """
    批量标准化合约代码

    Args:
        contracts: 合约代码列表
        default_exchange: 默认交易所

    Returns:
        List[str]: 标准化后的合约代码列表
    """
    return format_contracts(contracts, ContractFormat.STANDARD, default_exchange)
