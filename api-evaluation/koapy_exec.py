import logging
import os.path
from pprint import PrettyPrinter

import pandas as pd
from exchange_calendars import get_calendar
from google.protobuf.json_format import MessageToDict
from koapy import KiwoomOpenApiPlusEntrypoint  # python 3.10 not supported
from pandas import Timestamp

krx_calendar = get_calendar("XKRX")
pp = PrettyPrinter()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s - %(filename)s:%(lineno)d",
    level=logging.DEBUG,
)


def read_purchase_book(file_path):
    df = pd.read_csv(file_path, dtype=str)
    return df


def pprint_event(event):
    pp.pprint(MessageToDict(event, preserving_proto_field_name=True))


def kiwoom_test_run(context):
    # 로그인 처리
    context.EnsureConnected()

    # 이벤트를 알아서 처리하고 결과물만 제공하는 상위 함수 사용 예시
    code = "005930"
    info = context.GetStockBasicInfoAsDict(code)
    print(info)
    price = info["현재가"]
    print(price)


def is_currently_in_session():
    now = Timestamp.now(tz=krx_calendar.tz)
    previous_open = krx_calendar.previous_open(now).astimezone(krx_calendar.tz)
    next_close = krx_calendar.next_close(previous_open).astimezone(krx_calendar.tz)
    return previous_open <= now <= next_close


def order_portfolio(entrypoint, account_no, order_type, stock_code, quantity):
    request_name = "삼성전자 1주 시장가 신규 매수"  # 사용자 구분명, 구분가능한 임의의 문자열
    screen_no = None  # 화면번호, 0000 을 제외한 4자리 숫자 임의로 지정, None 의 경우 내부적으로 화면번호 자동할당
    # order_type = 1  # 주문유형입니다. (1: 매수, 2: 매도, 3: 매수취소, 4: 매도취소, 5: 매수정정, 6: 매도 정정)
    code = stock_code  # 종목코드, 앞의 삼성전자 종목코드
    quantity = quantity  # 주문수량, 1주 매수
    price = 0  # 주문가격, 시장가 매수는 가격설정 의미없음
    quote_type = "03"  # '00': 지정가, '03': 시장가
    original_order_no = ""  # 원주문번호, 주문 정정/취소 등에서 사용

    # 현재는 기본적으로 주문수량이 모두 소진되기 전까지 이벤트를 듣도록 되어있음 (단순 호출 예시)
    if is_currently_in_session():
        logging.info(
            "Sending order to buy %s, quantity of 1 stock, at market price...", code
        )
        for event in entrypoint.OrderCall(
                request_name,
                screen_no,
                account_no,
                order_type,
                code,
                quantity,
                price,
                quote_type,
                original_order_no,
        ):
            pprint_event(event)
    else:
        logging.info("Cannot send an order while market is not open, skipping...")


def allocate_budget_per_stock(total_budget, stock_cnt):
    per_stock_budget = total_budget / stock_cnt
    return per_stock_budget


def quantity_by_budget(current_price, per_stock_budget, price_range_percentage=0.98):
    quantity = per_stock_budget / (current_price * price_range_percentage)
    return quantity


def get_login_details(context):
    # GetLoginInfo
    # https://wikidocs.net/4243
    result = {}
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


# Create core part for _ParseTransactionCallResponses - Parsing failed
def deposit_details(entry_point):
    rqname = "예수금상세현황요청"
    trcode = "opw00001"
    inputs = {
        "계좌번호": account_no_candidate,
        "비밀번호": "",
        "비밀번호입력매체구분": "00",
        "조회구분": "2"  # 조회구분 = 3:추정조회, 2:일반조회
    }
    scrno = None
    output = {}
    for event in context.TransactionCall(rqname, trcode, scrno, inputs):
        logging.info('Got event for request: %s', rqname)
        # pprint_event(event)
        names = event.single_data.names
        values = event.single_data.values
        for name, value in zip(names, values):
            output[name] = value
    print(output['예수금'])
    print(output['주식증거금현금'])
    deposit = output['예수금']
    deposit_margin_cash = output['주식증거금현금']
    return deposit, deposit_margin_cash


def gen_subsequent_sell_buy_order_process():
    pass


if __name__ == '__main__':
    #file_path = 'D:\openKiwoom\data\오늘의종목_20211119_234441.csv'
    #df = read_purchase_book(os.path.abspath(file_path))
    #print(df.shape)
    #print(df)

    total_budget = 100000  # KRW

    with KiwoomOpenApiPlusEntrypoint() as context:
        # 로그인 처리
        context.EnsureConnected()
        # Test
        kiwoom_test_run(context)
        # Login Detail
        login_detail = get_login_details(context)
        print(login_detail)
        for key, val in login_detail.items():
            print(f'{key}: {val}')

        # Account List
        for account_no_candidate in context.GetAccountList():
            print(account_no_candidate, type(account_no_candidate))

            if account_no_candidate:
                # GetDepositInfo
                try:
                    deposit, deposit_margin_cash = deposit_details(context)
                except Exception as e:
                    print(e)
                    pass
            '''
            single, multi = context.GetAccountEvaluationStatusAsSeriesAndDataFrame(account_no_candidate)
            print(single)
            print(multi)
            '''
            response = context.GetOrderLogAsDataFrame1(account_no_candidate)
            for event in response:
                print(event)

    print("end------")
    context.close()
