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
    # 400 에러 방지를 위해 worksheet를 명시하고 캐시를 초기화(ttl=0)합니다.
    df = conn.read(worksheet=target_worksheet, ttl=0)
    
    # 만약 시트가 비어있어 None이 반환되면 구조를 잡아줍니다.
    if df is None or df.empty:
        df = pd.DataFrame(columns=["date", "category", "item", "amount", "memo"])
except Exception as e:
    st.error(f"데이터 로드 실패 (HTTP 400 가능성)")
    st.info("시트의 1행이 [date, category, item, amount, memo] 인지 확인하세요.")
    st.code(str(e))
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
                # 새 행 생성 (영어 컬럼명에 맞춤)
                new_row = pd.DataFrame([{
                    "date": str(d),
                    "category": str(g),
                    "item": str(i),
                    "amount": int(a),
                    "memo": str(memo)
                }])
                
                # 기존 데이터와 결합
                # 데이터가 완전히 비어있을 때를 대비해 모든 컬럼 타입을 맞춥니다.
                df_to_update = pd.concat([df, new_row], ignore_index=True)
                
                # 구글 시트 업데이트
                conn.update(worksheet=target_worksheet, data=df_to_update)
                
                st.success("✅ 저장 완료!")
                st.rerun()
            except Exception as save_error:
                st.error("⚠️ 저장 실패 (400 Bad Request)")
                st.code(str(save_error))

st.divider()
st.subheader("📑 최근 내역")
if not df.empty:
    # 화면 표시용으로만 컬럼명을 다시 한글로 보여줄 수 있습니다.
    display_df = df.copy()
    display_df.columns = ["날짜", "구분", "항목", "금액", "메모"]
    st.dataframe(display_df.sort_values("날짜", ascending=False), use_container_width=True)
else:
    st.write("데이터가 없습니다.")
