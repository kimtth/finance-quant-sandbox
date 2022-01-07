import os
import pandas as pd
from pandas import ExcelWriter


def gr_mdd(gr_df):
    dfs = list()
    for idx, df in gr_df:
        # print(df)
        df['PCT_CHANGE'] = df['Adj Close'].pct_change()
        df['DAY_RETURN (%)'] = df['PCT_CHANGE'] * 100
        df['DAY_RETURN (%)'] = df['DAY_RETURN (%)'].round(2)
        df['CUM_RETURN'] = (1 + df['PCT_CHANGE']).cumprod() - 1
        df['DRAWDOWN'] = (-(df['Adj Close'].cummax() - df['Adj Close']) / df['Adj Close'].cummax()) * 100
        df['DRAWDOWN (%)'] = df['DRAWDOWN'].round(2)
        df = df[['DATE', 'YEAR', 'YEAR_MM', 'Adj Close', 'PCT_CHANGE', 'DAY_RETURN (%)', 'CUM_RETURN', 'DRAWDOWN']]

        dfs.append(df)

    re_gr_df = pd.concat(dfs)
    re_gr_df = re_gr_df.reset_index(drop=True)
    re_gr_df['PCT_CHANGE_ALL_TIME'] = re_gr_df['Adj Close'].pct_change()
    re_gr_df['CUM_RETURN_ALL_TIME'] = (1 + re_gr_df['PCT_CHANGE_ALL_TIME']).cumprod() - 1

    return re_gr_df


def gr_data_mdd():
    porfpolio_tickers = ['^SOXSIMx3', 'SOXX', 'SOXL']
    xls = pd.ExcelFile(os.path.abspath('./portfolio/NASDAQ-SP-QQQ-data.xlsx'))
    dfs = dict()
    for sheet in xls.sheet_names:
        if sheet in porfpolio_tickers:
            df = pd.read_excel('./portfolio/NASDAQ-SP-QQQ-data.xlsx', sheet_name=sheet)  # index_col='DATE',
            dfs[sheet] = df

    df_soxx = dfs['^SOXSIMx3']
    dict_df = dict()

    gr_df_from_2000 = df_soxx.groupby('YEAR', as_index=False)
    df_soxx_from_2008 = df_soxx[df_soxx['YEAR'] >= 2008]
    gr_df_from_2008 = df_soxx_from_2008.groupby('YEAR', as_index=False)
    df_soxx_from_2010 = df_soxx[df_soxx['YEAR_MM'] >= 201003]
    gr_df_from_2010 = df_soxx_from_2010.groupby('YEAR', as_index=False)

    dict_df['sox3dotbubble'] = gr_mdd(gr_df_from_2000)
    dict_df['sox3lehman'] = gr_mdd(gr_df_from_2008)
    dict_df['sox3release'] = gr_mdd(gr_df_from_2010)

    writer = ExcelWriter('./portfolio/soxlsimx3-yearly-performance.xlsx')
    for key in dict_df:
        if isinstance(dict_df[key], pd.DataFrame):
            df: pd.DataFrame = dict_df[key]
            df.to_excel(writer, sheet_name=key, index=False)

    writer.save()


if __name__ == '__main__':
    gr_data_mdd()
