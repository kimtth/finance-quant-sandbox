import os.path
from datetime import datetime, timedelta
import pandas as pd
import pandas_datareader as pdr
import numpy as np
import nasdaq_data_rebalance


def get_price_data(ticker, start, end):
    df = pdr.get_data_yahoo(ticker, start, end)  # ['Adj Close']

    df['DATE'] = df.index
    df['YEAR'] = df['DATE'].dt.strftime('%Y').astype(str)
    df['YEAR_MM'] = df['DATE'].dt.strftime('%Y%m').astype(str)

    return df


def add_evaluation_property(df):
    df['PCT_CHANGE'] = df['Adj Close'].pct_change()
    df['DAY_RETURN (%)'] = df['PCT_CHANGE'] * 100
    df['DAY_RETURN (%)'] = df['DAY_RETURN (%)'].round(2)
    df['CUM_RETURN'] = (1 + df['PCT_CHANGE']).cumprod() - 1  # np.exp(np.log1p(df['PCT_CHANGE'])).cumsum()

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


def dfs_to_excel(targets, start, end, ticker_simulation=None):
    writer = pd.ExcelWriter('./portfolio/NASDAQ-SP-QQQ-data.xlsx', engine='xlsxwriter')

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


def get_unemployment_to_excel(start, end):
    df_unemployment = pdr.DataReader('UNRATE', 'fred', start, end)
    df_unemployment = df_unemployment.rename(columns={'UNRATE': 'UNEMPLOYMENT_RATE'})
    # @Tip: df_unemployment['UEM_CHANGE'] = df_unemployment['UNEMPLOYMENT_RATE'] - df_unemployment[
    # 'UNEMPLOYMENT_RATE'].shift(1)

    df_unemployment['DATE'] = df_unemployment.index
    # @Debug: print(df.dtypes) # df.info()
    df_unemployment['YEAR'] = df_unemployment['DATE'].dt.strftime('%Y').astype(str)
    df_unemployment['YEAR_MONTH'] = df_unemployment['DATE'].dt.strftime('%Y%m').astype(str)
    df_unemployment = add_uem_evaluation_property(df_unemployment)

    df_unemployment.to_excel('./portfolio/US-UNEMPLOYMENT-data.xlsx', sheet_name='UEM', index=False)

    return df_unemployment


def avg_momentum_score(df, invest_date):
    mtm_score_sum = 0
    mtm_score_cnt = 0
    for i in range(1, 13):
        mtm_score_date = nasdaq_data_rebalance.end_of_month(df, invest_date, i)
        if mtm_score_date and len(df[df['DATE'] == mtm_score_date]['Adj Close']) > 0:
            mtm_score_date_price = df[df['DATE'] == mtm_score_date]['Adj Close'].item()
            invest_date_price = df[df['DATE'] == invest_date]['Adj Close'].item()
            return_m = (invest_date_price / mtm_score_date_price) - 1
            if return_m > float(0):
                mtm_score_sum = mtm_score_sum + 1
            mtm_score_cnt += 1

    avg_mtm_score = mtm_score_sum / mtm_score_cnt
    print(mtm_score_cnt, round(avg_mtm_score, 2))
    return avg_mtm_score


def add_uem_evaluation_property(df):
    df['UEM_CHANGE'] = df['UNEMPLOYMENT_RATE'].pct_change()
    df['MA_12M'] = df['UNEMPLOYMENT_RATE'].rolling(12).mean()
    df = df.reset_index(drop=True)

    return df


def pause_and_cash_hold(df_origin, dropdown=15, leverage=1, period=30):
    df = df_origin.copy()
    minus_dropdown = df[df['DAY_RETURN (%)'] <= (-dropdown * leverage)]

    prev_pause_end_date = None
    prev_idx = 1
    for i in range(len(minus_dropdown)):
        pause_date = minus_dropdown.loc[minus_dropdown.index[i], 'DATE']
        pause_date_price = minus_dropdown.loc[minus_dropdown.index[i], 'Adj Close']
        pause_end_date = pause_date + timedelta(days=period)

        if i > 0 and pause_date <= prev_pause_end_date:
            pause_date_price = minus_dropdown.loc[minus_dropdown.index[i - prev_idx], 'Adj Close']
            prev_idx = prev_idx + 1
        elif i == 0:
            pass
        else:
            prev_idx = 1
        # print(pause_date, pause_date_price, pause_end_date, prev_idx)

        df['Adj Close'] = df[['DATE', 'Adj Close']].apply(
            lambda x: pause_date_price if (x['DATE'] >= pause_date) and (x['DATE'] <= pause_end_date) else x[
                'Adj Close'], axis=1)

        prev_pause_end_date = pause_end_date

    return df


if __name__ == '__main__':
    start = datetime(2000, 1, 2)
    end = datetime(datetime.now().year, datetime.now().month, datetime.now().day)
    # ['^IXIC', '^DJI', '^GSPC', ^SOX] NASDAQ, DOW JONES, S&P, PHLX Semiconductor
    # Download from Web
    # targets = ['^IXIC', 'QQQ', 'TQQQ', 'TECL', '^GSPC', 'SPXL', '^SOX', 'SOXX', 'SOXL', 'SMH']
    # ticker_simulation = ['QQQ', '^GSPC', '^SOX']
    # dfs_to_excel(targets, start, end, ticker_simulation)
    # get_unemployment_to_excel(start, end)

    # Read from Excel
    '''
    xls = pd.ExcelFile(os.path.abspath('./portfolio/NASDAQ-SP-QQQ-data.xlsx'))

    dfs = dict()
    for sheet in xls.sheet_names:
        if 'SIM' in sheet:
            df = pd.read_excel('./portfolio/NASDAQ-SP-QQQ-data.xlsx', sheet_name=sheet) # index_col='DATE',
            dfs[sheet] = df

    # Monthly Rebalancing - End of Month
    # initial budget = 10000
    # resample : https://stackoverflow.com/questions/17001389/pandas-resample-documentation
    
    # Business year start & business year end Test
    bl, el = populate_rebalancing_date_monthly(df)
    invest_date = el[-1]
    el = el[:-1]

    # Avg Momentum Score Test
    avg_mtm_score_list = []
    for ticker, df in dfs.items():
        print(ticker)

        invest_date = df['DATE'].tail(1).item()
        avg_mtm_score = avg_momentum_score(df, invest_date)
    '''
    # Pause and Cash hold test
    xls = pd.ExcelFile(os.path.abspath('./portfolio/NASDAQ-SP-QQQ-data.xlsx'))
    for sheet in xls.sheet_names:
        if '^SOXSIMx3' in sheet:
            df = pd.read_excel('./NASDAQ-SP-QQQ-data.xlsx', sheet_name=sheet)  # index_col='DATE',
            df = pause_and_cash_hold(df)
            df = df[['DATE', 'YEAR', 'YEAR_MM', 'Adj Close']]
            df.to_excel('SOXSIMx3-Cash-Hold-data.xlsx', sheet_name='SOXSIMx3', index=False)
