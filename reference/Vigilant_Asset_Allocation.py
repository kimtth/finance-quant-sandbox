# -*- coding: utf-8 -*-
"""
Created on Sun Dec  5 10:57:11 2021

@author: PlayGround

https://jacobjinwonlee.github.io/assetallocation/2021/06/06/assetallocation-strategy-vaa/
"""

import pandas as pd
import pandas_datareader as pdr # pip install pandas_datareader
from datetime import datetime, timedelta
# import backtrader as bt
import numpy as np
# %matplotlib inline
import matplotlib.pyplot as plt
# import pyfolio as pf
import quantstats # pip install quantstats
import math
import seaborn
plt.rcParams["figure.figsize"] = (10, 6) # (w, h)

# 공격 자산: SPY (S&P 500), EFA (MSCI EAFE), EEM (Emerging), AGG (Aggregate US Bond) 
# 방어 자산: LQD (Investment Grade Corporate Bond), IEF (US 7-10 Year Treausry), SHY (US 1-3 Year Treasury)

# AGG starts: 2003-09-29
start = datetime(2003,10,1)
end = datetime(2021,5,31)

tickers = ['SPY','EFA','EEM','AGG','LQD','SHY','IEF']

def get_price_data(tickers):
    df_asset = pd.DataFrame(columns=tickers)
    
    for ticker in tickers:
        df_asset[ticker] = pdr.get_data_yahoo(ticker, start, end)['Adj Close']  
         
    return df_asset

df_asset = get_price_data(tickers)
df_asset

def get_momentum(x):
    temp = [0 for _ in range(len(x.index))]
    momentum = pd.Series(temp, index=x.index)
    
    try:
        print(x.index)
        print(x.name)
        print(x.name-timedelta(days=35))
        print(x.name-timedelta(days=30))
        before_1m = df_asset[x.name-timedelta(days=35):x.name-timedelta(days=30)].iloc[-1]
        before_3m = df_asset[x.name-timedelta(days=95):x.name-timedelta(days=90)].iloc[-1]
        before_6m = df_asset[x.name-timedelta(days=185):x.name-timedelta(days=180)].iloc[-1]
        before_12m = df_asset[x.name-timedelta(days=370):x.name-timedelta(days=365)].iloc[-1]
        momentum = (x/before_1m - 1) * 12 + (x/before_3m - 1) * 4 + (x/before_6m - 1) * 2 + (x/before_12m - 1) * 1
        
    except:
        pass
    
    return momentum

momentum_col = [col + '_m' for col in df_asset.columns]
df_asset[momentum_col] = df_asset.apply(lambda x: get_momentum(x), axis=1)
df_asset

df_asset = df_asset.loc[df_asset.index >= '2004-10-01']
df_asset

df_asset = df_asset.resample(rule='M').last()
df_asset

def select_asset(x):
    selected_asset = pd.Series([0,0], index=['ASSET','PRICE'])
    
    # 모든 공격 자산 > 0
    if x['SPY_m'] > 0 and x['EFA_m'] > 0 and x['EEM_m'] > 0 and x['AGG_m'] > 0:
        selected_momentum = max(x['SPY_m'], x['EFA_m'], x['EEM_m'], x['AGG_m'])
    
    # 공격 자산 중 1개라도 < 0
    else:
        selected_momentum = max(x['LQD_m'], x['SHY_m'], x['IEF_m'])
    
    selected_asset['ASSET'] = x[x==selected_momentum].index[0][:3]
    selected_asset['PRICE'] = x[selected_asset['ASSET']]
    
    return selected_asset

df_asset[['ASSET','PRICE']] = df_asset.apply(lambda x: select_asset(x), axis=1) 
df_asset

return_col = [ticker + '_r' for ticker in tickers]
df_asset[return_col] = df_asset[tickers].pct_change()
df_asset

df_asset['RETURN'] = 0
df_asset['RETURN_ACC'] = 0
df_asset['LOG_RETURN'] = 0
df_asset['LOG_RETURN_ACC'] = 0

for i in range(len(df_asset)):
    strat_return = 0
    log_strat_return = 0
    
    # 직전 달 모멘텀이 좋은 것으로 리밸런싱해서 앞으로 한 달 가져가는 것
    if i > 0:
        strat_return = df_asset[df_asset.iloc[i-1]['ASSET']+'_r'].iloc[i]
        log_strat_return = math.log(strat_return + 1)
        
    df_asset.loc[df_asset.index[i], 'RETURN'] = strat_return
    # 누적 = 직전 누적 * 현재
    df_asset.loc[df_asset.index[i], 'RETURN_ACC'] = (1+df_asset.loc[df_asset.index[i-1], 'RETURN_ACC'])*(1+strat_return)-1
    df_asset.loc[df_asset.index[i], 'LOG_RETURN'] = log_strat_return
    # 로그누적 = 직전 로그누적 + 현재 로그
    df_asset.loc[df_asset.index[i], 'LOG_RETURN_ACC'] = df_asset.loc[df_asset.index[i-1], 'LOG_RETURN_ACC'] + log_strat_return
    
# 수익률 * 100
df_asset[['RETURN','RETURN_ACC','LOG_RETURN','LOG_RETURN_ACC']] = df_asset[['RETURN','RETURN_ACC','LOG_RETURN','LOG_RETURN_ACC']]*100
df_asset[return_col] = df_asset[return_col] * 100

df_asset['BALANCE'] = (1+df_asset['RETURN']/100).cumprod()
df_asset['DRAWDOWN'] = -(df_asset['BALANCE'].cummax() - df_asset['BALANCE']) / df_asset['BALANCE'].cummax()

df_asset[['BALANCE','DRAWDOWN']] = df_asset[['BALANCE','DRAWDOWN']] * 100
df_asset

total_month = len(df_asset)
profit_month = len(df_asset[df_asset['RETURN'] >= 0])
loss_month = len(df_asset[df_asset['RETURN'] < 0])
win_rate = profit_month / total_month * 100
CAGR = ((1+df_asset['RETURN_ACC'][-1]/100)**(1/(total_month/12)))-1
STDEV = np.std(df_asset['RETURN'][1:])*math.sqrt(12)
RRR = CAGR * 100 / STDEV

print(total_month, "개월 중 수익 월 :", profit_month, "개월")
print(total_month, "개월 중 손실 월 :", loss_month, "개월")
print("승률 :", round(win_rate, 2))

print('CAGR : ', round(CAGR*100, 2))
print('MDD : ', round(df_asset['DRAWDOWN'].min(), 2))
print('STDEV :', round(STDEV, 2))
print('Return-Risk Ratio: ', round(RRR, 2))

plt.figure(figsize=(15,5))
seaborn.lineplot(data=df_asset, x=df_asset.index, y=df_asset['LOG_RETURN_ACC'])

plt.figure(figsize=(15,5))
seaborn.lineplot(data=df_asset, x=df_asset.index, y=df_asset['DRAWDOWN'])

quantstats.stats.sharpe(df_asset['RETURN'])/math.sqrt(252/12)

quantstats.reports.plots(df_asset['RETURN']/100, mode='basic')