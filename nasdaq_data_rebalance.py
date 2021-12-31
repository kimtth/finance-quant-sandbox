import pandas as pd
import seaborn
from datetime import datetime
import dateutil.relativedelta
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

plt.rcParams["figure.figsize"] = (10, 10)
pd.options.mode.chained_assignment = None


def next_transaction_date_mm(df, date, n_month_back=0):
    n_day_adjust = 0
    n_year_back = 0
    date_ago = None
    while True:
        if n_day_adjust > 31:
            break

        try:
            if n_month_back == 12:
                n_year_back = 1
                n_month_back = 0

            # date_ago = datetime(date.year - n_year_back, date.month - n_month_back, date.day - n_day_adjust)
            date_ago = date - dateutil.relativedelta.relativedelta(years=n_year_back, months=n_month_back,
                                                                   days=n_day_adjust)
            if not len(df[df['DATE'] == date_ago]) > 0:
                n_day_adjust = n_day_adjust + 1
            else:
                break
        except ValueError:
            n_day_adjust = n_day_adjust + 1
            continue

    return date_ago


def end_of_year(df, date, n_year_back=0):
    date_n_yr_adjust_range = datetime(date.year - n_year_back, date.month, date.day - 5)

    try:
        date_ago = datetime(date.year - n_year_back, date.month, date.day)
        # @Debug: print(type(date), type(date_1yr_ago), date, date_1yr_ago)
    except ValueError:
        # @Tip: e.g. 2012-02-29 00:00:00 2011-02-28 00:00:00
        #       date.day-1 : ValueError: day is out of range for month
        date_ago = datetime(date.year - n_year_back, date.month, date.day - 1)

    date_1yr_ago_df = df[
        (df['DATE'] > date_n_yr_adjust_range) & (df['DATE'] <= date_ago)].tail(1)

    return date_1yr_ago_df


def rebalancing_criterias_uem(df_spy, df_uem, rebalancing_date):
    try:
        spy_price = df_spy.loc[df_spy['DATE'] == rebalancing_date, 'Adj Close'].item()
        spy_ma_200d = df_spy.loc[df_spy['DATE'] == rebalancing_date, 'MA_200D'].item()

        uem_yyyymm = str(rebalancing_date.year) + str(rebalancing_date.month).zfill(2)
        df_uem['YEAR_MONTH'] = df_uem['YEAR_MONTH'].astype(str)
        if len(df_uem.loc[df_uem['YEAR_MONTH'] == uem_yyyymm, 'UNEMPLOYMENT_RATE']) > 0:
            uem_index = df_uem.loc[df_uem['YEAR_MONTH'] == uem_yyyymm, 'UNEMPLOYMENT_RATE'].item()
            uem_12m = df_uem.loc[df_uem['YEAR_MONTH'] == uem_yyyymm, 'MA_12M'].item()
        else:
            uem_index = 0
            uem_12m = 0

        if spy_price < spy_ma_200d and uem_index > uem_12m:
            return 'SHY'
        else:
            return 'RISK'
    except ValueError as e:
        print(e, rebalancing_date)


def graph_cagr_mdd(df_asset, file_name='output'):
    trade_month = round(len(df_asset.index) / 12, 2)

    # CAGR
    if df_asset['TOTAL'].iat[0] != float(0):
        total_profit = (df_asset['TOTAL'].iat[-1] / df_asset['TOTAL'].iat[0])
        cagr = round((total_profit ** (1 / trade_month) - 1) * 100, 2)

        # MDD
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
