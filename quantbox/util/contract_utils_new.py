"""
合约代码标准化工具模块

该模块提供期货和股票合约代码的标准化、解析、验证和格式转换功能。
支持多种数据源格式（掘金、Tushare等），统一内部表示。

主要功能：
    - 合约代码解析（提取交易所、品种代码、年月等）
    - 格式标准化和转换
    - 合约代码验证
    - 支持股票和期货两种资产类型

标准格式说明：
    内部标准格式：EXCHANGE.symbol（例如：SHFE.rb2501, SHSE.600000）
    - 交易所使用标准化代码（SHFE, DCE, CZCE, CFFEX, INE, SHSE, SZSE等）
    - 期货品种代码小写（rb, m, SR等）
    - 期货合约月份4位数字（2501表示2025年1月）
    - 郑商所合约年份使用4位（SR2501而非SR501）
    
外部格式：
    - 掘金/GoldMiner: SHFE.rb2501, CZCE.SR2501
    - Tushare: rb2501.SHF, SR2501.ZCE（注意郑商所简写为ZCE，上期所简写为SHF）
    - 聚宽/JoinQuant: rb2501.XSGE, SR2501.XZCE

作者: quantbox
创建日期: 2025-01-30
"""

from typing import Optional, List, Dict, Tuple, Union
from enum import Enum
import re
from functools import lru_cache

from quantbox.util.exchange_utils_new import (
    ExchangeType,
    normalize_exchange,
    denormalize_exchange,
    is_futures_exchange,
    is_stock_exchange,
    STANDARD_EXCHANGES,
    STOCK_EXCHANGES,
    FUTURES_EXCHANGES,
)


class ContractFormat(str, Enum):
    """合约代码格式枚举"""
    STANDARD = "standard"  # 标准格式: EXCHANGE.symbol
    GOLDMINER = "goldminer"  # 掘金格式: EXCHANGE.SYMBOL
    TUSHARE = "tushare"  # Tushare格式: symbol.EXCHANGE
    JOINQUANT = "joinquant"  # 聚宽格式: symbol.XEXCHANGE
    PLAIN = "plain"  # 纯代码: symbol (不含交易所)


class AssetType(str, Enum):
    """资产类型枚举"""
    STOCK = "stock"  # 股票
    FUTURES = "futures"  # 期货
    INDEX = "index"  # 指数
    FUND = "fund"  # 基金
    UNKNOWN = "unknown"  # 未知


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
    ):
        """
        初始化合约信息
        
        Args:
            exchange: 标准化交易所代码（如 SHFE, SHSE）
            symbol: 完整合约代码（期货如 rb2501，股票如 600000）
            asset_type: 资产类型
            underlying: 期货标的品种代码（如 rb, m, SR）
            year: 期货合约年份（如 2025）
            month: 期货合约月份（如 1, 5, 9）
        """
        self.exchange = exchange
        self.symbol = symbol
        self.asset_type = asset_type
        self.underlying = underlying
        self.year = year
        self.month = month
    
    def __repr__(self) -> str:
        return (
            f"ContractInfo(exchange={self.exchange}, symbol={self.symbol}, "
            f"asset_type={self.asset_type.value}, underlying={self.underlying}, "
            f"year={self.year}, month={self.month})"
        )
    
    def to_standard(self) -> str:
        """转换为标准格式代码"""
        return f"{self.exchange}.{self.symbol}"
    
    def is_futures(self) -> bool:
        """判断是否为期货合约"""
        return self.asset_type == AssetType.FUTURES
    
    def is_stock(self) -> bool:
        """判断是否为股票"""
        return self.asset_type == AssetType.STOCK


# 期货品种代码正则模式
_FUTURES_UNDERLYING_PATTERN = re.compile(r"^([A-Za-z]+)(\d+)$")

# 股票代码正则模式（6位数字）
_STOCK_PATTERN = re.compile(r"^\d{6}$")


def parse_contract(
    contract: str,
    default_exchange: Optional[str] = None,
    asset_type: Optional[AssetType] = None,
) -> ContractInfo:
    """
    解析合约代码，提取交易所、品种、年月等信息
    
    支持多种输入格式：
        - EXCHANGE.symbol (标准格式)
        - symbol (纯代码，需要提供 default_exchange)
        - EXCHANGE.SYMBOL (掘金格式，大写)
        - symbol.EXCHANGE (Tushare等格式)
    
    Args:
        contract: 合约代码
        default_exchange: 当合约代码不包含交易所时的默认交易所
        asset_type: 资产类型提示（可选，用于优化解析）
    
    Returns:
        ContractInfo: 解析后的合约信息对象
    
    Raises:
        ValueError: 合约代码格式无效或无法解析
    
    Examples:
        >>> info = parse_contract("SHFE.rb2501")
        >>> print(info.exchange, info.underlying, info.year, info.month)
        SHFE rb 2025 1
        
        >>> info = parse_contract("rb2501", default_exchange="SHFE")
        >>> print(info.to_standard())
        SHFE.rb2501
        
        >>> info = parse_contract("600000.SHSE")
        >>> print(info.asset_type)
        AssetType.STOCK
    """
    if not contract or not contract.strip():
        raise ValueError("合约代码不能为空")
    
    contract = contract.strip()
    
    # 尝试分割交易所和代码
    if "." in contract:
        parts = contract.split(".")
        if len(parts) != 2:
            raise ValueError(f"合约代码格式无效: {contract}")
        
        part1, part2 = parts
        
        # 判断哪部分是交易所（通常交易所代码全是字母且较短）
        # 支持 EXCHANGE.symbol 和 symbol.EXCHANGE 两种格式
        if part1.isalpha() and len(part1) <= 6:
            # 可能是 EXCHANGE.symbol 格式
            try:
                exchange_normalized = normalize_exchange(part1)
                exchange = exchange_normalized
                symbol = part2
            except ValueError:
                # 可能是 symbol.EXCHANGE 格式（如 Tushare）
                try:
                    exchange_normalized = normalize_exchange(part2)
                    exchange = exchange_normalized
                    symbol = part1
                except ValueError:
                    raise ValueError(f"无法识别交易所: {contract}")
        elif part2.isalpha() and len(part2) <= 6:
            # 应该是 symbol.EXCHANGE 格式
            try:
                exchange_normalized = normalize_exchange(part2)
                exchange = exchange_normalized
                symbol = part1
            except ValueError:
                raise ValueError(f"无法识别交易所: {contract}")
        else:
            raise ValueError(f"无法识别交易所: {contract}")
    else:
        # 纯合约代码，需要默认交易所
        if not default_exchange:
            raise ValueError(f"合约代码 '{contract}' 未包含交易所信息，需要提供 default_exchange")
        
        exchange = normalize_exchange(default_exchange)
        symbol = contract
    
    # 标准化symbol格式（期货小写）
    # 先判断资产类型
    detected_asset_type = asset_type or _detect_asset_type(symbol, exchange)
    
    if detected_asset_type == AssetType.FUTURES:
        # 期货：品种代码小写
        symbol_lower = symbol.lower()
        
        # 解析期货品种和年月
        match = _FUTURES_UNDERLYING_PATTERN.match(symbol_lower)
        if not match:
            raise ValueError(f"期货合约代码格式无效: {symbol}")
        
        underlying = match.group(1)  # 品种代码（如 rb, m, SR）
        date_part = match.group(2)  # 年月部分（如 2501）
        
        # 检查是否为主力合约标识（888, 000等）
        if date_part in ["888", "000", "99", "00"]:
            # 主力合约，保持原样
            return ContractInfo(
                exchange=exchange,
                symbol=symbol_lower,
                asset_type=AssetType.FUTURES,
                underlying=underlying,
                year=None,
                month=None,
            )
        
        # 处理郑商所特殊格式（可能是3位年月如501）
        elif exchange == "CZCE" and len(date_part) == 3:
            # 需要智能判断是20xx还是21xx
            year_last_digit = int(date_part[0])
            # 假设当前年份2020年代，5-9表示2025-2029，0-4表示2030-2034
            if year_last_digit >= 0:  # 2020-2029
                year = 2020 + year_last_digit
            month = int(date_part[1:])
            # 转换为标准4位格式
            symbol_normalized = f"{underlying}{year % 100:02d}{month:02d}"
        elif len(date_part) == 4:
            year = 2000 + int(date_part[:2])
            month = int(date_part[2:])
            symbol_normalized = symbol_lower
        else:
            raise ValueError(f"期货合约日期格式无效: {symbol}")
        
        return ContractInfo(
            exchange=exchange,
            symbol=symbol_normalized,
            asset_type=AssetType.FUTURES,
            underlying=underlying,
            year=year,
            month=month,
        )
    
    elif detected_asset_type == AssetType.STOCK:
        # 股票：保持原样（通常是6位数字）
        if not _STOCK_PATTERN.match(symbol):
            raise ValueError(f"股票代码格式无效: {symbol}")
        
        return ContractInfo(
            exchange=exchange,
            symbol=symbol,
            asset_type=AssetType.STOCK,
        )
    
    else:
        # 其他类型或未知：保持原样
        return ContractInfo(
            exchange=exchange,
            symbol=symbol,
            asset_type=detected_asset_type,
        )


def _detect_asset_type(symbol: str, exchange: str) -> AssetType:
    """
    根据代码和交易所推断资产类型
    
    Args:
        symbol: 合约代码
        exchange: 交易所代码
    
    Returns:
        AssetType: 推断的资产类型
    """
    # 根据交易所判断
    if is_futures_exchange(exchange):
        return AssetType.FUTURES
    elif is_stock_exchange(exchange):
        # 进一步判断是股票还是指数
        if _STOCK_PATTERN.match(symbol):
            return AssetType.STOCK
        else:
            return AssetType.INDEX
    else:
        return AssetType.UNKNOWN


def format_contract(
    contract: str,
    target_format: Union[ContractFormat, str],
    default_exchange: Optional[str] = None,
    asset_type: Optional[AssetType] = None,
) -> str:
    """
    将合约代码转换为指定格式
    
    Args:
        contract: 输入合约代码（任意支持的格式）
        target_format: 目标格式
        default_exchange: 默认交易所（当输入代码不含交易所时）
        asset_type: 资产类型提示（可选）
    
    Returns:
        str: 转换后的合约代码
    
    Raises:
        ValueError: 合约代码无效或格式不支持
    
    Examples:
        >>> format_contract("SHFE.rb2501", ContractFormat.TUSHARE)
        'rb2501.SHF'
        
        >>> format_contract("rb2501.SHF", ContractFormat.STANDARD)
        'SHFE.rb2501'
        
        >>> format_contract("SR501", ContractFormat.STANDARD, default_exchange="CZCE")
        'CZCE.sr2501'
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
        # 标准格式: EXCHANGE.symbol
        return f"{info.exchange}.{info.symbol}"
    
    elif target_format == ContractFormat.GOLDMINER:
        # 掘金格式: EXCHANGE.SYMBOL (大写)
        # 掘金使用不同的交易所简称
        exchange_gm = denormalize_exchange(info.exchange, "goldminer")
        return f"{exchange_gm}.{info.symbol.upper()}"
    
    elif target_format == ContractFormat.TUSHARE:
        # Tushare格式: symbol.EXCHANGE
        # Tushare使用简写交易所代码
        exchange_ts = denormalize_exchange(info.exchange, "tushare")
        
        # 处理郑商所特殊格式（Tushare可能使用3位年月）
        if info.asset_type == AssetType.FUTURES and info.exchange == "CZCE":
            # 某些情况下转换为3位格式（但现在一般统一用4位）
            # 这里保持4位标准格式
            return f"{info.symbol}.{exchange_ts}"
        else:
            return f"{info.symbol}.{exchange_ts}"
    
    elif target_format == ContractFormat.JOINQUANT:
        # 聚宽格式: symbol.XEXCHANGE
        exchange_jq = denormalize_exchange(info.exchange, "joinquant")
        return f"{info.symbol}.{exchange_jq}"
    
    elif target_format == ContractFormat.PLAIN:
        # 纯代码，不含交易所
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
        contracts: 单个合约代码或合约代码列表（支持逗号分隔的字符串）
        target_format: 目标格式
        default_exchange: 默认交易所
        asset_type: 资产类型提示
    
    Returns:
        List[str]: 转换后的合约代码列表
    
    Examples:
        >>> format_contracts("SHFE.rb2501,SHFE.hc2501", "tushare")
        ['rb2501.SHF', 'hc2501.SHF']
        
        >>> format_contracts(["rb2501", "hc2501"], "standard", default_exchange="SHFE")
        ['SHFE.rb2501', 'SHFE.hc2501']
    """
    # 处理输入
    if isinstance(contracts, str):
        # 支持逗号分隔的字符串
        contracts = [c.strip() for c in contracts.split(",") if c.strip()]
    
    # 批量转换
    results = []
    for contract in contracts:
        try:
            formatted = format_contract(contract, target_format, default_exchange, asset_type)
            results.append(formatted)
        except ValueError as e:
            # 记录错误但继续处理其他代码
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
        exchange: 期望的交易所（可选，用于验证交易所是否匹配）
        asset_type: 期望的资产类型（可选，用于验证类型是否匹配）
    
    Returns:
        bool: 是否有效
    
    Examples:
        >>> validate_contract("SHFE.rb2501")
        True
        
        >>> validate_contract("SHFE.rb2501", exchange="DCE")
        False
        
        >>> validate_contract("invalid.code")
        False
    """
    try:
        info = parse_contract(contract)
        
        # 验证交易所
        if exchange is not None:
            expected_exchange = normalize_exchange(exchange)
            if info.exchange != expected_exchange:
                return False
        
        # 验证资产类型
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
        exchange: 期望的交易所（可选）
        asset_type: 期望的资产类型（可选）
        skip_invalid: 是否跳过无效代码（True时只返回整体是否有有效代码）
    
    Returns:
        Union[bool, List[bool]]: 
            - skip_invalid=False: 返回每个合约的验证结果列表
            - skip_invalid=True: 返回是否至少有一个有效合约
    
    Examples:
        >>> validate_contracts(["SHFE.rb2501", "DCE.m2501"])
        [True, True]
        
        >>> validate_contracts(["SHFE.rb2501", "invalid"], skip_invalid=True)
        True
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
        contract: 合约代码（标准格式 EXCHANGE.symbol）
    
    Returns:
        Tuple[str, str]: (交易所, 代码)
    
    Raises:
        ValueError: 格式无效
    
    Examples:
        >>> split_contract("SHFE.rb2501")
        ('SHFE', 'rb2501')
    """
    info = parse_contract(contract)
    return (info.exchange, info.symbol)


def get_underlying(contract: str) -> Optional[str]:
    """
    获取期货合约的标的品种代码
    
    Args:
        contract: 期货合约代码
    
    Returns:
        Optional[str]: 品种代码（如 rb, m, SR），非期货返回 None
    
    Examples:
        >>> get_underlying("SHFE.rb2501")
        'rb'
        
        >>> get_underlying("SHSE.600000")
        None
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
        Optional[Tuple[int, int]]: (年份, 月份)，非期货返回 None
    
    Examples:
        >>> get_contract_month("SHFE.rb2501")
        (2025, 1)
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
    判断是否为主力合约代码（通常以888或00结尾）
    
    Args:
        contract: 合约代码
    
    Returns:
        bool: 是否为主力合约标识
    
    Examples:
        >>> is_main_contract("SHFE.rb888")
        True
        
        >>> is_main_contract("SHFE.rb2501")
        False
    """
    try:
        info = parse_contract(contract)
        # 只对期货合约判断
        if info.asset_type != AssetType.FUTURES:
            return False
        symbol_lower = info.symbol.lower()
        return symbol_lower.endswith("888") or symbol_lower.endswith("000")
    except (ValueError, Exception):
        return False


def normalize_contract(
    contract: str,
    default_exchange: Optional[str] = None,
) -> str:
    """
    标准化合约代码为内部统一格式
    
    将各种外部格式转换为标准格式: EXCHANGE.symbol
    - 期货品种代码小写
    - 郑商所合约统一使用4位年月
    - 交易所代码标准化
    
    Args:
        contract: 输入合约代码
        default_exchange: 默认交易所
    
    Returns:
        str: 标准化后的合约代码
    
    Examples:
        >>> normalize_contract("rb2501.SHF")
        'SHFE.rb2501'
        
        >>> normalize_contract("SR501", default_exchange="CZCE")
        'CZCE.sr2501'
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
    
    Examples:
        >>> normalize_contracts("rb2501.SHF,SR501.ZCE")
        ['SHFE.rb2501', 'CZCE.sr2501']
    """
    return format_contracts(contracts, ContractFormat.STANDARD, default_exchange)


# 为了向后兼容，提供旧函数名的别名
util_format_future_symbols = format_contracts
