import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from talib.abstract import *
import pandas_datareader.data as web
matplotlib.rc('font', family='Malgun Gothic', size=8, weight='bold')
stock_list = ['SPY', 'EFA', 'IWD', 'IWF', 'IJH', 'IWM', 'EWJ']
bond_list = ['IEF', 'TLT', 'LQD', 'IEF', 'TLT', 'LQD', 'IEF']
cash_eq = ['SHY']
total_list = stock_list + bond_list + cash_eq

def stock_price(stock, start):
    stock_price = web.DataReader(name=stock, data_source='yahoo', start=start)['Adj Close']
    a = pd.DataFrame(stock_price.div(stock_price.iat[0]))
    a.columns = [stock]
    return a

def momentum(data, freq):
    a = pd.DataFrame()
    b = list(data)
    for i in b:
        a[i] = data.iloc[:, 0]
        a[i + 'ROC'] = ROC(data, timeperiod=freq, price=i).shift(0)
        a[i + '수익'] = np.where(a[i + 'ROC'].shift(1) > 0, a[i] / a[i].shift(1), 1).cumprod()
    return a[i + '수익']

def multi_momentum(데이터, 주기1, 주기2, 주기3, 주기4, 주기5):
    a = pd.DataFrame()
    b = [주기1, 주기2, 주기3, 주기4, 주기5]
    for i in b:
        a[str(i)] = momentum(데이터, i)
    return a.mean(axis=1)

def 전체데이터():
    a = pd.DataFrame()
    for i in total_list:
        a = pd.concat([a, stock_price(i, '2003-01-01')], axis=1)
    return a

a = pd.DataFrame()
for i in total_list:
    a = pd.concat([a, multi_momentum(stock_price(i, '2003-01-01'), 20, 60, 90, 120, 200)], axis=1)
a['mean'] = a.mean(axis=1)
전체데이터().mean(axis=1)
b = 전체데이터().mean(axis=1).to_frame()
b.columns = ['a']
multi_momentum(b, 20, 60, 90, 120, 200)

x = pd.DataFrame()
x = pd.concat([x, a['mean'], 전체데이터().mean(axis=1), multi_momentum(b, 20, 60, 90, 120, 200)], axis=1)
x.columns = ['종목다중평균', '전체평균', '전체다중평균']
x.plot()
plt.show()

# ---------------------------------------------------------

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import pandas_datareader.data as web
# EFA : iShares MSCI EAFE ETF
# IWD : iShares Russell 1000 Value ETF
# IWF : iShares Russell 1000 Growth ETF
# IJH : iShares Core S&P Mid-Cap ETF
# IWM : iShares Russell 2000 ETF
# EWJ : iShares MSCI Japan ETF
# LQD : iShares iBoxx $ Investment Grade Corporate Bond ETF

주식리스트 = ['SPY', 'EFA', 'IWD', 'IWF', 'IJH', 'IWM', 'EWJ']
채권리스트 = ['IEF', 'TLT', 'LQD']
현금리스트 = ['SHY']
전체리스트 = 주식리스트 + 채권리스트 + 현금리스트
주식개수 = 7
채권개수 = 3
현금개수 = 1
모멘텀스코어역치 = 0
월말지수 = pd.DataFrame()
월간수익률 = pd.DataFrame()
평균모멘텀 = pd.DataFrame()
평균모멘텀스코어 = pd.DataFrame()
투자비중 = pd.DataFrame()

# https://stock79.tistory.com/73?category=457287
'''
평균 모멘텀 스코어를 계산하는 방법은 다음과 같다.

최근 1개월~12개월 수익률을 구한다.
수익률이 +면 1점 아니면 0점을 부여한다.
평균값을 구한다.
'''

class 모멘텀시뮬:
    def __init__(self, 종목, 시작일):
        self.종목 = 종목
        self.시작일 = 시작일

    def 월말지수(self):
        수정종가 = web.DataReader(name=self.종목, data_source='yahoo', start=self.시작일)['Adj Close']
        수정수익률 = 수정종가 / 수정종가[0]
        return 수정수익률.resample('M').last()

    def 월간수익률(self):
        return self.월말지수() / self.월말지수().shift(1)

    def 평균모멘텀(self):
        초기값 = 0
        for i in range(1, 13):
            초기값 = self.월말지수() / self.월말지수().shift(i) + 초기값
        return 초기값 / 12

    def 평균모멘텀스코어(self):
        a = self.평균모멘텀().copy()
        초기값 = 0
        for i in range(1, 13):
            초기값 = np.where(self.월말지수() / self.월말지수().shift(i) > 1, 1, 0) + 초기값
        모멘텀스코어 = np.where(초기값 / 12 > 모멘텀스코어역치, 초기값 / 12, 0)
        a[a > -1] = 모멘텀스코어
        return a

    def 평균모멘텀스코이(self):
        초기값 = 0
        for i in range(1, 13):
            초기값 = np.where(self.월말지수().values / self.월말지수().shift(i).values > 1, 1, 0) + 초기값
        모멘텀스코어 = np.where(초기값 / 12 >= 모멘텀스코어역치, 초기값 / 12, 0)
        return pd.DataFrame(모멘텀스코어, columns=self.평균모멘텀().columns, index=self.평균모멘텀().index)

for i in 전체리스트:
    a = 모멘텀시뮬(i, '2000-01-01')
    월말지수[i] = a.월말지수()
    월간수익률[i] = a.월간수익률()
    평균모멘텀[i] = a.평균모멘텀()
    평균모멘텀스코어[i] = a.평균모멘텀스코어()

주식모멘텀순위 = 평균모멘텀.iloc[:, 0: len(주식리스트)].rank(1, ascending=0)
채권모멘텀순위 = 평균모멘텀.iloc[:, len(주식리스트): len(주식리스트) + len(채권리스트)].rank(1, ascending=0)
현금모멘텀순위 = 평균모멘텀.iloc[:, len(주식리스트) + len(채권리스트): len(주식리스트) + len(채권리스트) + len(현금리스트)].rank(1, ascending=0)
주식모멘텀비중 = pd.DataFrame(np.where(주식모멘텀순위 < 주식개수 + 1, 1 / 주식개수, 0))
채권모멘텀비중 = pd.DataFrame(np.where(채권모멘텀순위 < 채권개수 + 1, 1 / 채권개수, 0))
현금모멘텀비중 = pd.DataFrame(np.where(현금모멘텀순위 < 주식개수 + 1, 1 / 현금개수, 0))
투자비중 = pd.concat([주식모멘텀비중, 채권모멘텀비중, 현금모멘텀비중], axis=1)
투자비중.columns = 월말지수.columns
투자비중.index = 월말지수.index
최종수익률 = pd.DataFrame(월간수익률.values * 투자비중.shift(1).values * 평균모멘텀스코어.shift(1).values).sum(axis=1) / pd.DataFrame(
    투자비중.shift(1).values * 평균모멘텀스코어.shift(1).values).sum(axis=1)
최종수익률 = pd.DataFrame(최종수익률.cumprod())
최종수익률.columns = ['수익']
최종수익률.index = 월말지수.index
k = len(월말지수.index) - len(월말지수.dropna().index) + 12
월말지수1 = 월말지수.drop(월말지수.index[0:k])
최종수익률1 = 최종수익률.drop(최종수익률.index[0:k])
차트 = pd.concat([월말지수1, 최종수익률1], axis=1)
차트.index = 최종수익률1.index
차트.columns = 전체리스트 + ['수익']
차트 = 차트.div(차트.ix[0])
차트.plot()
plt.show()

file = pd.ExcelWriter('N:\\모멘텀255.xlsx')
월말지수.to_excel(file, sheet_name='월말지수')
월간수익률.to_excel(file, sheet_name='월간수익률')
평균모멘텀.to_excel(file, sheet_name='평균모멘텀')
평균모멘텀스코어.to_excel(file, sheet_name='평균모멘텀스코어')
투자비중.to_excel(file, sheet_name='투자비중')
최종수익률.to_excel(file, sheet_name='최종수익률')
차트.to_excel(file, sheet_name='차트')
file.save()
