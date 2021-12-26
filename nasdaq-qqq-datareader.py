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
    df['DAILY_RETURN (%)'] = df['PCT_CHANGE'] * 100
    df['DAILY_RETURN (%)'] = df['DAILY_RETURN (%)'].round(2)
    df['CUMLUATIVE_RETURN'] = np.exp(np.log1p(df['PCT_CHANGE'])).cumsum()

    df['MA_200D'] = df['Adj Close'].rolling(200).mean()
    df['MA_12M'] = df['Adj Close'].rolling(12).mean()
    df['DRAWDOWN'] = (-(df['Adj Close'].cummax() - df['Adj Close']) / df['Adj Close'].cummax()) * 100
    df['DRAWDOWN (%)'] = df['DRAWDOWN'].round(2)

    column_order = ['DATE', 'YEAR', 'YEAR_MM'] + [col for col in list(df.columns.values) if
                                                  col not in ['DATE', 'YEAR', 'YEAR_MM']]
    df = df[column_order]
    df = df.drop(['High', 'Low', 'Open', 'Close', 'Volume'], axis=1)
    df = df.reset_index(drop=True)

    return df


def dfs_to_excel(targets):
    start = datetime(2000, 1, 1)
    end = datetime(datetime.now().year, datetime.now().month, datetime.now().day)
    writer = pd.ExcelWriter('NASDAQ-SP-QQQ-data.xlsx', engine='xlsxwriter')

    dfs = dict()
    for ticker in targets:
        df = get_price_data(ticker, start, end)
        dfs[ticker] = df

    for sheet, frame in dfs.items():  # .use .items for python 3.X
        frame.to_excel(writer, sheet_name=sheet, index=False)

    writer.save()


if __name__ == '__main__':
    # ['^IXIC', '^DJI', '^GSPC'] NASDAQ, DOW JONES, S&P
    # targets = ['^IXIC', 'QQQ', 'TQQQ', 'TECL', '^GSPC', 'SPXL', 'SOXX', 'SOXL', 'SMH']
    # dfs_to_excel(targets)

    xls = pd.ExcelFile(os.path.abspath('QQQ-data.xlsx'))

    dfs = []
    for sheet in xls.sheet_names:
        print(sheet)
        df = pd.read_excel('QQQ-data.xlsx', index_col='DATE', sheet_name=sheet)
        dfs.append(df)

    print("sss")
    # print(dfs)

    df_soxx = dfs['SOXX']
