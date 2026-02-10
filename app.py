import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

# 2. 구글 시트 연결
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

if user_input not in user_mapping:
    st.error(f"'{user_input}'은(는) 등록되지 않은 아이디입니다.")
    st.stop()

target_worksheet = user_mapping[user_input]

# 4. 데이터 로드 (들여쓰기 수정 완료)
# app.py의 36~40번 라인 근처 수정
try:
    # 워크시트 이름을 빼고 가장 기본형으로 읽어봅니다.
    df = conn.read(ttl=0)
except Exception as e:
    st.error(f"상세 에러: {e}")
    st.stop()

# 데이터 전처리
if df is not None and not df.empty:
    df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
    df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
else:
    df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])

# 5. 메인 화면 구성
st.title(f"📊 {user_input.upper()}님 대시보드")

with st.form("add_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    d = col1.date_input("날짜", value=date.today())
    g = col2.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
    i = col3.text_input("항목")
    
    col4, col5 = st.columns([1, 2])
    a = col4.number_input("금액", min_value=0, step=1000)
    memo = col5.text_input("메모")
    
    submit = st.form_submit_button("장부에 기록", use_container_width=True)

    if submit:
        if not i:
            st.warning("항목을 입력해주세요.")
        elif a <= 0:
            st.warning("금액을 입력해주세요.")
        else:
            try:
                new_row = pd.DataFrame([{
                    "날짜": d.strftime("%Y-%m-%d"),
                    "구분": g,
                    "항목": i,
                    "금액": a,
                    "메모": memo
                }])
                
                updated_df = pd.concat([df, new_row], ignore_index=True)
                # 저장 전 날짜 포맷 정리
                updated_df["날짜"] = pd.to_datetime(updated_df["날짜"]).dt.strftime("%Y-%m-%d")
                
                conn.update(worksheet=target_worksheet, data=updated_df)
                st.success("✅ 성공적으로 저장되었습니다!")
                st.rerun()
            except Exception as save_error:
                st.error(f"저장 중 오류 발생: {save_error}")

st.divider()

# 6. 내역 보기
st.subheader("📑 최근 내역")
if not df.empty:
    st.dataframe(df.sort_values("날짜", ascending=False), use_container_width=True)
else:
    st.info("기록된 데이터가 없습니다.")

