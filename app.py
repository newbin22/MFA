import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import json

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

# 2. 구글 시트 직접 연결 설정 (gspread 방식)
def get_gspread_client():
    # Secrets에서 인증 정보 로드
    creds_info = json.loads(st.secrets["connections"]["gsheets"]["service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)

try:
    client = get_gspread_client()
    # Secrets에 저장된 시트 ID (URL 전체가 아닌 ID값)
    spreadsheet_id = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_key(spreadsheet_id)
except Exception as e:
    st.error(f"구글 시트 연결 실패: {e}")
    st.stop()

# 3. 사이드바 및 사용자 설정
st.sidebar.title("💎 WealthFlow Pro")
user_input = st.sidebar.text_input("접속 아이디", value="").strip().lower()

user_mapping = {"newbin": "newbin", "sheet2": "sheet2"}

if not user_input or user_input not in user_mapping:
    st.title("💰 자산관리 시스템")
    st.info("왼쪽 사이드바에 아이디를 입력해주세요.")
    st.stop()

target_worksheet_name = user_mapping[user_input]

# 4. 데이터 로드 및 저장 함수
def load_data(ws_name):
    try:
        ws = sh.worksheet(ws_name)
        data = ws.get_all_records()
        return pd.DataFrame(data), ws
    except Exception as e:
        # 워크시트가 없으면 생성하거나 에러 처리
        st.error(f"데이터 로드 에러: {e}")
        return pd.DataFrame(columns=["date", "category", "item", "amount", "memo"]), None

df, worksheet = load_data(target_worksheet_name)

# 5. 메인 화면 및 입력 폼
st.title(f"📊 {user_input.upper()}님 대시보드")

with st.form("add_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    d = col1.date_input("날짜", value=date.today())
    g = col2.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
    i = col3.text_input("항목")
    a = st.number_input("금액", min_value=0, step=1000)
    m = st.text_input("메모")
    submit = st.form_submit_button("장부에 기록", use_container_width=True)

    if submit and worksheet:
        try:
            # gspread는 행을 직접 추가할 수 있어 400 에러에서 자유롭습니다.
            new_data = [str(d), g, i, int(a), m]
            worksheet.append_row(new_data)
            st.success("✅ 저장 완료!")
            st.rerun()
        except Exception as e:
            st.error(f"저장 실패: {e}")

st.divider()
st.subheader("📑 최근 내역")
if not df.empty:
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
else:
    st.write("데이터가 없습니다.")
