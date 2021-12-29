# 모멘텀
# 2020-10-25~26
# https://comdoc.tistory.com/m/entry/%ED%8C%8C%EC%9D%B4%EC%8D%AC-%EB%AA%A8%EB%A9%98%ED%85%80momentum

from datetime import datetime, timedelta  # 사용법: https://dojang.io/mod/page/view.php?id=2463

import FinanceDataReader as fdr
import matplotlib.pyplot as plt
import pandas as pd
from dateutil.relativedelta import relativedelta  # month는 timedelta 사용불가 relativedelta


def load_data(code, start_date):
    data = fdr.DataReader(code, start_date)  # , '2016-01-01'
    return data['Close']  # 종가만 남김.


def buy_etf(money, etf_price, last_etf_num, fee_rate, etf_rate):
    etf_num = money * etf_rate // etf_price
    etf_money = etf_num * etf_price
    etf_fee = (last_etf_num - etf_num) * etf_price * fee_rate if last_etf_num > etf_num else 0
    while etf_num > 0 and money < (etf_money + etf_fee):
        etf_num -= 1
        etf_money = etf_num * etf_price
        etf_fee = (last_etf_num - etf_num) * etf_price * fee_rate if last_etf_num > etf_num else 0
    money -= etf_money + etf_fee
    return money, etf_num, etf_money


def back_test(money: int, fee_rate: float, interval: int, ratio: float, code1: str, code2: str, code3: str,
              start_date: str):
    start_date = datetime.strptime(start_date, '%Y-%m-%d')  # 조회시작일

    # 데이터를 받습니다.
    etf1 = load_data(code1, start_date)
    etf2 = load_data(code2, start_date)
    etf3 = load_data(code3, start_date)

    # 3종류의 종가 데이터를 하나의 데이터프레임으로 합칩니다.
    df = pd.concat([etf1, etf2, etf3], axis=1, keys=['etf1', 'etf2', 'etf3'])

    # 리밸런싱 날짜의 데이터만 new_df에 남깁니다.
    new_df = pd.DataFrame()
    while start_date <= df.index[-1]:
        temp_date = start_date
        while temp_date not in df.index and temp_date < df.index[-1]:
            temp_date += timedelta(days=1)  # 영업일이 아닐 경우 1일씩 증가.
        new_df = new_df.append(df.loc[temp_date])
        start_date += relativedelta(months=interval)  # interval 개월씩 증가.

    new_df["etf1_shift"] = new_df["etf1"].shift(2)
    new_df["etf2_shift"] = new_df["etf2"].shift(2)

    #     print(new_df)

    etf1_num = etf2_num = etf3_num = 0  # 구매한 ETF 개수

    backtest_df = pd.DataFrame()  # 백테스트를 위한 데이터프레임

    for each in new_df.index:
        etf1_price = new_df['etf1'][each]
        etf2_price = new_df['etf2'][each]

        # 모멘텀 계산
        etf1_shift = new_df["etf1_shift"][each]
        etf2_shift = new_df["etf2_shift"][each]

        moment1 = (etf1_price - etf1_shift) / etf1_shift
        moment2 = (etf2_price - etf2_shift) / etf2_shift

        if moment1 > moment2:
            rate = ratio
        elif moment1 < moment2:
            rate = 1 - ratio
        else:
            rate = 0.5

        # 보유 ETF 매도
        money += etf1_num * etf1_price
        money += etf2_num * etf2_price

        # ETF 매입
        money, etf1_num, etf1_money = buy_etf(money, etf1_price, etf1_num, fee_rate, rate)
        money, etf2_num, etf2_money = buy_etf(money, etf2_price, etf2_num, fee_rate, 1)

        total = money + etf1_money + etf2_money
        backtest_df[each] = [int(total)]
        # print(f'{each}: {total//1}, etf1:{etf1_num}, etf2:{etf2_num}')

    # 행열을 바꿈
    backtest_df = backtest_df.transpose()
    backtest_df.columns = ['backtest', ]

    # 백테스트 결과 출력
    # print(backtest_df)
    print(backtest_df.tail())

    # 최종 데이터 프레임, 3개의 지표와 백테스트 결과
    final_df = pd.concat([new_df, backtest_df], axis=1)

    # 시작점을 1로 통일함.
    final_df['etf1'] = final_df['etf1'] / final_df['etf1'][0]
    final_df['etf2'] = final_df['etf2'] / final_df['etf2'][0]
    final_df['etf3'] = final_df['etf3'] / final_df['etf3'][0]
    final_df['backtest'] = final_df['backtest'] / final_df['backtest'][0]

    # 그래프 출력
    plt.plot(final_df['etf1'].index, final_df['etf1'], label='etf1', color='r')
    plt.plot(final_df['etf2'].index, final_df['etf2'], label='etf2', color='g')
    plt.plot(final_df['etf3'].index, final_df['etf3'], label='etf3', color='b')
    plt.plot(final_df['backtest'].index, final_df['backtest'], label='back_test', color='black')
    plt.legend(loc='upper left')
    plt.show()