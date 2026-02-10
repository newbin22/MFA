import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

# 2. 구글 시트 연결 (가장 표준적인 방식)
# 라이브러리가 Secrets의 [connections.gsheets] 섹션을 자동으로 읽도록 둡니다.
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 설정
st.sidebar.title("💎 WealthFlow Pro")
user_input = st.sidebar.text_input("접속 아이디", value="").strip().lower()

user_mapping = {
    "newbin": "newbin", 
    "sheet2": "sheet2",
    "sheet3": "sheet3"
}

if not user_input:
    st.title("💰 자산관리 시스템")
    st.info("왼쪽 사이드바에 아이디를 입력해주세요.")
    st.stop()

target_worksheet = user_mapping.get(user_input)
if not target_worksheet:
    st.error(f"'{user_input}'은(는) 등록되지 않은 아이디입니다.")
    st.stop()

# 4. 데이터 로드
try:
    # spreadsheet 인자를 비워두면 Secrets의 spreadsheet 값을 자동으로 사용합니다.
    df = conn.read(worksheet=target_worksheet, ttl=0)
except Exception as e:
    st.error("❌ 데이터를 불러올 수 없습니다.")
    st.code(str(e))
    st.stop()

# 데이터 전처리
if df is not None and not df.empty:
    df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
    df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
else:
    df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])

# 5. 메인 화면 및 입력 폼
st.title(f"📊 {user_input.upper()}님 대시보드")

with st.form("add_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    d = col1.date_input("날짜", value=date.today())
    g = col2.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
    i = col3.text_input("항목")
    a = st.number_input("금액", min_value=0, step=1000)
    memo = st.text_input("메모")
    submit = st.form_submit_button("장부에 기록", use_container_width=True)

    if submit and i and a > 0:
        new_row = pd.DataFrame([{"날짜": d.strftime("%Y-%m-%d"), "구분": g, "항목": i, "금액": a, "메모": memo}])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        # 저장 시 날짜 포맷팅
        updated_df["날짜"] = pd.to_datetime(updated_df["날짜"]).dt.strftime("%Y-%m-%d")
        
        # 중요: 업데이트 시에도 worksheet만 지정합니다.
        conn.update(worksheet=target_worksheet, data=updated_df)
        st.success("✅ 저장 완료!")
        st.rerun()

st.divider()
st.subheader("📑 내역")
st.dataframe(df, use_container_width=True)

