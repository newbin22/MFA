import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

# 2. 구글 시트 연결
# (Secrets에 [connections.gsheets] 설정이 정확해야 합니다)
conn = st.connection("gsheets", type=GSheetsConnection, spreadsheet="https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit")

# 3. 사이드바 설정
st.sidebar.title("💎 WealthFlow Pro")
user_input = st.sidebar.text_input("접속 아이디", value="").strip().lower()

# [중요] 여기에 적힌 이름이 실제 구글 시트 하단 '탭 이름'과 정확히 일치해야 합니다.
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

# 4. 데이터 로드 및 에러 추적
try:
    # 워크시트 이름을 지정하여 데이터를 읽어옵니다.
    df = conn.read(worksheet=target_worksheet, ttl=0)
    
except Exception as e:
    st.error("❌ 데이터를 불러올 수 없습니다.")
    st.info("아래 에러 내용을 확인하여 조치하세요:")
    # 실제 에러 메시지를 화면에 출력합니다.
    st.code(str(e))
    
    if "WorksheetNotFound" in str(e):
        st.warning(f"팁: 시트에 '{target_worksheet}'라는 이름의 탭이 있는지 확인하세요.")
    elif "Permission denied" in str(e) or "SpreadsheetNotFound" in str(e):
        st.warning("팁: 서비스 계정 이메일을 구글 시트 [공유]에 '편집자'로 추가했는지 확인하세요.")
    st.stop()

# 데이터 전처리 (에러 방지용)
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
                # 새 행 추가 데이터 생성
                new_row = pd.DataFrame([{
                    "날짜": d.strftime("%Y-%m-%d"),
                    "구분": g,
                    "항목": i,
                    "금액": a,
                    "메모": memo
                }])
                
                # 기존 데이터와 합치기
                updated_df = pd.concat([df, new_row], ignore_index=True)
                # 날짜 열을 문자열로 변환 (저장용)
                updated_df["날짜"] = pd.to_datetime(updated_df["날짜"]).dt.strftime("%Y-%m-%d")
                
                # 시트 업데이트
                conn.update(worksheet=target_worksheet, data=updated_df)
                st.success("✅ 성공적으로 저장되었습니다!")
                st.rerun()
            except Exception as save_error:
                st.error(f"저장 중 오류 발생: {save_error}")

st.divider()

# 6. 내역 보기
st.subheader("📑 최근 내역")
st.dataframe(df.sort_values("날짜", ascending=False), use_container_width=True)

