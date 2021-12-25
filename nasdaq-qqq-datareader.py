import os.path
from datetime import datetime
import pandas as pd
import pandas_datareader as pdr


def get_price_data(ticker, start, end):
    df = pdr.get_data_yahoo(ticker, start, end)  # ['Adj Close']

    df['DATE'] = df.index
    df['YEAR'] = df['DATE'].dt.strftime('%Y').astype(str)
    df['YEAR_MONTH'] = df['DATE'].dt.strftime('%Y%m').astype(str)
    df['PCT_CHANGE'] = df['Adj Close'].pct_change()
    df['PCT_CHANGE (%)'] = df['PCT_CHANGE'] * 100
    df['PCT_CHANGE (%)'] = df['PCT_CHANGE (%)'].round(2)

    df['MA_200D'] = df['Adj Close'].rolling(200).mean()
    df['MA_12M'] = df['Adj Close'].rolling(12).mean()
    df['DRAWDOWN'] = (-(df['Adj Close'].cummax() - df['Adj Close']) / df['Adj Close'].cummax()) * 100
    df['DRAWDOWN (%)'] = df['DRAWDOWN'].round(2)

    index_order = ['DATE', 'YEAR', 'YEAR_MONTH'] + [index for index in list(df.columns.values) if
                                                    index not in ['DATE', 'YEAR', 'YEAR_MONTH']]
    df = df[index_order]
    df = df.reset_index(drop=True)

    return df


def dfs_to_excel():
    # ['^IXIC', '^DJI', '^GSPC'] NASDAQ, DOW JONES, S&P
    target = ['^IXIC', 'QQQ', 'TQQQ', 'TECL', '^GSPC']
    start = datetime(2000, 1, 1)
    end = datetime(datetime.now().year, datetime.now().month, datetime.now().day)
    writer = pd.ExcelWriter('NASDAQ-SP-QQQ-data.xlsx', engine='xlsxwriter')

    dfs = dict()
    for ticker in target:
        df = get_price_data(ticker, start, end)
        dfs[ticker] = df

    for sheet, frame in dfs.items():  # .use .items for python 3.X
        frame.to_excel(writer, sheet_name=sheet, index=False)

    writer.save()


if __name__ == '__main__':
    dfs_to_excel()
    '''
    xls = pd.ExcelFile(os.path.abspath('QQQ-data.xlsx'))

    dfs = []
    for sheet in xls.sheet_names:
        print(sheet)
        df = pd.read_excel('QQQ-data.xlsx', index_col='DATE', sheet_name=sheet)
        dfs.append(df)

    print("sss")
    print(dfs)
    '''
