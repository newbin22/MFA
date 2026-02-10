import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Shared", layout="wide")

# 2. 구글 시트 연결
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 로그인 및 탭 매핑
st.sidebar.title("💎 WealthFlow")
user_input = st.sidebar.text_input("접속 아이디를 입력하세요", value="").strip()

# 아이디별 탭 순서 매핑 (0: 첫 번째 탭, 1: 두 번째 탭...)
# 중요: 구글 시트의 실제 탭 순서와 일치해야 합니다.
user_mapping = {
    "newbin": 0,   # 첫 번째 탭에 연결
    "sheet2": 1    # 두 번째 탭에 연결
}

if not user_input:
    st.title("💰 자산관리 시스템")
    st.info("왼쪽 사이드바에 아이디를 입력해주세요.")
    st.stop()

if user_input not in user_mapping:
    st.error(f"❌ '{user_input}'은 등록되지 않은 아이디입니다.")
    st.stop()

# 해당 아이디에 할당된 탭 번호 가져오기
target_index = user_mapping[user_input]

# 4. 데이터 로드 (탭 번호 기반)
try:
    # 모든 탭 목록을 가져와서 지정된 순서의 탭 이름을 알아냅니다.
    all_worksheets = conn.list_worksheets(spreadsheet=SHEET_URL)
    target_sheet_name = all_worksheets[target_index]
    
    # 해당 탭 이름으로 데이터 읽기
    df = conn.read(spreadsheet=SHEET_URL, worksheet=target_sheet_name, ttl=0)
    
    if df is None or df.empty:
        df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])
except Exception as e:
    st.error("데이터 로드 중 오류가 발생했습니다.")
    st.write(f"상세 에러: {e}")
    st.stop()

# 데이터 전처리
df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
df = df.sort_values("날짜", ascending=False)

# 5. 메인 화면 구성
st.title(f"📊 {user_input}님 전용 장부")

# 요약 수치
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

# 6. 데이터 입력 및 편집
col_in, col_view = st.columns([1, 2])

with col_in:
    st.subheader("➕ 내역 추가")
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("날짜", value=date.today())
        g = st.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = st.text_input("항목")
        a = st.number_input("금액", min_value=0, step=1000)
        memo = st.text_input("메모")
        submit = st.form_submit_button("기록하기", use_container_width=True)
        
        if submit and i and a > 0:
            new_row = pd.DataFrame([{"날짜": d.strftime("%Y-%m-%d"), "구분": g, "항목": i, "금액": a, "메모": memo}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet_name, data=updated_df)
            st.success("기록 완료!")
            st.rerun()

with col_view:
    st.subheader("📑 내역 관리")
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 전체 저장", use_container_width=True):
        conn.update(spreadsheet=SHEET_URL, worksheet=target_sheet_name, data=edited_df)
        st.success("동기화 완료!")
        st.rerun()

# 7. 차트
st.subheader("📈 지출 현황")
exp_df = df[df["구분"] == "지출"]
if not exp_df.empty:
    fig = px.pie(exp_df, values="금액", names="항목", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
