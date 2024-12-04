from quantbox.fetchers.local_fetcher import LocalFetcher
import os
import pandas as pd

# 本地查询器
queryer = LocalFetcher()

# 1. 参数设置
target_spec = "螺纹钢" # 考察品种
start_date = "2023-11-27" # 考察时间起始时间
end_date = "2024-12-03" # 考察时间结束时间

# 2. 在考察时间范围内， 合约获取
total_symbols = set()
for cursor_date in pd.date_range(start_date, end_date):
    symbols = queryer.fetch_future_contracts(spec_name=target_spec, cursor_date=cursor_date)['symbol'].tolist()
    total_symbols.update(symbols)
total_symbols = list(total_symbols)

# 3. 分合约计算累计盈亏
total_pnl = pd.DataFrame()
total_cumpnl = pd.DataFrame()
for symbol in total_symbols:
    # 3.1 查找当前合约的上市日期
    list_date = queryer.fetch_future_contracts(
        symbol=symbol
    )['list_date'].iloc[0]

    # 3.2 获取指定合约的行情数据
    df_daily = queryer.fetch_future_daily(
        symbols=symbol,
        start_date=list_date,
        end_date=end_date
    )

    if df_daily.empty:
        continue

    # 3.3 计算当前合约的累计盈亏
    # 指定时间段内，指定合约的持仓排行情况，并按日期，经纪商分组
    pre_holdings = queryer.fetch_future_holdings(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date
    )
    if pre_holdings.empty:
        continue
    pre_holdings = pre_holdings.fillna(0.).groupby(["trade_date", "broker"]).apply(
        lambda x: x["short_hld"] - x["long_hld"]
    ).droplevel(2)

    # 3.4 计算权重，即实际合约结算价差
    settle_difference = df_daily.groupby(['trade_date']).apply(lambda x: x['pre_settle'] - x["settle"]).droplevel(1)

    # 3.5 计算逐日盈亏
    pnl = pre_holdings.unstack(level=1).shift(1).reindex(settle_difference.index).mul(settle_difference, axis=0).stack()
    cumpnl = pnl.groupby(level=1).apply(lambda x: x.cumsum()).droplevel(level=2)
    pnl = pnl.rename("pnl").reset_index()
    pnl['symbol'] = symbol
    cumpnl = cumpnl.rename("cumpnl").reset_index()
    cumpnl['symbol'] = symbol

    total_pnl = pd.concat([total_pnl, pnl], axis=0)
    total_cumpnl = pd.concat([total_cumpnl, cumpnl], axis=0)

# 获取指定品种指定时间范围内的排行情况
results = total_cumpnl.groupby(['symbol', 'broker']).apply(lambda x: x.iloc[-1]).groupby(level=1).apply(lambda x: x['cumpnl'].sum()).sort_values()
if not os.path.exists("results/"):
    os.makedirs("results")
results.to_excel(f'results/{target_spec}-{start_date}-{end_date}.xlsx')

