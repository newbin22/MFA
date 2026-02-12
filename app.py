import streamlit as st
import pandas as pd
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import plotly.express as px

# 1. 페이지 설정 및 모바일 최적화 레이아웃
st.set_page_config(page_title="WealthFlow Pro", layout="wide", initial_sidebar_state="collapsed")

# 모바일용 CSS: 텍스트 크기 가변형 조정 및 여백 최적화
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 5vw !important; }
    [data-testid="stMetricLabel"] { font-size: 3vw !important; }
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    /* 모바일에서 표 가독성 향상 */
    .stDataEditor { width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 구글 시트 연결 (캐싱 적용으로 모바일 끊김 방지)
@st.cache_resource
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
    st.error("연결 오류: 새로고침을 해주세요.")
    st.stop()

# 3. 사이드바 설정 (아이디 입력 및 자산 설정)
with st.sidebar:
    st.title("💎 WealthFlow Pro")
    user_input = st.text_input("아이디 입력", value="").strip().lower()
    
    st.divider()
    st.subheader("⚙️ 자산 설정")
    initial_asset = st.number_input("기초 현금 (원)", min_value=0, value=1000000, step=100000)
    initial_savings = st.number_input("누적 저축 (원)", min_value=0, value=0, step=100000)

user_mapping = {"newbin": "newbin", "sheet2": "sheet2", "sheet3": "sheet3"}

if not user_input or user_input not in user_mapping:
    st.info("👈 왼쪽 메뉴에서 아이디를 입력해주세요.")
    st.stop()

target_worksheet_name = user_mapping[user_input]

# 4. 데이터 로드 (에러 방지용)
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
    except:
        return pd.DataFrame(columns=["date", "category", "item", "amount", "memo"]), None

df, worksheet = load_data(target_worksheet_name)

# 5. 요약 대시보드 (모바일에선 2열씩 배치)
st.subheader(f"📊 {user_input.upper()}님 현황")

total_income = df[df['category'] == '수익']['amount'].sum()
total_expense = df[df['category'] == '지출']['amount'].sum()
monthly_savings = df[df['category'].str.contains('저축', na=False)]['amount'].sum()
total_savings_display = initial_savings + monthly_savings
current_balance = initial_asset + total_income - total_expense - monthly_savings

col1, col2 = st.columns(2)
col1.metric("현재 잔액", f"{current_balance:,}원")
col2.metric("총 수익", f"{total_income:,}원")
col3, col4 = st.columns(2)
col3.metric("총 지출", f"{total_expense:,}원")
col4.metric("총 저축", f"{total_savings_display:,}원")

st.divider()

# 6. 월 마감 기능 (사이드바 하단)
if st.sidebar.button("🚀 이번 달 마감 (백업)"):
    if not df.empty:
        archive_name = f"{user_input}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        new_ws = sh.add_worksheet(title=archive_name, rows="100", cols="20")
        save_data = [df.columns.values.tolist()] + df.astype(str).values.tolist()
        new_ws.update('A1', save_data)
        worksheet.clear()
        worksheet.update('A1', [["date", "category", "item", "amount", "memo"]])
        st.sidebar.success("마감 완료!")
        st.rerun()

# 7. 입력 및 편집 (모바일 대응)
with st.expander("📝 내역 추가/수정", expanded=False):
    # 입력 폼
    with st.form("mobile_form", clear_on_submit=True):
        d = st.date_input("날짜", value=date.today())
        g = st.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = st.text_input("항목")
        a = st.number_input("금액", min_value=0, step=1000)
        m = st.text_input("메모")
        if st.form_submit_button("저장하기", use_container_width=True):
            new_row = pd.DataFrame([{"date": d, "category": g, "item": i, "amount": int(a), "memo": m}])
            full_df = pd.concat([df, new_row], ignore_index=True)
            full_df = full_df.sort_values('date')
            worksheet.clear()
            worksheet.update('A1', [full_df.columns.tolist()] + full_df.astype(str).values.tolist())
            st.rerun()

# 8. 데이터 관리 테이블
st.subheader("📑 상세 내역")
if not df.empty:
    edited_df = st.data_editor(df, use_container_width=True, hide_index=True)
    if st.button("💾 표 수정사항 저장", use_container_width=True):
        save_df = edited_df.sort_values('date')
        worksheet.clear()
        worksheet.update('A1', [save_df.columns.tolist()] + save_df.astype(str).values.tolist())
        st.rerun()

# 9. 통계 그래프 (모바일은 세로로 배치)
if not df.empty:
    st.divider()
    st.subheader("📈 분석")
    exp_df = df[df['category'] == '지출'].copy()
    if not exp_df.empty:
        fig1 = px.bar(exp_df.groupby('date')['amount'].sum().reset_index(), x='date', y='amount', title="일별 지출")
        st.plotly_chart(fig1, use_container_width=True)
        
        fig2 = px.pie(exp_df.groupby('item')['amount'].sum().reset_index(), values='amount', names='item', title="항목 비중")
        st.plotly_chart(fig2, use_container_width=True)
