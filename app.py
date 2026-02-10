import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import json
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

# 2. 구글 시트 연결 설정
def get_gspread_client():
    creds_info = json.loads(st.secrets["connections"]["gsheets"]["service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)

try:
    client = get_gspread_client()
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
        df = pd.DataFrame(data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['amount'] = pd.to_numeric(df['amount'])
        return df, ws
    except Exception as e:
        return pd.DataFrame(columns=["date", "category", "item", "amount", "memo"]), None

df, worksheet = load_data(target_worksheet_name)

# 5. 메인 화면 상단: 입력 폼
st.title(f"📊 {user_input.upper()}님 대시보드")

with st.expander("➕ 새로운 내역 기록하기", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        d = col1.date_input("날짜", value=date.today())
        g = col2.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = col3.text_input("항목")
        
        col4, col5 = st.columns([1, 2])
        a = col4.number_input("금액", min_value=0, step=1000)
        m = col5.text_input("메모")
        submit = st.form_submit_button("장부에 기록", use_container_width=True)

        if submit and worksheet:
            try:
                new_data = [str(d), g, i, int(a), m]
                worksheet.append_row(new_data)
                st.success("✅ 저장 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

st.divider()

# 6. 메인 화면 중간: 상세 내역 리스트 (중간 배치)
st.subheader("📑 상세 내역 리스트")
if not df.empty:
    # 날짜를 보기 좋게 문자열로 변환하여 출력
    display_df = df.copy()
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
    st.dataframe(display_df.sort_values('date', ascending=False), use_container_width=True)
else:
    st.info("기록된 데이터가 아직 없습니다. 첫 내역을 입력해 보세요!")

st.divider()

# 7. 메인 화면 하단: 통계 분석 (하단 배치)
if not df.empty:
    st.subheader("📈 지출 분석 리포트")
    col_left, col_right = st.columns(2)

    # '지출' 항목만 필터링
    expense_df = df[df['category'] == '지출'].copy()

    # A. 날짜별 지출 총액 (막대 그래프)
    with col_left:
        st.markdown("#### 📅 날짜별 지출 합계")
        if not expense_df.empty:
            daily_expense = expense_df.groupby('date')['amount'].sum().reset_index()
            fig_bar = px.bar(daily_expense, x='date', y='amount', 
                             labels={'amount':'지출 금액', 'date':'날짜'},
                             color_discrete_sequence=['#FF4B4B'])
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("지출 내역이 없습니다.")

    # B. 항목별 지출 비율 (원그래프)
    with col_right:
        st.markdown("#### 🍕 항목별 지출 비율")
        if not expense_df.empty:
            item_expense = expense_df.groupby('item')['amount'].sum().reset_index()
            fig_pie = px.pie(item_expense, values='amount', names='item', 
                             hole=0.4, 
                             color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("분석할 지출 내역이 없습니다.")
