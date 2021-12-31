# -*- coding: utf-8 -*-
"""
Created on Tue Dec  7 21:39:53 2021

@author: PlayGround
"""
import os

import pandas as pd
import pandas_datareader as pdr
from datetime import datetime
import math
import numpy as np
import seaborn
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

plt.rcParams["figure.figsize"] = (10, 10)
pd.options.mode.chained_assignment = None


def data_formatter(df):
    df['DATE'] = df.index
    # @Debug: print(df.dtypes) # df.info()
    df['YEAR'] = df['DATE'].dt.strftime('%Y').astype(str)
    df['YEAR_MONTH'] = df['DATE'].dt.strftime('%Y%m').astype(str)
    df = df.reset_index(drop=True)

    return df


def get_price_data(tickers, start, end):
    df = pd.DataFrame(columns=tickers)

    for ticker in tickers:
        df[ticker] = pdr.get_data_yahoo(ticker, start, end)['Adj Close']

    df = data_formatter(df)

    return df


def get_unemployment(start, end):
    df_unemployment = pdr.DataReader('UNRATE', 'fred', start, end)
    df_unemployment = df_unemployment.rename(columns={'UNRATE': 'UNEMPLOYMENT_RATE'})
    # @Tip: df_unemployment['UEM_CHANGE'] = df_unemployment['UNEMPLOYMENT_RATE'] - df_unemployment[
    # 'UNEMPLOYMENT_RATE'].shift(1)
    df_unemployment['UEM_CHANGE'] = df_unemployment['UNEMPLOYMENT_RATE'].pct_change()
    return df_unemployment


def select_dual_momentum(spy_m12_return, bil_m12_return, efa_m12_return):
    if spy_m12_return > bil_m12_return:
        if spy_m12_return > efa_m12_return:
            return 'SPY'
        else:
            return 'EFA'
    else:
        return 'AGG'


def select_qqq_or_shy(spy_index, spy_ma_200d, uem_index, uem_12m):
    if spy_index < spy_ma_200d and uem_index > uem_12m:
        return 'SHY'
    else:
        return 'QQQ'


def asset_data(start, end):
    tickers_laa = ['SPY', 'GLD', 'IEF', 'IWD', 'QQQ', 'SHY', 'SMH']
    tickers_dual_momentum = ['SPY', 'EFA', 'AGG', 'BIL']

    df_asset_laa = get_price_data(tickers_laa, start, end)
    df_asset_dual = get_price_data(tickers_dual_momentum, start, end)
    uem = get_unemployment(start, end)
    uem_monthly = data_formatter(uem)

    return df_asset_laa, df_asset_dual, uem_monthly


def laa_backtest(df_asset_laa, uem_monthly):
    # LAA
    '''
    월말 리밸런싱을 가정.

    LAA
    고정자산: 미국 대형가치주 IWD, 금 GLD, 미국 중기국채 IEF
    타이밍 자산: 나스닥 QQQ, 미국 단기국채 SHY
    자산의 각 25%를 IWD, GLD, IEF에 투자
    나머지 25%는 QQQ 또는 SHY 에 투자.
     미국 S&P 500 지수 가격이 200일 이동평균보다 낮고 미국 실업률이 12개월 이동평균보다 높은 경우 SHY에 투자.
     그럴지 않을 경우 QQQ 투자
    연1회: 고정자산
    월1회: 타이밍 자산
    '''
    # @Tip: as_index=False -> Don't lose join column
    df_asset_laa_monthly = df_asset_laa.groupby('YEAR_MONTH', as_index=False).last().dropna()
    df_asset_laa_yearly = df_asset_laa_monthly.groupby('YEAR', as_index=False).last().dropna()

    df_spy = df_asset_laa[['SPY', 'DATE']]
    df_spy['MA_200D'] = df_spy.loc[:, 'SPY'].rolling(200).mean()
    df_spy = df_spy.dropna()

    df_uem = uem_monthly[['UNEMPLOYMENT_RATE', 'UEM_CHANGE', 'DATE', 'YEAR_MONTH', 'YEAR']]
    df_uem['MA_12M'] = df_uem.loc[:, 'UNEMPLOYMENT_RATE'].rolling(12).mean()
    df_uem = df_uem.dropna()

    rebalancing_yearly_dates = df_asset_laa_yearly['DATE'].tolist()
    rebalancing_monthly_dates = df_asset_laa_monthly['DATE'].tolist()
    rebalancing_monthly_spy_ma_200d = df_spy.loc[df_spy['DATE'].isin(rebalancing_monthly_dates)]

    begin_date_of_investment = rebalancing_monthly_dates[0]
    budget = 10000  # USD

    prev_cash_amount = 0
    prev_iwd_quantity = prev_gld_quantity = prev_ief_quantity = prev_qqq_or_shy_quantity = qqq_or_shy_quantity = 0
    prev_qqq_or_shy_price = remain_amount = 0
    prev_target_ticker = ''

    df_rebalancing_target = df_asset_laa[['IWD', 'GLD', 'IEF', 'QQQ', 'SHY', 'DATE']]
    output = pd.DataFrame()

    rebalancing_yearly_dates = [begin_date_of_investment] + rebalancing_yearly_dates
    iwd_quantity = gld_quantity = ief_quantity = 0
    iwd_amount = gld_amount = ief_amount = 0

    for date in rebalancing_monthly_dates:
        # @Tip: print(type(date), date)  # <class 'pandas._libs.tslibs.timestamps.Timestamp'> 2009-01-30 00:00:00
        df_price = df_rebalancing_target[df_rebalancing_target['DATE'] == date]

        spy_price_ma = rebalancing_monthly_spy_ma_200d[rebalancing_monthly_spy_ma_200d['DATE'] == date]
        # @Tip: .dt is needed when it's a group of data, if it's only one element you don't need .dt
        df_uem['YEAR'] = df_uem.loc[:, 'YEAR'].astype(str)
        df_uem['YEAR_MONTH'] = df_uem.loc[:, 'YEAR_MONTH'].astype(str)
        year_month_str = str(date.year_month) + str(date.month).zfill(2)
        uem_target = df_uem[
            (df_uem['YEAR'] == str(date.year_month)) & (df_uem['YEAR_MONTH'] == str(
                year_month_str))]

        if uem_target.shape[0] == 0:
            # print('UEM {} EMPTY'.format(date))
            continue

        iwd_price = df_price['IWD'].item()
        gld_price = df_price['GLD'].item()
        ief_price = df_price['IEF'].item()

        spy_index = spy_price_ma['SPY'].item()
        spy_ma_200d = spy_price_ma['MA_200D'].item()
        uem_index = uem_target['UNEMPLOYMENT_RATE'].item()
        uem_12m = uem_target['MA_12M'].item()
        target_ticker = select_qqq_or_shy(spy_index, spy_ma_200d, uem_index, uem_12m)
        qqq_or_shy_price = df_price[target_ticker].item()

        # IWD or GLD or IEF - Yearly ReBalancing
        if date in rebalancing_yearly_dates:
            if prev_qqq_or_shy_quantity == 0:
                allocation = budget / 4
            else:
                budget = ((prev_iwd_quantity * iwd_price) + (prev_gld_quantity * gld_price) + (
                        prev_ief_quantity * ief_price) + (prev_qqq_or_shy_quantity * qqq_or_shy_price)
                          + prev_cash_amount)
                allocation = budget / 4

            iwd_quantity = int(allocation / iwd_price)
            gld_quantity = int(allocation / gld_price)
            ief_quantity = int(allocation / ief_price)
            qqq_or_shy_quantity = int(allocation / qqq_or_shy_price)

            iwd_amount = iwd_price * iwd_quantity
            gld_amount = gld_price * gld_quantity
            ief_amount = ief_price * ief_quantity
            qqq_or_shy_amount = qqq_or_shy_price * qqq_or_shy_quantity

            prev_qqq_or_shy_quantity, prev_qqq_or_shy_price = qqq_or_shy_quantity, qqq_or_shy_price
            prev_iwd_quantity, prev_gld_quantity, prev_ief_quantity = iwd_quantity, gld_quantity, ief_quantity
            remain_amount = budget - sum([iwd_amount, gld_amount, ief_amount, qqq_or_shy_amount])
            prev_cash_amount = remain_amount
        else:
            # QQQ or SHY - Monthly ReBalancing
            iwd_amount = iwd_price * prev_iwd_quantity
            gld_amount = gld_price * prev_gld_quantity
            ief_amount = ief_price * prev_ief_quantity

            qqq_or_shy_price = df_price[target_ticker].item()
            if target_ticker == prev_target_ticker:
                qqq_or_shy_amount = prev_qqq_or_shy_quantity * qqq_or_shy_price
            else:
                qqq_or_shy_allocation = prev_qqq_or_shy_quantity * prev_qqq_or_shy_price
                qqq_or_shy_quantity = int(qqq_or_shy_allocation / qqq_or_shy_price)
                qqq_or_shy_amount = qqq_or_shy_quantity * qqq_or_shy_price  # qqq_or_shy_allocation

                prev_qqq_or_shy_quantity, prev_qqq_or_shy_price = qqq_or_shy_quantity, qqq_or_shy_price

        prev_target_ticker = target_ticker

        # Store Result
        price_dict = {'IWD_P': iwd_price, 'GLD_P': gld_price, 'IEF_P': ief_price,
                      'QQQ_SHY_P': qqq_or_shy_price}
        quantity_dict = {'IWD_Q': iwd_quantity, 'GLD_Q': gld_quantity, 'IEF_Q': ief_quantity,
                         'QQQ_SHY_Q': qqq_or_shy_quantity}
        amount_dict = {'IWD': iwd_amount, 'GLD': gld_amount, 'IEF': ief_amount, 'QQQ_SHY': qqq_or_shy_amount,
                       'CASH': remain_amount}

        output_dict = {'DATE': date, **price_dict, **quantity_dict, **amount_dict,
                       'BUDGET': sum([iwd_amount, gld_amount, ief_amount, qqq_or_shy_amount, remain_amount]),
                       'TARGET': target_ticker,
                       'TOTAL': sum([iwd_amount, gld_amount, ief_amount, qqq_or_shy_amount])}
        output = output.append(output_dict, ignore_index=True)

        # print(date, 'TOTAL:', sum([iwd_amount, gld_amount, ief_amount, qqq_or_shy_amount]), ',',
        #      ', '.join([':'.join([str(k), str(v)]) for k, v in amount_dict.items()]))

    return output


def dual_momentum_backtest(df_asset_dual):
    # Dual Momentum
    '''
     매월 말 미국 주식 SPY, 선진국 주식 EFA, 초단기채권 BIL의 최근 12개월 수익률을 계산
     SPY 수익률이 BIL 보다 높으면 SPY 또는 EFA 중 최근 12개월 수익률이 더 높은 ETF에 투자
     SPY 수익률이 BIL 보다 낮으면 미국채권 AGG에 투자
     월 1회 리밸런싱
    '''
    df_asset_dual_monthly = df_asset_dual.groupby('YEAR_MONTH', as_index=False).last()
    rebalancing_monthly_dates = df_asset_dual_monthly['DATE'].tolist()
    initial_buget = 10000  # USD
    prev_spy_or_bil_or_efa_quantity = prev_spy_or_bil_or_efa_price = 0
    prev_target_ticker = ''
    df_asset = pd.DataFrame()

    for date in rebalancing_monthly_dates:
        try:
            date_1yr_ago = datetime(date.year_month - 1, date.month, date.day)
            # @Debug: print(type(date), type(date_1yr_ago), date, date_1yr_ago)
        except ValueError:
            # @Tip: e.g. 2012-02-29 00:00:00 2011-02-28 00:00:00
            #       date.day-1 : ValueError: day is out of range for month
            date_1yr_ago = datetime(date.year_month - 1, date.month, date.day - 1)
            # @Debug: print(type(date_1yr_ago), date, date_1yr_ago)
            pass

        date_1yr_ago_adjust_range = datetime(date.year_month - 1, date.month, date.day - 5)
        date_df = df_asset_dual[df_asset_dual['DATE'] == date]
        # @Tip: df.iloc[-1] == df.iloc[-1:] == df.tail(1)
        date_1yr_ago_df = df_asset_dual[
            (df_asset_dual['DATE'] > date_1yr_ago_adjust_range) & (df_asset_dual['DATE'] <= date_1yr_ago)].tail(1)

        if len(date_1yr_ago_df) > 0:
            spy_m12_return = float(date_df['SPY'].item()) / float(date_1yr_ago_df['SPY'].item()) - 1
            bil_m12_return = float(date_df['BIL'].item()) / float(date_1yr_ago_df['BIL'].item()) - 1
            efa_m12_return = float(date_df['EFA'].item()) / float(date_1yr_ago_df['EFA'].item()) - 1

            # @Debug: print(spy_m12_return, bil_m12_return, efa_m12_return)
            target_ticker = select_dual_momentum(spy_m12_return, bil_m12_return, efa_m12_return)

            spy_or_bil_or_efa_price = date_df[target_ticker].item()
            if prev_spy_or_bil_or_efa_quantity == 0:
                spy_or_bil_or_efa_allocation = initial_buget
            else:
                if prev_target_ticker == target_ticker:
                    spy_or_bil_or_efa_allocation = prev_spy_or_bil_or_efa_quantity * spy_or_bil_or_efa_price
                else:
                    spy_or_bil_or_efa_allocation = prev_spy_or_bil_or_efa_quantity * prev_spy_or_bil_or_efa_price

            spy_or_bil_or_efa_quantity = int(spy_or_bil_or_efa_allocation / spy_or_bil_or_efa_price)
            # print(date, ':', target_ticker, ':', spy_or_bil_or_efa_price * spy_or_bil_or_efa_quantity)
            prev_spy_or_bil_or_efa_quantity, prev_spy_or_bil_or_efa_price = spy_or_bil_or_efa_quantity, spy_or_bil_or_efa_price
            prev_target_ticker = target_ticker

            output_dict = {'DATE': date, 'BUDGET': spy_or_bil_or_efa_allocation,
                           'TARGET': target_ticker, 'PRICE': spy_or_bil_or_efa_price,
                           'QUANTITY': prev_spy_or_bil_or_efa_quantity,
                           'TOTAL': spy_or_bil_or_efa_price * spy_or_bil_or_efa_quantity}
            df_asset = df_asset.append(output_dict, ignore_index=True)

    return df_asset


def laa_variant_qqq_backtest(df_asset_laa, uem_monthly):
    '''
    월말 리밸런싱을 가정.

    QQQ 또는 SHY 에 투자.
     미국 S&P 500 지수 가격이 200일 이동평균보다 낮고 미국 실업률이 12개월 이동평균보다 높은 경우 SHY에 투자.
     그럴지 않을 경우 QQQ 투자
    월1회
    '''
    # @Tip: as_index=False -> Don't lose join column
    df_asset_laa_monthly = df_asset_laa.groupby('YEAR_MONTH', as_index=False).last().dropna()
    df_spy = df_asset_laa[['SPY', 'DATE']]
    df_spy['MA_200D'] = df_spy.loc[:, 'SPY'].rolling(200).mean()
    df_spy['SPY'] = df_spy['SPY'].dropna()

    df_uem = uem_monthly[['UNEMPLOYMENT_RATE', 'UEM_CHANGE', 'DATE', 'YEAR_MONTH', 'YEAR']]
    df_uem['MA_12M'] = df_uem.loc[:, 'UNEMPLOYMENT_RATE'].rolling(12).mean()
    df_uem[['UNEMPLOYMENT_RATE']] = df_uem[['UNEMPLOYMENT_RATE']].dropna()

    rebalancing_monthly_dates = df_asset_laa_monthly['DATE'].tolist()
    rebalancing_monthly_spy_ma_200d = df_spy.loc[df_spy['DATE'].isin(rebalancing_monthly_dates)]

    budget = 10000  # USD
    prev_qqq_or_shy_price = prev_remain_cash_amount = qqq_or_shy_allocation = 0
    prev_target_ticker = ''
    prev_qqq_or_shy_quantity = 0

    df_rebalancing_target = df_asset_laa[['QQQ', 'SHY', 'DATE']]
    output = pd.DataFrame()

    for date in rebalancing_monthly_dates:
        # @Tip: print(type(date), date)  # <class 'pandas._libs.tslibs.timestamps.Timestamp'> 2009-01-30 00:00:00
        df_price = df_rebalancing_target[df_rebalancing_target['DATE'] == date]

        spy_price_ma = rebalancing_monthly_spy_ma_200d[rebalancing_monthly_spy_ma_200d['DATE'] == date]
        # @Tip: .dt is needed when it's a group of data, if it's only one element you don't need .dt
        df_uem['YEAR'] = df_uem.loc[:, 'YEAR'].astype(str)
        df_uem['YEAR_MONTH'] = df_uem.loc[:, 'YEAR_MONTH'].astype(str)
        year_month_str = str(date.year_month) + str(date.month).zfill(2)
        uem_target = df_uem[
            (df_uem['YEAR'] == str(date.year_month)) & (df_uem['YEAR_MONTH'] == str(
                year_month_str))]

        if uem_target.shape[0] == 0:
            print('UEM {} EMPTY'.format(date))
            continue

        spy_index = spy_price_ma['SPY'].item()
        spy_ma_200d = spy_price_ma['MA_200D'].item()
        uem_index = uem_target['UNEMPLOYMENT_RATE'].item()
        uem_12m = uem_target['MA_12M'].item()
        target_ticker = select_qqq_or_shy(spy_index, spy_ma_200d, uem_index, uem_12m)

        # Yearly ReBalancing
        # QQQ or SHY - Monthly ReBalancing
        qqq_or_shy_price = df_price[target_ticker].item()
        if qqq_or_shy_allocation == 0:
            qqq_or_shy_allocation = budget
        elif target_ticker == prev_target_ticker:
            qqq_or_shy_allocation = prev_qqq_or_shy_quantity * qqq_or_shy_price + prev_remain_cash_amount
        else:
            qqq_or_shy_allocation = prev_qqq_or_shy_quantity * prev_qqq_or_shy_price + prev_remain_cash_amount

        qqq_or_shy_quantity = int(qqq_or_shy_allocation / qqq_or_shy_price)
        qqq_or_shy_amount = qqq_or_shy_price * qqq_or_shy_quantity
        remain_cash_amount = qqq_or_shy_allocation - qqq_or_shy_amount

        prev_qqq_or_shy_quantity, prev_qqq_or_shy_price, prev_remain_cash_amount = qqq_or_shy_quantity, qqq_or_shy_price, remain_cash_amount
        prev_target_ticker = target_ticker

        # Store Result
        price_dict = {'BUDGET': qqq_or_shy_allocation, 'QQQ_SHY_P': qqq_or_shy_price}
        quantity_dict = {'QQQ_SHY_Q': qqq_or_shy_quantity}
        amount_dict = {'QQQ_SHY': qqq_or_shy_amount, 'CASH': remain_cash_amount}

        output_dict = {'DATE': date, **price_dict, **quantity_dict, **amount_dict, 'TARGET': target_ticker,
                       'TOTAL': sum([qqq_or_shy_amount])}
        output = output.append(output_dict, ignore_index=True)

    return output


def laa_variant_smh_backtest(df_asset_laa, uem_monthly):
    '''
    월말 리밸런싱을 가정.

    SMH 또는 SHY 에 투자.
     미국 S&P 500 지수 가격이 200일 이동평균보다 낮고 미국 실업률이 12개월 이동평균보다 높은 경우 SHY에 투자.
     그럴지 않을 경우 SMH 투자
    월1회
    '''
    # @Tip: as_index=False -> Don't lose join column
    df_asset_laa_monthly = df_asset_laa.groupby('YEAR_MONTH', as_index=False).last().dropna()
    df_spy = df_asset_laa[['SPY', 'DATE']]
    df_spy['MA_200D'] = df_spy.loc[:, 'SPY'].rolling(200).mean()
    df_spy['SPY'] = df_spy['SPY'].dropna()

    df_uem = uem_monthly[['UNEMPLOYMENT_RATE', 'UEM_CHANGE', 'DATE', 'YEAR_MONTH', 'YEAR']]
    df_uem['MA_12M'] = df_uem.loc[:, 'UNEMPLOYMENT_RATE'].rolling(12).mean()
    df_uem[['UNEMPLOYMENT_RATE']] = df_uem[['UNEMPLOYMENT_RATE']].dropna()

    rebalancing_monthly_dates = df_asset_laa_monthly['DATE'].tolist()
    rebalancing_monthly_spy_ma_200d = df_spy.loc[df_spy['DATE'].isin(rebalancing_monthly_dates)]

    budget = 10000  # USD
    prev_smh_or_shy_price = prev_remain_cash_amount = smh_or_shy_allocation = 0
    prev_target_ticker = ''
    prev_smh_or_shy_quantity = 0

    df_rebalancing_target = df_asset_laa[['SMH', 'SHY', 'DATE']]
    output = pd.DataFrame()

    for date in rebalancing_monthly_dates:
        # @Tip: print(type(date), date)  # <class 'pandas._libs.tslibs.timestamps.Timestamp'> 2009-01-30 00:00:00
        df_price = df_rebalancing_target[df_rebalancing_target['DATE'] == date]

        spy_price_ma = rebalancing_monthly_spy_ma_200d[rebalancing_monthly_spy_ma_200d['DATE'] == date]
        # @Tip: .dt is needed when it's a group of data, if it's only one element you don't need .dt
        df_uem['YEAR'] = df_uem.loc[:, 'YEAR'].astype(str)
        df_uem['YEAR_MONTH'] = df_uem.loc[:, 'YEAR_MONTH'].astype(str)
        year_month_str = str(date.year_month) + str(date.month).zfill(2)
        uem_target = df_uem[
            (df_uem['YEAR'] == str(date.year_month)) & (df_uem['YEAR_MONTH'] == str(
                year_month_str))]

        if uem_target.shape[0] == 0:
            print('UEM {} EMPTY'.format(date))
            continue

        spy_index = spy_price_ma['SPY'].item()
        spy_ma_200d = spy_price_ma['MA_200D'].item()
        uem_index = uem_target['UNEMPLOYMENT_RATE'].item()
        uem_12m = uem_target['MA_12M'].item()
        target_ticker = select_qqq_or_shy(spy_index, spy_ma_200d, uem_index, uem_12m)

        if target_ticker == 'QQQ':
            target_ticker = 'SMH'

        # Yearly ReBalancing
        # SMH or SHY - Monthly ReBalancing
        smh_or_shy_price = df_price[target_ticker].item()
        if smh_or_shy_allocation == 0:
            smh_or_shy_allocation = budget
        elif target_ticker == prev_target_ticker:
            smh_or_shy_allocation = prev_smh_or_shy_quantity * smh_or_shy_price + prev_remain_cash_amount
        else:
            smh_or_shy_allocation = prev_smh_or_shy_quantity * prev_smh_or_shy_price + prev_remain_cash_amount

        smh_or_shy_quantity = int(smh_or_shy_allocation / smh_or_shy_price)
        smh_or_shy_amount = smh_or_shy_price * smh_or_shy_quantity
        remain_cash_amount = smh_or_shy_allocation - smh_or_shy_amount

        prev_smh_or_shy_quantity, prev_smh_or_shy_price, prev_remain_cash_amount = smh_or_shy_quantity, smh_or_shy_price, remain_cash_amount
        prev_target_ticker = target_ticker

        # Store Result
        price_dict = {'BUDGET': smh_or_shy_allocation, 'SMH_SHY_P': smh_or_shy_price}
        quantity_dict = {'SMH_SHY_Q': smh_or_shy_quantity}
        amount_dict = {'SMH_SHY': smh_or_shy_amount, 'CASH': remain_cash_amount}

        output_dict = {'DATE': date, **price_dict, **quantity_dict, **amount_dict, 'TARGET': target_ticker,
                       'TOTAL': sum([smh_or_shy_amount])}
        output = output.append(output_dict, ignore_index=True)

    return output


def graph_cagr_mdd(df_asset, file_name='output'):
    trade_month = round(len(df_asset.index) / 12, 2)

    ## CAGR 계산
    if df_asset['TOTAL'].iat[0] != float(0):
        total_profit = (df_asset['TOTAL'].iat[-1] / df_asset['TOTAL'].iat[0])
        cagr = round((total_profit ** (1 / trade_month) - 1) * 100, 2)

        ## MDD 계산
        df_asset['DRAWDOWN'] = (-(df_asset['TOTAL'].cummax() - df_asset['TOTAL']) / df_asset['TOTAL'].cummax()) * 100
        df_asset['YEAR'] = df_asset['DATE'].dt.strftime('%Y%m').astype(str)

        print('MM_PERIOD', trade_month, 'CAGR', cagr, 'MDD', df_asset['DRAWDOWN'].min())

        fig, axs = plt.subplots(2)

        plt.xlabel('xlabel', fontsize=4)
        plt.xticks(fontsize=8)

        xtick_label = list()
        xtick_label.append(df_asset.index[0])
        xtick_label.extend(list(df_asset.index[::6]))
        xtick_label.append(df_asset.index[-1])

        axs[0].set_xticks(xtick_label)
        axs[0].set_xticklabels(xtick_label)
        seaborn.lineplot(data=df_asset, x=df_asset.index, y=df_asset['TOTAL'], ax=axs[0], linewidth=2.5)

        xtick_label = list()  # freq 6 months + with first and last date
        xtick_label.append(df_asset['DATE'].head(1).item())
        xtick_label.extend(list(df_asset['DATE'][::6]))
        xtick_label.append(df_asset['DATE'].tail(1).item())

        axs[1].set_xticks(xtick_label)
        axs[1].set_xticklabels(xtick_label)  # ax2.set_xticklabels(x[::2], rotation=45)
        axs[1].xaxis.set_major_formatter(DateFormatter("%Y%m"))
        seaborn.lineplot(data=df_asset, x=df_asset['DATE'], y=df_asset['DRAWDOWN'], ax=axs[1], linewidth=2.5)

        fig.autofmt_xdate()
        plt.savefig(file_name, dpi=400)
        # plt.show()


if __name__ == '__main__':
    # @Tip: BIL beginning date 2007/05/30
    #       GLD beginning date 2004/11/18
    start = datetime(2007, 5, 30)
    end = datetime(datetime.now().year, datetime.now().month, datetime.now().day)
    df_asset_laa, df_asset_dual, uem_monthly = asset_data(start, end)

    print('LAA -- START')
    df_output = laa_backtest(df_asset_laa, uem_monthly)
    df_output = df_output[df_output['TOTAL'] != 0]
    graph_cagr_mdd(df_output, 'LAA_output.png')
    filename = 'laa-output-' + datetime.now().strftime("%Y%m%d-%H%M%S") + '.xlsx'
    df_output.to_excel('.' + os.sep + filename, sheet_name='rtn')
    print('LAA -- END')

    print('UEM QQQ -- START')
    df_output = laa_variant_qqq_backtest(df_asset_laa, uem_monthly)
    graph_cagr_mdd(df_output, 'UEM_QQQ_output.png')
    filename = 'laa-variant-output-' + datetime.now().strftime("%Y%m%d-%H%M%S") + '.xlsx'
    df_output.to_excel('.' + os.sep + filename, sheet_name='rtn')
    print('UEM QQQ -- END')

    print('DUAL MOMENTUM -- START')
    df_output = dual_momentum_backtest(df_asset_dual)
    filename = 'dual-mtum-output-' + datetime.now().strftime("%Y%m%d-%H%M%S") + '.xlsx'
    df_output.to_excel('.' + os.sep + filename, sheet_name='rtn')
    graph_cagr_mdd(df_output, 'DUAL_MTM_output.png')
    print('DUAL MOMENTUM -- END')

    print('UEM SMH -- START')
    df_output = laa_variant_smh_backtest(df_asset_laa, uem_monthly)
    graph_cagr_mdd(df_output, 'UEM_SMH_output.png')
    filename = 'smh-variant-output-' + datetime.now().strftime("%Y%m%d-%H%M%S") + '.xlsx'
    df_output.to_excel('.' + os.sep + filename, sheet_name='rtn')
    print('UEM SMH -- END')
