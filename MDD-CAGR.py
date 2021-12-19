import pandas as pd
import matplotlib.pyplot as plt
import math
import seaborn
import numpy as np

df_asset = pd.read_excel('laa-output-20211214-004739.xlsx', index_col=0)

trade_month = round(len(df_asset.index) / 12, 2)
print(trade_month)
result = round((df_asset['TOTAL'].iat[-1] / df_asset['TOTAL'].iat[0] - 1) * 100, 3)

## CAGR 계산
total_profit = (df_asset['TOTAL'].iat[-1] / df_asset['TOTAL'].iat[0])
cagr = round((total_profit ** (1 / trade_month) - 1) * 100, 2)

## MDD 계산
arr_v = np.array(df_asset['TOTAL'])
peak_lower = np.argmax(np.maximum.accumulate(arr_v) - arr_v)
peak_upper = np.argmax(arr_v[:peak_lower])

mdd = round((arr_v[peak_lower] - arr_v[peak_upper]) / arr_v[peak_upper] * 100, 3)
print(trade_month, cagr, mdd)

df_asset['DRAWDOWN'] = (-(df_asset['TOTAL'].cummax() - df_asset['TOTAL']) / df_asset['TOTAL'].cummax()) * 100

df_asset['YEAR'] = df_asset['DATE'].dt.strftime('%Y%m').astype(str)

fig, axs = plt.subplots(2)

plt.xlabel('xlabel', fontsize=4)
plt.xticks(rotation=90)
seaborn.lineplot(data=df_asset, x=df_asset.index, y=df_asset['TOTAL'], ax=axs[0], linewidth=2.5)

plt.xlabel('xlabel', fontsize=4)
plt.xticks(rotation=90)
seaborn.lineplot(data=df_asset, x=df_asset.index, y=df_asset['DRAWDOWN'], ax=axs[1], linewidth=2.5)
plt.show()