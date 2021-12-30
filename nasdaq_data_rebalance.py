import pandas as pd
from datetime import datetime


def end_of_month(df, date, n_month_back=0):
    n_day_adjust = 0
    n_year_back = 0
    date_ago = None
    while True:
        if n_day_adjust > 31:
            break

        try:
            if n_month_back == 12:
                n_year_back = 1
                n_month_back = 0

            date_ago = datetime(date.year - n_year_back, date.month - n_month_back, date.day - n_day_adjust)
            if not len(df[df['DATE'] == date_ago]) > 0:
                n_day_adjust = n_day_adjust + 1
            else:
                break
        except ValueError:
            n_day_adjust = n_day_adjust + 1
            continue

    return date_ago


def end_of_year(df, date, n_year_back=0):
    date_n_yr_adjust_range = datetime(date.year - n_year_back, date.month, date.day - 5)

    try:
        date_ago = datetime(date.year - n_year_back, date.month, date.day)
        # @Debug: print(type(date), type(date_1yr_ago), date, date_1yr_ago)
    except ValueError:
        # @Tip: e.g. 2012-02-29 00:00:00 2011-02-28 00:00:00
        #       date.day-1 : ValueError: day is out of range for month
        date_ago = datetime(date.year - n_year_back, date.month, date.day - 1)

    date_1yr_ago_df = df[
        (df['DATE'] > date_n_yr_adjust_range) & (df['DATE'] <= date_ago)].tail(1)

    return date_1yr_ago_df


def rebalancing_criterias_uem(df_spy, df_uem, rebalancing_date):
    spy_price = df_spy.loc[df_spy['DATE'] == rebalancing_date, 'Adj Close'].item()
    spy_ma_200d = df_spy.loc[df_spy['DATE'] == rebalancing_date, 'MA_200D'].item()

    uem_yyyymm = str(rebalancing_date.year) + str(rebalancing_date.month).zfill(2)
    df_uem['YEAR_MONTH'] = df_uem['YEAR_MONTH'].astype(str)
    uem_index = df_uem.loc[df_uem['YEAR_MONTH'] == uem_yyyymm, 'UNEMPLOYMENT_RATE'].item()
    uem_12m = df_uem.loc[df_uem['YEAR_MONTH'] == uem_yyyymm, 'MA_12M'].item()

    if spy_price < spy_ma_200d and uem_index > uem_12m:
        return 'SHY'
    else:
        return 'RISK'


def rebalance_portfolio_by_ratio(df, date, portfolio_dict: dict):
    pass

    if len(df[df['DATE'] == date]) > 0:
        rebalance_date_df = df[df['DATE'] == date]
        row_num = rebalance_date_df.index[0]

        if row_num == 0:  # invest_init
            budget = 10000
        else:
            prev_row_num = row_num - 1
            prev_rebalance_date_df = df.iloc[prev_row_num, :].to_frame()

            # {QQQ: 50, SPY: 50}
            tickers = [ticker + '_P' for ticker, ratio in portfolio_dict.items()]
            budget = prev_rebalance_date_df[tickers].sum()


        # df[ticker+'_Q'] = budget * int(portfolio_dict[ticker]) for ticker in tickers]
