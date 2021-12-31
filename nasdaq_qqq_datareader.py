import os.path
from datetime import datetime, timedelta

import pandas as pd
import pandas_datareader as pdr

from nasdaq_data_rebalance import rebalance_portfolio_by_ratio, next_transaction_date_mm, \
    rebalancing_criterias_uem, graph_cagr_mdd


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


def add_uem_evaluation_property(df):
    df['UEM_CHANGE'] = df['UNEMPLOYMENT_RATE'].pct_change()
    df['MA_12M'] = df['UNEMPLOYMENT_RATE'].rolling(12).mean()
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
        mtm_score_date = next_transaction_date_mm(df, invest_date, i)
        if mtm_score_date and len(df[df['DATE'] == mtm_score_date]['Adj Close']) > 0:
            mtm_score_date_price = df[df['DATE'] == mtm_score_date]['Adj Close'].item()
            invest_date_price = df[df['DATE'] == invest_date]['Adj Close'].item()
            return_m = (invest_date_price / mtm_score_date_price) - 1
            if return_m > float(0):
                mtm_score_sum = mtm_score_sum + 1
            mtm_score_cnt += 1

    if mtm_score_cnt == 0:
        return 0, 0

    avg_mtm_score = round(mtm_score_sum / mtm_score_cnt, 2)
    # print(invest_date, mtm_score_cnt, avg_mtm_score)
    return avg_mtm_score, mtm_score_cnt


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
            df['Adj Period'] = False
            pass
        else:
            prev_idx = 1
        # print(pause_date, pause_date_price, pause_end_date, prev_idx)

        df['Adj Close'] = df[['DATE', 'Adj Close']].apply(
            lambda x: pause_date_price if (x['DATE'] >= pause_date) and (x['DATE'] <= pause_end_date) else x[
                'Adj Close'], axis=1)

        df['Adj Period'] = df[['DATE', 'Adj Close', 'Adj Period']].apply(
            lambda x: True if (x['DATE'] >= pause_date) and (x['DATE'] <= pause_end_date) else x[
                'Adj Period'], axis=1)

        prev_pause_end_date = pause_end_date

    # print(df.columns.values)
    cols_list = list(df.columns.values)[:4]
    cols_list.append(list(df.columns.values)[-1])
    post_cols_list = list(df.columns.values)[5:-1]
    cols_list = cols_list + post_cols_list

    df = df[cols_list]
    df = df[['DATE', 'YEAR', 'YEAR_MM', 'Adj Close', 'Adj Period']]

    return df, minus_dropdown


if __name__ == '__main__':
    start = datetime(2000, 1, 2)
    end = datetime(datetime.now().year, datetime.now().month, datetime.now().day)
    # ['^IXIC', '^DJI', '^GSPC', ^SOX] NASDAQ, DOW JONES, S&P, PHLX Semiconductor
    # Download from Web
    # targets = ['^IXIC', 'SPY', 'SHY', 'QQQ', 'TQQQ', 'TECL', '^GSPC', 'SPXL', '^SOX', 'SOXX', 'SOXL', 'SMH']
    # ticker_simulation = ['QQQ', '^GSPC', '^SOX']
    # dfs_to_excel(targets, start, end, ticker_simulation)
    # start = datetime(1999, 1, 1)
    # get_unemployment_to_excel(start, end)

    # Pause and Cash hold test
    # xls = pd.ExcelFile(os.path.abspath('./portfolio/NASDAQ-SP-QQQ-data.xlsx'))
    # for sheet in xls.sheet_names:
    #     if '^SOXSIMx3' in sheet:
    #         df = pd.read_excel('./portfolio/NASDAQ-SP-QQQ-data.xlsx', sheet_name=sheet)  # index_col='DATE',
    #         df, _ = pause_and_cash_hold(df)
    #         df.to_excel('./portfolio/SOXSIMx3-Cash-Hold-data.xlsx', sheet_name='SOXSIMx3', index=False)

    # Read from Excel
    # Monthly Rebalancing - End of Month
    porfpolio_tickers = ['^SOXSIMx3', 'SPY', 'SHY', '^GSPC']
    uem_df = pd.read_excel(os.path.abspath('./portfolio/US-UNEMPLOYMENT-data.xlsx'))
    xls = pd.ExcelFile(os.path.abspath('./portfolio/NASDAQ-SP-QQQ-data.xlsx'))
    dfs = dict()
    for sheet in xls.sheet_names:
        if sheet in porfpolio_tickers:
            df = pd.read_excel('./portfolio/NASDAQ-SP-QQQ-data.xlsx', sheet_name=sheet)  # index_col='DATE',
            dfs[sheet] = df
    dfs['UEM'] = uem_df

    risky_asset_ticker = '^SOXSIMx3'
    risky_asset_df = dfs[risky_asset_ticker]
    cash_asset_ticker = 'SHY'
    cash_asset_df = dfs[cash_asset_ticker]

    # Business year start & business year end Test
    begin_month, _end_month = populate_rebalancing_date_monthly(risky_asset_df)

    # Type: Datetime
    initial_invest_date = begin_month[0]
    rebalancing_dates = _end_month
    last_date = _end_month[-1]
    end_month = _end_month[:-1]

    df_spy = dfs['SPY']
    df_spy['MA_200D'] = df_spy['Adj Close'].rolling(200).mean()
    df_uem = dfs['UEM']

    output = pd.DataFrame()
    balance = 10000  # initial_balance

    # Risk Control #1
    risky_asset_df, minus_dropdown = pause_and_cash_hold(risky_asset_df)
    minus_dropdown_dates = minus_dropdown['DATE'].tolist()
    invest_dates = [initial_invest_date] + minus_dropdown_dates + rebalancing_dates
    invest_dates_sort = sorted(invest_dates)

    prev_transaction = dict()
    risky_quantity = 0
    risky_price = 0

    for invest_date in invest_dates_sort:
        # Risk Control #2
        risky_ratio, mtm_score_cnt = avg_momentum_score(risky_asset_df, invest_date)
        # Risk Control #3
        target_ticker = rebalancing_criterias_uem(df_spy, df_uem, invest_date)

        risky_price = risky_asset_df.loc[risky_asset_df['DATE'] == invest_date, 'Adj Close'].item()

        if invest_date == initial_invest_date:
            risky_balance = 0.5 * balance
            cash_balance = 0.5 * balance
            risky_quantity = round(risky_balance / risky_price, 2)
        else:
            balance = risky_price * prev_transaction['RISK_Q'] + prev_transaction['CASH_EQ_BALANCE']

            if invest_date in minus_dropdown_dates:
                risky_balance = 0
                risky_quantity = 0
                cash_balance = balance
            else:
                if target_ticker != 'SHY':
                    risky_balance = risky_ratio * balance
                    cash_balance = (1 - risky_ratio) * balance
                    risky_quantity = round(risky_balance / risky_price, 2)
                else:
                    risky_balance = 0
                    risky_quantity = 0
                    cash_balance = balance

        prev_transaction['RISK_Q'] = risky_quantity
        prev_transaction['RISK_P'] = risky_price
        prev_transaction['BALANCE'] = balance
        prev_transaction['CASH_EQ_BALANCE'] = cash_balance

        output_dict = {'DATE': invest_date, 'CASH_EQ_BALANCE': cash_balance, 'RISK_Q': risky_quantity,
                       'RISK_P': risky_price, 'RISK_BALANCE': risky_balance, 'AVG_MTM': risky_ratio,
                       'MTM_CNT': mtm_score_cnt, 'TARGET': target_ticker, 'TOTAL': balance}
        output = output.append(output_dict, ignore_index=True)

    output.to_excel('./portfolio/soxx-x3-risk-control.xlsx', sheet_name='soxx_x3', index=False)
    graph_cagr_mdd(output, 'soxx-x3-risk-control.png')
