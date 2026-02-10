import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="My WealthFlow", layout="wide")

# 2. 구글 시트 연결 (URL 확인)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit"
MY_TAB = "newbin" # 내가 사용할 탭 이름 고정

conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 데이터 로드 (캐시 없이 실시간 로드)
try:
    df = conn.read(spreadsheet=SHEET_URL, worksheet=MY_TAB, ttl=0)
    
    # 데이터가 비어있거나 헤더가 없을 경우 대비
    if df is None or df.empty:
        df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])
except Exception as e:
    st.error(f"구글 시트의 '{MY_TAB}' 탭을 읽어올 수 없습니다.")
    st.info("구글 시트에 'newbin' 탭이 있는지, 첫 줄에 제목이 있는지 확인해주세요.")
    st.stop()

# 데이터 전처리
df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
df = df.sort_values("날짜", ascending=False)

# 4. 메인 화면 구성
st.title("💰 나의 자산 관리 로그")

# 요약 수치 계산
inc = df[df["구분"] == "수익"]["금액"].sum()
exp = df[df["구분"] == "지출"]["금액"].sum()
sav = df[df["구분"] == "저축-적금"]["금액"].sum()
inv = df[df["구분"] == "저축-투자"]["금액"].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("💵 가용 현금", f"{inc - exp - sav - inv:,.0f}원")
m2.metric("🏦 누적 적금", f"{sav:,.0f}원")
m3.metric("📈 누적 투자", f"{inv:,.0f}원")
m4.metric("💸 누적 지출", f"{exp:,.0f}원")

st.divider()

# 5. 입력 및 관리 섹션
col_in, col_view = st.columns([1, 2])

with col_in:
    st.subheader("➕ 내역 추가")
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("날짜", value=date.today())
        g = st.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = st.text_input("항목")
        a = st.number_input("금액", min_value=0, step=1000)
        memo = st.text_input("메모")
        submit = st.form_submit_button("장부에 기록", use_container_width=True)
        
        if submit and i and a > 0:
            new_row = pd.DataFrame([{"날짜": d.strftime("%Y-%m-%d"), "구분": g, "항목": i, "금액": a, "메모": memo}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            # 즉시 업데이트
            conn.update(spreadsheet=SHEET_URL, worksheet=MY_TAB, data=updated_df)
            st.success("성공적으로 기록되었습니다!")
            st.rerun()

with col_view:
    st.subheader("📑 전체 내역")
    # 표에서 직접 수정 가능하도록 설정
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 변경사항 전체 저장", use_container_width=True):
        conn.update(spreadsheet=SHEET_URL, worksheet=MY_TAB, data=edited_df)
        st.success("시트와 동기화되었습니다!")
        st.rerun()

# 6. 통계 차트
st.divider()
st.subheader("📈 지출 분포")
exp_df = df[df["구분"] == "지출"]
if not exp_df.empty:
    fig = px.pie(exp_df, values="금액", names="항목", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("아직 지출 내역이 없습니다.")
