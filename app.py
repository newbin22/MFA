import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Multi-User", layout="wide")

# CSS 스타일 (세련된 디자인 유지)
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff; border-radius: 12px; padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .daily-box {
        padding: 10px 15px; border-radius: 8px; background: white; margin-bottom: 5px;
        border-left: 5px solid #4F46E5; display: flex; justify-content: space-between;
    }
    .plus-val { color: #d9534f; font-weight: bold; }
    .minus-val { color: #0275d8; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# =============================
# 2. 로그인 및 사용자 식별
# =============================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit?gid=0#gid=0"

st.sidebar.title("🔐 개인 로그인")
user_id = st.sidebar.text_input("아이디(영문/숫자)", value="").strip()

if not user_id:
    st.title("💰 WealthFlow Pro")
    st.info("왼쪽 사이드바에서 아이디를 입력하여 본인의 장부에 접속하세요.")
    st.stop()

# =============================
# 3. 데이터 로드 (사용자별 탭 접근)
# =============================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 사용자 아이디와 동일한 이름의 시트 탭을 읽어옴
    df = conn.read(spreadsheet=SHEET_URL, worksheet=user_id, ttl="0s")
except Exception:
    # 해당 탭이 없으면 빈 데이터프레임 생성 (처음 접속하는 유저)
    df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])

# 데이터 클리닝
if not df.empty:
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
    df = df.sort_values("날짜", ascending=False)

# =============================
# 4. 사이드바: 내역 추가
# =============================
with st.sidebar:
    st.success(f"👤 {user_id} 님 환영합니다!")
    st.divider()
    
    with st.expander("💰 기초 자산 설정"):
        init_asset = st.number_input("현재 현금", value=0, step=10000)
        init_saving = st.number_input("기존 적금", value=0, step=10000)
        init_invest = st.number_input("기존 투자", value=0, step=10000)
    
    st.subheader("➕ 내역 추가")
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("날짜", value=date.today())
        g = st.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = st.text_input("항목")
        a = st.number_input("금액", min_value=0, step=1000)
        m = st.text_input("메모")
        
        if st.form_submit_button("기록하기", use_container_width=True):
            if i and a > 0:
                new_row = pd.DataFrame([{
                    "날짜": d.strftime("%Y-%m-%d"), "구분": g, "항목": i, "금액": a, "메모": m
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                # 사용자 아이디와 이름이 같은 탭에 저장 (없으면 자동 생성됨)
                conn.update(spreadsheet=SHEET_URL, worksheet=user_id, data=updated_df)
                st.success("데이터가 저장되었습니다!")
                st.rerun()

# =============================
# 5. 메인 대시보드 시각화 (기존 로직 유지)
# =============================
st.title(f"📊 {user_id}님의 재무 현황")

# 상단 메트릭 계산
inc = df[df["구분"] == "수익"]["금액"].sum()
exp = df[df["구분"] == "지출"]["금액"].sum()
sav = df[df["구분"] == "저축-적금"]["금액"].sum()
inv = df[df["구분"] == "저축-투자"]["금액"].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("💵 가용 현금", f"{init_asset + inc - exp - sav - inv:,.0f}원")
m2.metric("🏦 총 적금", f"{init_saving + sav:,.0f}원")
m3.metric("📈 총 투자", f"{init_invest + inv:,.0f}원")
m4.metric("💸 총 지출", f"{exp:,.0f}원")

st.divider()

# 상세 내역 편집기
st.subheader("📑 상세 거래 내역")
if not df.empty:
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="editor")
    if st.button("💾 변경사항 저장", use_container_width=True):
        conn.update(spreadsheet=SHEET_URL, worksheet=user_id, data=edited_df)
        st.success("수정사항이 반영되었습니다!")
        st.rerun()

st.divider()

# 시각화 (지출 비중 & 일별 요약)
c1, c2 = st.columns(2)
with c1:
    st.subheader("🍕 지출 비중")
    exp_df = df[df["구분"] == "지출"]
    if not exp_df.empty:
        fig = px.pie(exp_df, values="금액", names="항목", hole=0.5)
        st.plotly_chart(fig, use_container_width=True)
with c2:
    st.subheader("🗓 날짜별 요약")
    if not df.empty:
        summary = df.copy()
        summary['net'] = summary.apply(lambda x: x['금액'] if x['구분'] == '수익' else (-x['금액'] if x['구분'] == '지출' else 0), axis=1)
        daily = summary.groupby(summary['날짜'].dt.date)['net'].sum().reset_index().head(10)
        for _, r in daily.iterrows():
            st.markdown(f"<div class='daily-box'><span>📅 {r['날짜']}</span><span class='{'plus-val' if r['net']>=0 else 'minus-val'}'>{r['net']:+,.0f}원</span></div>", unsafe_allow_html=True)
