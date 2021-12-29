import os.path
from datetime import datetime
import pandas as pd
import pandas_datareader as pdr
import numpy as np


def get_price_data(ticker, start, end):
    df = pdr.get_data_yahoo(ticker, start, end)  # ['Adj Close']

    df['DATE'] = df.index
    df['YEAR'] = df['DATE'].dt.strftime('%Y').astype(str)
    df['YEAR_MM'] = df['DATE'].dt.strftime('%Y%m').astype(str)
    df['PCT_CHANGE'] = df['Adj Close'].pct_change()

    return df


def add_evaluation_property(df):
    df['DAY_RETURN (%)'] = df['PCT_CHANGE'] * 100
    df['DAY_RETURN (%)'] = df['DAY_RETURN (%)'].round(2)
    df['CUM_RETURN'] = np.exp(np.log1p(df['PCT_CHANGE'])).cumsum()

    df['MA_5D'] = df['Adj Close'].rolling(5).mean()
    df['MA_10D'] = df['Adj Close'].rolling(10).mean()
    df['MA_20D'] = df['Adj Close'].rolling(20).mean()
    df['MA_60D'] = df['Adj Close'].rolling(60).mean()
    df['MA_120D'] = df['Adj Close'].rolling(120).mean()
    df['MA_200D'] = df['Adj Close'].rolling(200).mean()
    # BA: Business Year End / A: Year End
    # df['MA_Y'] = df.resample('A', on='DATE')['Adj Close'].rolling(1).mean()

    df['DRAWDOWN'] = (-(df['Adj Close'].cummax() - df['Adj Close']) / df['Adj Close'].cummax()) * 100
    df['DRAWDOWN (%)'] = df['DRAWDOWN'].round(2)

    column_order = ['DATE', 'YEAR', 'YEAR_MM'] + [col for col in list(df.columns.values) if
                                                  col not in ['DATE', 'YEAR', 'YEAR_MM']]
    df = df[column_order]
    if all(i in df.columns.tolist() for i in ['High', 'Low', 'Open', 'Close', 'Volume']):
        df = df.drop(['High', 'Low', 'Open', 'Close', 'Volume'], axis=1)
    df = df.reset_index(drop=True)

    return df


def gen_simulation_data(df_origin, leverage):
    df = df_origin.copy()
    initial_price = df['Adj Close'].head(1).item()

    for i in range(len(df)):
        if i > 0:
            df.loc[df.index[i], 'Adj Close'] = df.loc[df.index[i - 1], 'Adj Close'] + df.loc[
                df.index[i - 1], 'Adj Close'] * (df.loc[df.index[i], 'PCT_CHANGE'] * leverage)
    df.loc[df.index[0], 'Adj Close'] = initial_price
    df['PCT_CHANGE'] = df['Adj Close'].pct_change()

    return df


def dfs_to_excel(targets, ticker_simulation=None):
    start = datetime(2000, 1, 2)
    end = datetime(datetime.now().year, datetime.now().month, datetime.now().day)
    writer = pd.ExcelWriter('NASDAQ-SP-QQQ-data.xlsx', engine='xlsxwriter')

    dfs = dict()
    for ticker in targets:
        df = get_price_data(ticker, start, end)
        df = add_evaluation_property(df)
        dfs[ticker] = df

        if ticker_simulation and ticker in ticker_simulation:
            ticker_2x = ticker + 'SIMx2'
            dfx2 = gen_simulation_data(df, 2)
            dfs[ticker_2x] = add_evaluation_property(dfx2)
            ticker_3x = ticker + 'SIMx3'
            dfx3 = gen_simulation_data(df, 3)
            dfs[ticker_3x] = add_evaluation_property(dfx3)

    for sheet, frame in dfs.items():  # .use .items for python 3.X
        frame.to_excel(writer, sheet_name=sheet, index=False)

    writer.save()


def populate_rebalancing_date_monthly(df):
    df['DATE'] = df.index
    group_yyyymm = df.groupby('YEAR_MM', as_index=False)
    begin_date_monthly = group_yyyymm.head(1)
    end_date_monthly = group_yyyymm.tail(1)
    bl = begin_date_monthly['DATE'].tolist()
    el = end_date_monthly['DATE'].tolist()

    return bl, el


if __name__ == '__main__':
    # ['^IXIC', '^DJI', '^GSPC', ^SOX] NASDAQ, DOW JONES, S&P, PHLX Semiconductor
    # Download from Web
    # targets = ['^IXIC', 'QQQ', 'TQQQ', 'TECL', '^GSPC', 'SPXL', '^SOX', 'SOXX', 'SOXL', 'SMH']
    # ticker_simulation = ['QQQ', '^GSPC', '^SOX']
    # dfs_to_excel(targets, ticker_simulation)

    # Read from Excel
    xls = pd.ExcelFile(os.path.abspath('./NASDAQ-SP-QQQ-data.xlsx'))

    dfs = dict()
    for sheet in xls.sheet_names:
        if 'SIM' in sheet:
            df = pd.read_excel('./NASDAQ-SP-QQQ-data.xlsx', index_col='DATE', sheet_name=sheet)
            dfs[sheet] = df

    # Monthly Rebalancing
    # initial budget = 10000
    # resample : https://stackoverflow.com/questions/17001389/pandas-resample-documentation

    # Avg Momentum Score
    avg_mtm_score_list = []
    for ticker, df in dfs.items():
        print(ticker)
        # business year start & business year end
        bl, el = populate_rebalancing_date_monthly(df)
        year_values = set(map(lambda b: b.year, bl))
        group_by_year = [[(b, e) for b, e in list(zip(bl, el)) if e.year == x] for x in year_values]

        avg_score_by_year_list = list()
        for year in group_by_year:
            avg_score_by_year_item = dict()
            avg_score_count = 0
            for bl, el in year:
                if df[df['DATE'] == bl]['Adj Close'].item() < df[df['DATE'] == el]['Adj Close'].item():
                    avg_score_by_year_item[str(bl.year) + str(bl.month).zfill(2)] = 1
                    avg_score_count += 1
                else:
                    avg_score_by_year_item[str(bl.year) + str(bl.month).zfill(2)] = 0

            avg_score_by_year_list.append(avg_score_by_year_item)
            print(bl.year, avg_score_count / len(year))
        print(avg_score_by_year_list)
