import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 수식 기능 비활성화 시도
# (참고: Streamlit 자체 설정으로 수식 엔진을 끌 수는 없으나 텍스트 표시 방식을 단순화합니다.)
st.set_page_config(page_title="WealthFlow Mobile-Ready", layout="wide")

# 2. 구글 시트 연결
BASE_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 구성
st.sidebar.title("💎 WealthFlow Pro")
user_input = st.sidebar.text_input("접속 아이디", value="").strip().lower()

user_mapping = {
    "newbin": "0",          
    "sheet2": "1542887265",
    "sheet3": "2039379199",
    "sheet4": "866978095"
}

if not user_input:
    st.info("왼쪽 사이드바에서 ID를 입력해주세요.")
    st.stop()

if user_input not in user_mapping:
    st.error("등록되지 않은 ID입니다.")
    st.stop()

target_gid = user_mapping[user_input]
TARGET_URL = f"{BASE_URL}?gid={target_gid}"

# 4. 데이터 로드
try:
    df = conn.read(spreadsheet=TARGET_URL, ttl=0)
    if df is None or df.empty:
        df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])
except:
    st.error("데이터 로딩 실패")
    st.stop()

# 데이터 전처리
df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
df = df.sort_values("날짜", ascending=False)

# 5. 메인 화면 (수식 에러 방지를 위해 st.write 대신 st.text나 단순 포맷 사용)
# f-string 내에 $ 기호 등이 들어가지 않도록 주의합니다.
st.subheader(f"User: {user_input}")

# 요약 수치 (Metric 컴포넌트 사용)
inc = df[df["구분"] == "수익"]["금액"].sum()
exp = df[df["구분"] == "지출"]["금액"].sum()
sav = df[df["구분"] == "저축-적금"]["금액"].sum()
inv = df[df["구분"] == "저축-투자"]["금액"].sum()

m1, m2 = st.columns(2) # 모바일 가독성을 위해 2열로 배치
m1.metric("가용 현금", f"{inc - exp - sav - inv:,.0f}")
m1.metric("누적 적금", f"{sav:,.0f}")
m2.metric("누적 투자", f"{inv:,.0f}")
m2.metric("누적 지출", f"{exp:,.0f}")

st.divider()

# 6. 입력창 (모바일에서 가장 안정적임)
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
        conn.update(spreadsheet=TARGET_URL, data=updated_df)
        st.success("기록 완료!")
        st.rerun()

st.divider()

# 7. 상세 내역 (에러를 유발할 수 있는 data_editor 대신 단순 dataframe 사용 고려)
st.subheader("📑 상세 내역")
# 만약 여전히 에러가 난다면 st.data_editor를 st.dataframe으로 바꿔보세요.
edited_df = st.data_editor(df, use_container_width=True)
if st.button("💾 변경사항 저장", use_container_width=True):
    conn.update(spreadsheet=TARGET_URL, data=edited_df)
    st.success("저장 완료!")
    st.rerun()

# 8. 차트
if not exp_df.empty:
    fig = px.pie(df[df["구분"] == "지출"], values="금액", names="항목", hole=0.4)
    # 모바일 렌더링 안정성을 위해 가로폭 설정
    st.plotly_chart(fig, use_container_width=True)
