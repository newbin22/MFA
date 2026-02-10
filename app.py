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

if not user_input or user_input not in user_mapping:
    st.title("💰 자산관리 시스템")
    st.info("왼쪽 사이드바에 아이디를 입력해주세요.")
    st.stop()

target_worksheet = user_mapping[user_input]

# 4. 데이터 로드
try:
    # 최초 로드 시 데이터가 없을 경우를 대비해 기본값 설정
    df = conn.read(worksheet=target_worksheet, ttl=0)
    if df is None:
        df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])
except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    st.stop()

# 5. 메인 화면 및 입력 폼
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
        if not i or a <= 0:
            st.warning("항목과 금액을 정확히 입력해주세요.")
        else:
            try:
                # 1단계: 새 행 생성
                new_row = pd.DataFrame([{
                    "날짜": str(d), # 날짜를 단순 문자열로 변환
                    "구분": str(g),
                    "항목": str(i),
                    "금액": int(a), # 금액을 순수 정수로 변환
                    "메모": str(memo)
                }])
                
                # 2단계: 기존 데이터와 결합 (빈 데이터프레임 처리 포함)
                if df is not None and not df.empty:
                    # 모든 기존 데이터의 형식을 단순화하여 합칩니다.
                    df["날짜"] = df["날짜"].astype(str)
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                else:
                    updated_df = new_row
                
                # 3단계: 구글 시트로 업데이트 (핵심!)
                # 여기서 에러가 난다면 시트의 1행(헤더) 이름이 "날짜, 구분, 항목, 금액, 메모"와 다른지 확인해야 합니다.
                conn.update(worksheet=target_worksheet, data=updated_df)
                
                st.success("✅ 저장 완료!")
                st.rerun()
            except Exception as save_error:
                st.error("⚠️ 저장 실패 (400 Bad Request)")
                st.info("시트의 1행(헤더) 제목들이 코드와 일치하는지 확인하세요: [날짜, 구분, 항목, 금액, 메모]")
                st.code(str(save_error))

st.divider()
st.subheader("📑 최근 내역")
if df is not None and not df.empty:
    st.dataframe(df.sort_values("날짜", ascending=False), use_container_width=True)

