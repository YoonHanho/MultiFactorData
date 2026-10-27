def get_stockinfo(N=10): 
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