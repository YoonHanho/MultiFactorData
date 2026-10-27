import FinanceDataReader as fdr

import pandas as pd
import numpy as np
from datetime import date

def get_momentum_one(scode):
    """
    주가 모멘텀과 거래량 모멘텀 계산

    매개변수:
         scode : 종목 코드 (예: '005930')
         SD : 주가데이터 추출시작일 (예: '20250102')
         ED : 주가데이터 추출종료일 (예: '20250131')

    반환값:
        avg : 주가 모멘텀 지표 (기간별 수익률 평균)
        vol : 거래량 모멘텀 지표
    """


    def get_stockinfo_yf(N=10): 
        """
        종목정보 추출 
          2026-10-27 
            1. fdr 오류시, 깃헙에 적재된 종목정보 우회 추출 코드 추가 
               깃헙 적재 파일 : 26년 10월 24일 업로드 (KRX Data Market, KRX Open API 등에서 종목정보 찾을 수 있음) 
            2. 종가 정보 반영 안되는 경우, 우회 코드 적용 
          
        """
        # 거래소 전체 추출 (코스피, 코스닥 대상) 
        try: 
            df = fdr.StockListing('KRX').query("Market in ['KOSPI', 'KOSDAQ']")

            # 종목별 종가(Close) 문자형에서 수치형(integer)으로 변환
            df['Close'] = df['Close'].astype(int)

            # 제외조건
            # 소형주: 시가총액 1,000억 원 미만 종목 제외 적용
            df = df.query(" Marcap >= 100000000000 ")

            # 저유동성 : 일 거래량 2,000주 미만 제외 적용
            df = df.query(" Volume >= 2000 ")

            # 동전주: 높은 변동성 위험을 고려하여 주가 1,000원 미만 종목 제외 적용
            df = df.query(" Close >= 1000 ")

            # 우선주: 낮은 거래량과 본주와의 주가 차이(괴리율)로 인한 분석의 한계로 제외 (종목코드 끝자리 5,7,9,K) 적용
            df = df[ df['Code'].apply(lambda x: False if x[-1] in ['5','7','9','K'] else True) ]

            # 스팩(SPAC), 리츠, 벤처투자 등 : 재무 데이터의 실효성이 없어 제외 적용
            df = df[ ~df['Name'].str.contains('스팩|리츠|리얼티|인프라|유전|벤처') ]

            # 시가총액 N종목 추출
            df = df.sort_values(by='Marcap', ascending=False).iloc[:N]

            # 데이터프레임 인덱스 초기화
            df = df.reset_index(drop=True)

            # 최종 종목 추출 건수 출력
            print("종목 추출 건수 ", len(df))
        
        
        except:
            # fdr 오류시 깃헙 업로드 파일 다운로드 
            url = "https://raw.githubusercontent.com/YoonHanho/MultiFactorData/main/fdr_stocklisting.csv"
            df = pd.read_csv(url)

            # 종목별 종가(Close) 문자형에서 수치형(integer)으로 변환
            df['Close'] = df['Close'].astype(int)

            # 제외조건
            # 소형주: 시가총액 1,000억 원 미만 종목 제외 적용
            df = df.query(" Marcap >= 100000000000 ")

            # 저유동성 : 일 거래량 2,000주 미만 제외 적용
            df = df.query(" Volume >= 2000 ")

            # 동전주: 높은 변동성 위험을 고려하여 주가 1,000원 미만 종목 제외 적용
            df = df.query(" Close >= 1000 ")

            # 우선주: 낮은 거래량과 본주와의 주가 차이(괴리율)로 인한 분석의 한계로 제외 (종목코드 끝자리 5,7,9,K) 적용
            df = df[ df['Code'].apply(lambda x: False if x[-1] in ['5','7','9','K'] else True) ]

            # 스팩(SPAC), 리츠, 벤처투자 등 : 재무 데이터의 실효성이 없어 제외 적용
            df = df[ ~df['Name'].str.contains('스팩|리츠|리얼티|인프라|유전|벤처') ]

            # 시가총액 N종목 추출
            df = df.sort_values(by='Marcap', ascending=False).iloc[:N]

            # 데이터프레임 인덱스 초기화
            df = df.reset_index(drop=True)

            # 최종 종목 추출 건수 출력
            print("종목 추출 건수 ", len(df))

        return df
    
    
    def yfDataReader(scode, SD, ED, stock_list_yf):

        # 1. yfinance로 데이터 수집
        #   종목코드 형식 : '005930.KS' 날짜 형식 : 2026-10-23        
        scode_yf = stock_list_yf.query(f"Code == '{scode}'")['scode_yf'].iloc[0]  
        SD = '-'.join([SD[:4], SD[4:6], SD[6:]])
        ED = '-'.join([ED[:4], ED[4:6], ED[6:]])        
        df = yf.download(scode_yf, start=SD)   # end는 생략 : 최근일자 자동 지정 

        # 2. yfinance 버전에 따라 컬럼이 멀티인덱스(MultiIndex)로 반환될 경우 단일 인덱스로 정리
        if isinstance(df.columns, pd.MultiIndex):
          df.columns = df.columns.get_level_values(0)

        # 3. FinanceDataReader와 동일한 컬럼 순서 및 구성 맞추기
        # yfinance에는 'Change' 컬럼이 없으므로 종가(Close)를 기준으로 일일 등락률을 계산하여 추가합니다.
        df['Change'] = df['Close'].pct_change()

        # 필요한 컬럼만 정확히 순서대로 선택
        df = df[['Open', 'High', 'Low', 'Close', 'Volume', 'Change']]

        # 4. 인덱스 이름 설정 ('Date') 및 날짜 포맷 맞추기
        df.index.name = 'Date'

        return df 


    # 날짜 : SD 작년 1/2, ED는 오늘 
    ED = date.today().strftime('%Y%m%d')   # 오늘
    
    last_year = date.today().year - 1
    SD = date(last_year, 1, 2).strftime('%Y%m%d')  # 작년 1월2일 


    # 모멘텀 지표 계산 후 result에 적재
    result = []

    try: 

        # 1. 주가 및 거래량 데이터 수집 (fdr 에러나면 yfinance)
        try:
            df = fdr.DataReader(scode, SD, ED)
            
        except:   # FDR 오류시 yfinance 에서 데이터 수집
            stock_list_yf = get_stockinfo_yf(9999)[['Code', 'Name', 'Market']]  # 9999 : 전체 코드 
            stock_list_yf['scode_yf'] = np.where(stock_list_yf['Market'] == 'KOSPI', stock_list_yf['Code'] + '.KS', stock_list_yf['Code'] + '.KQ') 
            df = yfDataReader(scode, SD, ED, stock_list_yf) 
    
    
        # 2. 주가 모멘텀 지표 생성
        # 단기 (1일, 1주, 1개월) - 데이터가 너무 없으면 에러가 나는 게 맞으므로 그대로 둠
        mom_1d = ( df.iloc[-1]['Close'] / df.iloc[-2]['Close'] - 1 )  * 100    # 전일
        mom_1w = ( df.iloc[-1]['Close'] / df.iloc[-5]['Close'] - 1 )  * 100    # 주간
        mom_1m = ( df.iloc[-1]['Close'] / df.iloc[-20]['Close'] - 1 )  * 100   # 월간
    
        # 3개월간 (데이터 부족 시 NaN 처리)
        try:
            mom_3m = ( df.iloc[-1]['Close'] / df.iloc[-60]['Close'] - 1 )  * 100
        except:
            mom_3m = np.nan
    
        # 연간 (데이터 부족 시 NaN 처리)
        try:
            mom_1y = ( df.iloc[-1]['Close'] / df.iloc[-240]['Close'] - 1 )  * 100
        except:
            mom_1y = np.nan
    
        # 3. 기간별 수익률의 평균 계산 (NaN을 제외하고 평균 산출)
        avg = np.nanmean([mom_1d, mom_1w, mom_1m, mom_3m, mom_1y])
    
        # 4. 거래량 모멘텀 지표 생성
        try:
            vol_short = df['Volume'].rolling(window=5).mean().iloc[-1]  # 최근 5일
            vol_long = df['Volume'].rolling(window=20).mean().iloc[-1]  # 최근 20일
            vol = ( vol_short / vol_long - 1) * 100
        except:
            vol = np.nan

        result.append( [ scode, avg, vol ] )
        data_mom = pd.DataFrame(result, columns=['scode', 'mom_price', 'mom_vol'])    
        return data_mom

    except Exception as e:
        print(f"에러가 발생했습니다. 상세 내용: {e}")
        print("추출오류 : ", scode) 
        return None
    
        
    