import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import json
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

# CSS 커스텀: 메트릭 카드를 한 줄로 강제 고정하고 글자 크기 조정
st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 1.8vw !important;
        white-space: nowrap !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1vw !important;
        white-space: nowrap !important;
    }
    div[data-testid="column"] {
        width: 25% !important;
        flex: 1 1 calc(25% - 1rem) !important;
        min-width: 150px !important;
    }
    </style>
    """, unsafe_allow_html=True)

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

st.sidebar.divider()
st.sidebar.subheader("⚙️ 자산 설정")
initial_asset = st.sidebar.number_input("기초 자산 (원)", min_value=0, value=1000000, step=100000)

user_mapping = {"newbin": "newbin", "sheet2": "sheet2", "sheet3": "sheet3"}

if not user_input or user_input not in user_mapping:
    st.title("💰 자산관리 시스템")
    st.info("사이드바에 아이디를 입력해주세요.")
    st.stop()

target_worksheet_name = user_mapping[user_input]

# 4. 데이터 로드 함수
def load_data(ws_name):
    try:
        ws = sh.worksheet(ws_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).astype(int)
            df = df.sort_values('date').reset_index(drop=True)
        else:
            df = pd.DataFrame(columns=["date", "category", "item", "amount", "memo"])
        return df, ws
    except Exception as e:
        return pd.DataFrame(columns=["date", "category", "item", "amount", "memo"]), None

df, worksheet = load_data(target_worksheet_name)

# --- 5. 대시보드 요약 섹션 (최상단 한 줄 고정) ---
st.title(f"📊 {user_input.upper()}님 자산 현황")

total_income = df[df['category'] == '수익']['amount'].sum()
total_expense = df[df['category'] == '지출']['amount'].sum()
total_savings = df[df['category'].str.contains('저축', na=False)]['amount'].sum()
current_balance = initial_asset + total_income - total_expense - total_savings

# 한 줄 배치를 위한 컬럼 생성
m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric("현재 잔액", f"{current_balance:,}원")
m_col2.metric("총 수익", f"{total_income:,}원")
m_col3.metric("총 지출", f"{total_expense:,}원")
m_col4.metric("총 저축액", f"{total_savings:,}원")

st.divider()

# 6. 입력 폼
with st.expander("➕ 새로운 내역 기록하기", expanded=False):
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
            new_row = pd.DataFrame([{"date": d, "category": g, "item": i, "amount": int(a), "memo": m}])
            full_df = pd.concat([df, new_row], ignore_index=True)
            full_df['date'] = pd.to_datetime(full_df['date']).dt.date
            full_df = full_df.sort_values('date')
            save_data = [full_df.columns.values.tolist()] + full_df.astype(str).values.tolist()
            worksheet.clear()
            worksheet.update('A1', save_data)
            st.success("✅ 기록되었습니다!")
            st.rerun()

# 7. 상세 내역 관리
st.subheader("📑 상세 내역 관리")
if not df.empty:
    edited_df = st.data_editor(
        df, use_container_width=True, num_rows="dynamic",
        column_config={
            "date": st.column_config.DateColumn("날짜", format="YYYY-MM-DD"),
            "category": st.column_config.SelectboxColumn("구분", options=["수익", "지출", "저축-적금", "저축-투자"]),
            "amount": st.column_config.NumberColumn("금액", format="%d원"),
        },
        hide_index=True,
    )
    if st.button("💾 변경사항 저장하기"):
        save_df = edited_df.copy()
        save_df['date'] = pd.to_datetime(save_df['date']).dt.date
        save_df = save_df.sort_values('date')
        save_data = [save_df.columns.values.tolist()] + save_df.astype(str).values.tolist()
        worksheet.clear()
        worksheet.update('A1', save_data)
        st.success("✅ 동기화 완료!")
        st.rerun()
else:
    st.info("데이터가 없습니다.")

st.divider()

# 8. 하단 통계 분석
if not df.empty:
    st.subheader("📈 소비 및 저축 분석")
    exp_df = df[df['category'] == '지출'].copy()
    if not exp_df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📅 날짜별 지출 흐름")
            daily_exp = exp_df.groupby('date')['amount'].sum().reset_index()
            fig_bar = px.bar(daily_exp, x='date', y='amount', color_discrete_sequence=['#FF4B4B'])
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            st.markdown("#### 🍕 항목별 지출 비중")
            item_exp = exp_df.groupby('item')['amount'].sum().reset_index()
            fig_pie = px.pie(item_exp, values='amount', names='item', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
