import configparser
import logging
import os
import time
from datetime import datetime
from pprint import PrettyPrinter

import pandas as pd
# from exchange_calendars import get_calendar
from google.protobuf.json_format import MessageToDict
from koapy import KiwoomOpenApiPlusEntrypoint  # python 3.10 not supported
from pandas import ExcelWriter
from workalendar.asia import SouthKorea

# krx_calendar = get_calendar("XKRX")
kr_calendar = SouthKorea()
pp = PrettyPrinter()

data_root_path = os.path.abspath('.\\data')
data_sell_path = 'sell'
data_buy_path = 'buy'

# Set up logging to file
time_stamp_str = datetime.now().strftime('%Y%m%d-%H%M%S')
file = logging.FileHandler(filename='logging_' + time_stamp_str + '.log', encoding='utf-8', mode='w+')
console = logging.StreamHandler()
logging.basicConfig(
    force=True,
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO,
    handlers=[file, console]
)

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')
test_mode = config['TRANSACTION'].getboolean('TEST_MODE')
price_range_on_off = config['TRANSACTION'].getboolean('PRICE_RANGE_ON_OFF')
buy_on = config['TRANSACTION'].getboolean('BUY_ON')
sell_on = config['TRANSACTION'].getboolean('SELL_ON')
fast_track = config['TRANSACTION'].getboolean('FAST_TRACK')

#  가격이 급상승 경우도 있으므로 시가에서 % 만큼 곱한 가격으로 매수량을 판단
price_range_percentage = 1  # config['TRANSACTION']['PRICE_RANGE_PERCENTAGE']
if test_mode:
    data_root_path = os.path.abspath('.\\test-data')
if price_range_on_off:
    price_range_percentage_config = config['TRANSACTION']['PRICE_RANGE_PERCENTAGE']
    price_range_percentage = float(price_range_percentage_config)


def read_purchase_book(file_path):
    df = pd.read_csv(file_path, dtype=str)
    df = df.dropna(axis=1, how="all")
    return df


def read_sell_book(file_path):
    df = pd.read_csv(file_path, dtype=str)
    df = df.dropna(axis=1, how="all")
    return df


def pprint_event(event):
    pp.pprint(MessageToDict(event, preserving_proto_field_name=True))


def logging_dict_detail(df):
    for key, val in df.items():
        logging.info(f'{key}: {val}')


def logging_row_detail(df):
    for key, val in df.iterrows():
        logging.info(f'{key}: {val}')


def get_login_details(context):
    result = dict()
    result["보유계좌수"] = context.GetLoginInfo("ACCOUNT_CNT")
    account_numbers = context.GetLoginInfo("ACCLIST").rstrip(";").split(";")
    for i, accno in enumerate(account_numbers):
        result["계좌번호 (%d/%s)" % (i + 1, result["보유계좌수"])] = accno
    result["사용자 ID"] = context.GetLoginInfo("USER_ID")
    result["사용자 명"] = context.GetLoginInfo("USER_NAME")
    result["키보드보안 해지 여부"] = {
        "0": "정상",
        "1": "해지",
    }.get(context.GetLoginInfo("KEY_BSECGB"), "알수없음")
    result["방화벽 설정 여부"] = {
        "0": "미설정",
        "1": "설정",
        "2": "해지",
    }.get(context.GetLoginInfo("FIREW_SECGB"), "알수없음")
    result["접속서버 구분"] = {
        "1": "모의투자",
    }.get(context.GetServerGubun(), "실서버")

    return pd.Series(result)


# Create separate low level function due to _ParseTransactionCallResponses - Parsing failed
def deposit_details(context, account_no):
    rqname = "예수금상세현황요청"
    trcode = "opw00001"
    inputs = {
        "계좌번호": account_no,
        "비밀번호": "",
        "비밀번호입력매체구분": "00",
        "조회구분": "2"  # 조회구분 = 3:추정조회, 2:일반조회
    }
    scrno = None
    output = dict()
    deposit_output = dict()
    for event in context.TransactionCall(rqname, trcode, scrno, inputs):
        logging.info('Got event for request: %s', rqname)
        # pprint_event(event)
        names = event.single_data.names
        values = event.single_data.values
        for name, value in zip(names, values):
            output[name] = value
    logging.info('%s %s', '예수금', output['예수금'])
    logging.info('%s %s', '출금가능금액', output['출금가능금액'])
    logging.info('%s %s', '주문가능금액', output['주문가능금액'])

    deposit_output['예수금'] = output['예수금']
    deposit_output['출금가능금액'] = output['출금가능금액']
    deposit_output['주문가능금액'] = output['주문가능금액']

    return deposit_output


def deposit_balance(context, account_no, lookup_type=None):
    # 계좌평가잔고내역요청
    # 조회구분 = 1:합산, 2:개별
    single, multi = context.GetAccountEvaluationBalanceAsSeriesAndDataFrame(account_no)
    # logging.info('%s %s', '계좌평가현황요청', single)
    # logging.info('%s %s', '계좌평가잔고내역요청', multi)
    return single, multi


def allocate_budget_per_stock(total_budget, number_item):
    per_stock_budget = int(total_budget) / int(number_item)
    return int(per_stock_budget)


'''
# GetStockBasicInfoAsDict
    {'종목코드': '005930', '종목명': '삼성전자', '결산월': '12', '액면가': '100', '자본금': '7780', '상장주식': '5969783', 
    '신용비율': '+0.16', '연중최고': '+96800', '연중최저': '-68300', '시가총액': '4250485', '시가총액비중': '', '외인소진률': '+51.21', 
    '대용가': '54750', 'PER': '18.54', 'EPS': '3841', 'ROE': '10.0', 'PBR': '1.81', 'EV': '4.83', 
    'BPS': '39406', '매출액': '2368070', '영업이익': '359939', '당기순이익': '264078', '250최고': '+96800', 
    '250최저': '-63900', '시가': '+70400', '고가': '+71400', '저가': '-70100', '상한가': '+91200', '하한가': '-49200', 
    '기준가': '70200', '예상체결가': '-0', '예상체결수량': '0', '250최고가일': '20210111', '250최고가대비율': '-26.45', '250최저가일': 
    '20201116', '250최저가대비율': '+11.42', '현재가': '+71200', '대비기호': '2', '전일대비': '+1000', '등락율': '+1.42', 
    '거래량': '11954728', '거래대비': '+117.84', '액면가단위': '원', '유통주식': '4454905', '유통비율': '74.6'} 
'''


def sell_order_process_data(context, sell_file_path, balance_quantity):
    if sell_file_path:
        sell_df = read_sell_book(sell_file_path)
    else:
        sell_df = pd.DataFrame()

    # order_type = 1  # 주문유형입니다. (1: 매수, 2: 매도, 3: 매수취소, 4: 매도취소, 5: 매수정정, 6: 매도 정정)
    # quote_type = "03"  # '00': 지정가, '03': 시장가
    # 코드번호,종목명,주가
    sell_df_target = pd.DataFrame()

    if sell_df.empty is False:
        if balance_quantity.empty is False:
            sell_df_target = sell_df[['코드번호', '종목명', '순위']].copy()
            balance_quantity = balance_quantity.rename(columns={'종목번호': '코드번호', '보유수량': 'quantity'})
            balance_quantity['코드번호'] = balance_quantity['코드번호'].str.replace('A', '')
            sell_df_target['코드번호'] = sell_df_target['코드번호'].str.replace('A', '')
            sell_df_target = pd.merge(sell_df_target, balance_quantity, on=['코드번호'])  # inner_join
            sell_df_target['order_type'] = 2

    return sell_df_target


def buy_order_process_data(context, buy_file_path, per_stock_budget):
    if buy_file_path:
        buy_df = read_purchase_book(buy_file_path)
    else:
        buy_df = pd.DataFrame()

    buy_df_target = pd.DataFrame()
    # 코드번호,종목명,주가
    if buy_df.empty is False:
        buy_df_target = buy_df[['코드번호', '종목명', '순위']].copy()
        buy_df_target['order_type'] = 1
        buy_df_target['코드번호'] = buy_df_target['코드번호'].str.replace('A', '')

        # Sell 은 시장가 / Buy 의 mid_price는 전일 Min/Max의 중간가
        for index, row in buy_df_target.iterrows():
            code_no = row['코드번호']
            stock_name = row['종목명']
            info = context.GetStockBasicInfoAsDict(code_no)

            # Empty check
            if info["현재가"]:
                price = abs(int(info["현재가"]))  # 가장 최근에 거래된 가격
                market_price = abs(int(info['시가']))  # 즉시 체결
                market_high_price = abs(int(info['고가']))
                market_low_price = abs(int(info['저가']))
                mid_price = int((int(market_high_price) + int(market_low_price)) / 2)
                buy_df_target.loc[index, 'price'] = price
                buy_df_target.loc[index, 'market_price'] = market_price
                buy_df_target.loc[index, 'mid_price'] = mid_price
                buy_df_target.loc[index, 'quantity'] = int(
                    int(per_stock_budget) / int(market_price * price_range_percentage))
                int_cols = ['price', 'market_price', 'mid_price', 'quantity']
                buy_df_target[int_cols] = buy_df_target[int_cols].apply(pd.to_numeric, downcast="integer",
                                                                        errors='coerce')
                buy_df_target[int_cols] = buy_df_target[int_cols].fillna(0).astype(int)
            else:
                logging.info('%s %s is not existed.', code_no, stock_name)

    return buy_df_target


def sell_order_process_action(context, account_no, sell_file_path, balance_quantity):
    sell = sell_order_process_data(context, sell_file_path, balance_quantity)

    logging.info('%s\n %s', 'Sell', sell)
    time_stamp_str = datetime.now().strftime('%Y%m%d-%H%M%S')
    xls_path = os.path.join(os.path.abspath('.'), 'sell_' + time_stamp_str + '.xlsx')
    logging.info('%s %s', 'Excel', xls_path)

    with ExcelWriter(xls_path) as writer:
        sell.to_excel(writer, '%s' % 'sell')
        writer.save()

    if sell.empty is False:
        for index, row in sell.iterrows():
            order_type = row['order_type']
            stock_code = row['코드번호']
            quantity = row['quantity']
            order_portfolio(context, account_no, order_type, stock_code, quantity)


def buy_order_process_action(context, account_no, buy_file_path, per_stock_budget):
    buy = buy_order_process_data(context, buy_file_path, per_stock_budget)

    logging.info('%s\n %s', 'Buy', buy)
    time_stamp_str = datetime.now().strftime('%Y%m%d-%H%M%S')
    xls_path = os.path.join(os.path.abspath('.'), 'buy_' + time_stamp_str + '.xlsx')
    logging.info('%s %s', 'Excel', xls_path)

    with ExcelWriter(xls_path) as writer:
        buy.to_excel(writer, '%s' % 'buy')
        writer.save()

    if buy.empty is False:
        for index, row in buy.iterrows():
            order_type = row['order_type']
            stock_code = row['코드번호']
            quantity = row['quantity']
            if index == buy.tail(1).index:
                deposit_output = deposit_details(context, account_no)
                logging.info('------Last Order Call 예수금상세현황------')
                logging_dict_detail(deposit_output)
                total_budget = deposit_output['주문가능금액']
                stock_info = context.GetStockBasicInfoAsDict(stock_code)
                market_price = abs(int(stock_info['시가']))  # 즉시 체결
                quantity = abs(abs(int(total_budget)) / int(market_price))  # 마지막 종목일 경우 재계산 후 잔량 만큼 만 구입.
                order_portfolio(context, account_no, order_type, stock_code, quantity)
            else:
                order_portfolio(context, account_no, order_type, stock_code, quantity)


# def is_currently_in_session_exchange_calendars():
#     # exchange_calendars not worked.
#     now = Timestamp.now(tz=krx_calendar.tz)
#     previous_open = krx_calendar.previous_open(now).astimezone(krx_calendar.tz)
#     next_close = krx_calendar.next_close(previous_open).astimezone(krx_calendar.tz)
#
#     return previous_open <= now <= next_close


def is_currently_in_session():
    now = datetime.today()
    is_working = kr_calendar.is_working_day(now)

    return is_working


def order_portfolio(entrypoint, account_no, order_type, stock_code, quantity):
    request_name = "%s-%s".format(order_type, stock_code)  # 사용자 구분명, 구분가능한 임의의 문자열
    screen_no = None  # 화면번호, 0000 을 제외한 4자리 숫자 임의로 지정, None 의 경우 내부적으로 화면번호 자동할당
    # order_type = 1  # 주문유형입니다. (1: 매수, 2: 매도, 3: 매수취소, 4: 매도취소, 5: 매수정정, 6: 매도 정정)
    code = stock_code  # 종목코드
    quantity = quantity  # 주문수량, 1주 매수
    price = 0  # 주문가격, 시장가 매수는 가격설정 의미없음
    quote_type = "03"  # '00': 지정가, '03': 시장가
    original_order_no = ""  # 원주문번호, 주문 정정/취소 등에서 사용

    # 현재는 기본적으로 주문수량이 모두 소진되기 전까지 이벤트를 듣도록 되어있음 (단순 호출 예시)
    order_type_str = 'buy'
    if str(order_type) == '2':
        order_type_str = 'sell'

    if is_currently_in_session():
        logging.info(
            "Sending order to %s %s, quantity of %s stock, at market price...", order_type_str, code, str(quantity)
        )
        stream = entrypoint.OrderCall(
                request_name,
                screen_no,
                account_no,
                order_type,
                code,
                quantity,
                price,
                quote_type,
                original_order_no,
        )
        if fast_track:
            # Order만 전송 Event를 듣지 않음.
            # Event 수신 시에는 건별로 체결 완료 될 때까지 기다리므로 시간이 걸림.
            # https://github.com/elbakramer/koapy/issues/13
            if hasattr(stream, 'cancel') and callable(getattr(stream, 'cancel')):
                stream.cancel()
            else:
                logging.info('event.cancel() calling failed.')
        else:
            for event in stream:
                pprint_event(event)
                # logging.info('%s\n %s', code, str(MessageToDict(event, preserving_proto_field_name=True)))
                event_dict = MessageToDict(event, preserving_proto_field_name=True)

                if 'single_data' in event_dict:
                    if 'names' in event_dict['single_data']:
                        logging.info('[%s]' % ', '.join(map(str, event_dict['single_data']['names'])))
                    if 'values' in event_dict['single_data']:
                        logging.info('[%s]' % ', '.join(map(str, event_dict['single_data']['values'])))

        time.sleep(1)
    else:
        logging.info("Cannot send an order while market is not open, skipping...")


def concluded_outstanding_contract(context, account_no):
    # 체결 주문
    conclude_contract = context.GetOrderLogAsDataFrame1(account_no)
    # 미체결 주문
    outstanding_contract = context.GetOrderLogAsDataFrame2(account_no)

    return conclude_contract, outstanding_contract


def newest_file(path):
    files = os.listdir(path)
    paths = [os.path.join(path, basename) for basename in files]
    if len(paths):
        return max(paths, key=os.path.getctime)
    else:
        return ''


if __name__ == '__main__':
    number_item = config['TRANSACTION']['NUMBER_ITEM']

    with KiwoomOpenApiPlusEntrypoint() as context:
        # 로그인 처리
        context.EnsureConnected()

        logging.info("------Transaction start------")
        # Login Detail
        login_detail = get_login_details(context)
        logging.info('------로그인------')
        logging_dict_detail(login_detail)

        # Account List
        account_no = context.GetAccountList()[0]
        logging.info('%s %s', '계좌번호', account_no)

        if account_no:
            # GetDepositInfo
            balance, balance_multi = deposit_balance(context, account_no)
            logging.info('------계좌평가현황요청------')
            logging_row_detail(balance_multi)

            balance_quantity = pd.DataFrame()
            if balance_multi.empty is False:
                balance_quantity = balance_multi[['종목번호', '보유수량']]

            # Latest file set as a transaction input.
            sell_file_path = newest_file(os.path.join(data_root_path, data_sell_path))
            buy_file_path = newest_file(os.path.join(data_root_path, data_buy_path))

            # OrderCall
            if sell_on:
                sell_order_process_action(context, account_no, sell_file_path, balance_quantity)

            deposit_output = deposit_details(context, account_no)
            logging.info('------예수금상세현황------')
            logging_dict_detail(deposit_output)
            total_budget = deposit_output['주문가능금액']
            per_stock_budget = allocate_budget_per_stock(total_budget, number_item)

            if per_stock_budget <= 0:
                logging.warning('주문가능금액이 없습니다.')
            else:
                # per_stock_budget 기준으로 매수
                if buy_on:
                    buy_order_process_action(context, account_no, buy_file_path, per_stock_budget)

                logging.info("------Transaction end------")
                logging.info("======거래 후 계좌 현황 조회======시작")
                deposit_output = deposit_details(context, account_no)
                logging.info('------예수금상세현황------')
                logging_dict_detail(deposit_output)
                #
                # balance, balance_multi = deposit_balance(context, account_no)
                # logging.info('------계좌평가현황요청------')
                # logging_row_detail(balance_multi)
                # context.close()
                logging.info("======거래 후 계좌 현황 조회======종료")

                # time.sleep(10)
                # logging.info("======주문 후 체결/미체결 현황 조회======시작")
                # conclude_contract, outstanding_contract = concluded_outstanding_contract(context, account_no)
                # logging.info("======거래 후 체결 현황 조회======")
                # logging_row_detail(conclude_contract)
                # logging.info("======거래 후 미체결 현황 조회======")
                # logging_row_detail(outstanding_contract)
                # logging.info("======주문 후 체결/미체결 현황 조회======종료")

        context.close()
