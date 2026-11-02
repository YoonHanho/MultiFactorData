from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from datetime import datetime 
import time

import pandas as pd

import FinanceDataReader as fdr

API_URL = "https://stock.naver.com/api/domestic/detail/{item_code}/ETFComponent"
CSV_COLUMNS = ("구성종목명", "주식수", "구성비중")




def format_number(value: object) -> str:
	"""API 숫자 문자열의 불필요한 소수점 0을 제거합니다."""
	if value is None or value == "":
		return ""
	try:
		return format(Decimal(str(value)).normalize(), "f")
	except InvalidOperation:
		return str(value)


def fetch_components(item_code: str) -> list[dict[str, str]]:
	url = API_URL.format(item_code=item_code)
	request = Request(
		url,
		headers={
			"User-Agent": "Mozilla/5.0",
			"Referer": f"https://stock.naver.com/domestic/stock/{item_code}/info/analysis",
		},
	)

	try:
		with urlopen(request, timeout=20) as response:
			payload = json.load(response)
	except (HTTPError, URLError, TimeoutError) as error:
		raise RuntimeError(f"네이버 증권 API 요청에 실패했습니다: {error}") from error
	except json.JSONDecodeError as error:
		raise RuntimeError("API 응답을 JSON으로 읽을 수 없습니다.") from error

	if not isinstance(payload, list):
		raise RuntimeError("예상한 구성종목 목록 형식이 아닙니다.")

	rows = []
	for component in payload:
		if not isinstance(component, dict):
			continue
		rows.append(
			{
				CSV_COLUMNS[0]: str(component.get("componentName", "")),
				CSV_COLUMNS[1]: format_number(component.get("cuUnitQuantity")),
				CSV_COLUMNS[2]: format_number(component.get("weight")),
			}
		)
	return rows
    
    
def get_pdf(etf_code, etf_name, bas_dt=''):
    #etf_code = "102110" # etf_code='TIGER 200'
    components = fetch_components(etf_code)
    
    if not components:
        raise RuntimeError("구성종목 데이터가 없습니다. 종목코드 또는 API 응답을 확인하세요.")
        return None 
        
    else:
        df = pd.DataFrame(components, columns=CSV_COLUMNS)
        df['etf_code'] = etf_code
        df['etf_name'] = etf_name
        if bas_dt == '':
            df['bas_dt'] = datetime.now().strftime('%Y%m%d')
        df = df.merge(stocks, on=['구성종목명'], how='left')   # 주식 종목코드 조인(left)  
        df = df[['bas_dt', 'etf_name', 'etf_code', "구성종목명", "종목코드", "주식수", "구성비중"]]  # 컬럼순서 조정  
        return df 
        
        
def main():
     # 코스피/코스닥 종목코드, 종목명 추출 : 종목코드 조인을 위해서 
    stocks = fdr.StockListing('KRX')[['Code','Name']] # KRX 종목(=코스피+코스닥+코넥스)
    stocks.rename({'Code':'종목코드', 'Name':'구성종목명'}, axis=1, inplace=True) 
    
    # ETF 전종목 기본 정보 (KRX Market) 
    df_etf = pd.read_csv('krx data market ETF전종목기본정보.csv', encoding='cp949')
    df_etf.rename({'단축코드':'etf_code'}, axis=1, inplace=True) 

    data = [] 
    for i, row in df_etf.iloc[:5].iterrows():  # 테스트 5종목 
        res = get_pdf(row['etf_code'], row['한글종목약명'])
        data.append(res)
        time.sleep(1)  # 1초 쉰다 
        
    df = pd.concat(data, axis=0, ignore_index=False) 
    df = df.merge(df_etf[['etf_code', '상장일', '기초지수명', '복제방법', '기초시장분류', '기초자산분류', '운용사', '총보수', '과세유형']],
                  on='etf_code', how='left')
    return df 
    
            
if __name__ == '__main__':
    
    df = main() 
    
   