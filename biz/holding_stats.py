"""
期货持仓统计分析脚本

功能：
- 分析指定时间范围内各品种的持仓情况
- 计算各经纪商的累计盈亏
- 生成 Excel 报告

注意事项：
- 本脚本使用收盘价代替结算价计算盈亏（数据源限制）
- 如需精确结算价，请使用 Tushare Pro 或掘金数据源
- 需要本地数据库包含完整的历史持仓和行情数据
"""

from quantbox.services.market_data_service import MarketDataService
import os
import pandas as pd

# 本地查询器
queryer = MarketDataService()

# 1. 参数设置
start_date = "2023-11-27" # 考察时间起始时间
end_date = "2024-12-03" # 考察时间结束时间

# 2. 获取所有可用品种列表
all_specs = set()
all_contracts = queryer.get_future_contracts(date=start_date)
all_specs.update(all_contracts['chinese_name'].unique())

# 3. 循环处理每个品种
for target_spec in all_specs:
    print(f"Processing {target_spec}...")

    # 3.1 在考察时间范围内，合约获取
    total_symbols = set()
    for cursor_date in pd.date_range(start_date, end_date):
        symbols = queryer.get_future_contracts(spec_names=target_spec, date=cursor_date)['symbol'].tolist()
        total_symbols.update(symbols)
    total_symbols = list(total_symbols)

    # 3.2 分合约计算累计盈亏
    total_pnl = pd.DataFrame()
    total_cumpnl = pd.DataFrame()
    for symbol in total_symbols:
        # 3.2.1 查找当前合约的上市日期
        list_date = queryer.get_future_contracts(
            symbols=symbol
        )['list_date'].iloc[0]
        # 转换为 Python int 类型（从 numpy.int64）
        list_date = int(list_date)

        # 3.2.2 获取指定合约的行情数据
        df_daily = queryer.get_future_daily(
            symbols=symbol,
            start_date=list_date,
            end_date=end_date
        )

        if df_daily.empty:
            continue

        # 3.2.3 计算当前合约的累计盈亏
        # 指定时间段内，指定合约的持仓排行情况，并按日期，经纪商分组
        pre_holdings = queryer.get_future_holdings(
            symbols=symbol,
            start_date=start_date,
            end_date=end_date
        )
        if pre_holdings.empty:
            continue
        # 注意：新 API 使用 date 字段而非 trade_date
        pre_holdings = pre_holdings.fillna(0.).groupby(["date", "broker"]).apply(
            lambda x: x["short_hld"] - x["long_hld"]
        ).droplevel(2)

        # 3.2.4 计算权重，即实际合约结算价差
        # 注意：由于数据源不包含 settle/pre_settle 字段，使用 close 价格代替
        # 如果需要精确的结算价，请从 Tushare Pro 或掘金等数据源获取
        if 'settle' in df_daily.columns and 'pre_settle' in df_daily.columns:
            settle_difference = df_daily.groupby(['date']).apply(
                lambda x: x['pre_settle'] - x["settle"]
            ).droplevel(1)
        else:
            # 使用收盘价代替结算价（注意：新API返回date字段）
            df_daily['pre_close_shift'] = df_daily.groupby('symbol')['close'].shift(1)
            settle_difference = df_daily.groupby(['date']).apply(
                lambda x: x['pre_close_shift'] - x["close"]
            ).droplevel(1)

        # 3.2.5 计算逐日盈亏
        pnl = pre_holdings.unstack(level=1).shift(1).reindex(settle_difference.index).mul(settle_difference, axis=0).stack()
        cumpnl = pnl.groupby(level=1).apply(lambda x: x.cumsum()).droplevel(level=2)
        pnl = pnl.rename("pnl").reset_index()
        pnl['symbol'] = symbol
        cumpnl = cumpnl.rename("cumpnl").reset_index()
        cumpnl['symbol'] = symbol

        total_pnl = pd.concat([total_pnl, pnl], axis=0)
        total_cumpnl = pd.concat([total_cumpnl, cumpnl], axis=0)

    # 3.3 保存当前品种的结果
    if not total_pnl.empty and not total_cumpnl.empty:
        # 获取指定品种指定时间范围内的排行情况
        results = total_cumpnl.groupby(['symbol', 'broker']).apply(lambda x: x.iloc[-1]).groupby(level=1).apply(lambda x: x['cumpnl'].sum()).sort_values()
        if not os.path.exists("results/"):
            os.makedirs("results")

        # 保存pnl和cumpnl到Excel的不同sheet中
        with pd.ExcelWriter(f'results/{target_spec}-{start_date}-{end_date}.xlsx') as writer:
            results.to_excel(writer, sheet_name='summary')
            total_pnl.to_excel(writer, sheet_name='pnl', index=False)
            total_cumpnl.to_excel(writer, sheet_name='cumpnl', index=False)
        print(f"Saved results for {target_spec}")
