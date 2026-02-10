import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WF Mobile", layout="wide")

# 2. 구글 시트 연결
BASE_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 (아이디 입력)
user_input = st.sidebar.text_input("ID", value="").strip().lower()

user_mapping = {
    "newbin": "0",          
    "sheet2": "1542887265",
    "sheet3": "2039379199",
    "sheet4": "866978095"
}

if not user_input:
    st.info("ID를 입력해주세요.")
    st.stop()

if user_input not in user_mapping:
    st.error("ID 없음")
    st.stop()

target_gid = user_mapping[user_input]
TARGET_URL = f"{BASE_URL}?gid={target_gid}"

# 4. 데이터 로드
try:
    df = conn.read(spreadsheet=TARGET_URL, ttl=0)
    if df is None or df.empty:
        df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])
except:
    st.stop()

# 데이터 전처리
df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
df = df.sort_values("날짜", ascending=False)

# 5. 메인 화면 (에러 우회를 위해 텍스트 출력 최소화)
# st.title 대신 헤더를 사용하고, 특수기호를 최대한 뺍니다.
st.header(f"WealthFlow {user_input}")

# 요약 수치
inc = df[df["구분"] == "수익"]["금액"].sum()
exp = df[df["구분"] == "지출"]["금액"].sum()
sav = df[df["구분"] == "저축-적금"]["금액"].sum()
inv = df[df["구분"] == "저축-투자"]["금액"].sum()

# 모바일은 컬럼을 너무 많이 나누면 에러 확률이 높으므로 2개씩 배치
c1, c2 = st.columns(2)
c1.metric("Cash", f"{inc - exp - sav - inv:,.0f}")
c2.metric("Savings", f"{sav:,.0f}")
c1.metric("Invest", f"{inv:,.0f}")
c2.metric("Spend", f"{exp:,.0f}")

st.divider()

# 6. 내역 추가 폼
with st.form("add"):
    d = st.date_input("Date")
    g = st.selectbox("Type", ["수익", "지출", "저축-적금", "저축-투자"])
    i = st.text_input("Item")
    a = st.number_input("Amount", step=1000)
    sub = st.form_submit_button("Save", use_container_width=True)
    
    if sub and i:
        new = pd.DataFrame([{"날짜": d.strftime("%Y-%m-%d"), "구분": g, "항목": i, "금액": a, "메모": ""}])
        updated = pd.concat([df, new], ignore_index=True)
        conn.update(spreadsheet=TARGET_URL, data=updated)
        st.rerun()

# 7. 내역 보기 (st.data_editor가 모바일 에러의 주범일 수 있음 -> st.dataframe으로 변경 시도)
st.subheader("History")
# 에러가 계속되면 아래 data_editor를 st.dataframe(df)로 바꿔보세요.
edited_df = st.data_editor(df, use_container_width=True)
if st.button("Sync All"):
    conn.update(spreadsheet=TARGET_URL, data=edited_df)
    st.rerun()

# 8. 차트 (Plotly는 모바일 호환성이 좋음)
exp_df = df[df["구분"] == "지출"]
if not exp_df.empty:
    fig = px.pie(exp_df, values="금액", names="항목")
    st.plotly_chart(fig, use_container_width=True)
