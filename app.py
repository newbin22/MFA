import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

# 2. 구글 시트 연결 (Secrets 설정을 자동으로 불러옴)
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 로그인 및 탭 정보
st.sidebar.title("💎 WealthFlow Pro")
user_input = st.sidebar.text_input("접속 아이디", value="").strip().lower()

# 각 아이디별 실제 구글 시트의 [탭 이름]을 적어주세요.
user_mapping = {
    "newbin": "newbin",
    "sheet2": "sheet2",
    "sheet3": "sheet3"
}

if not user_input or user_input not in user_mapping:
    st.title("💰 자산관리 시스템")
    st.info("왼쪽 사이드바에 등록된 아이디를 입력해주세요.")
    st.stop()

target_name = user_mapping[user_input]

# 4. 데이터 로드
try:
    # 워크시트 이름을 직접 지정하여 읽어옵니다.
    df = conn.read(worksheet=target_name, ttl=0)
    if df is None or df.empty:
        df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])
except Exception as e:
    st.error("데이터를 불러올 수 없습니다. 시트 공유 설정과 탭 이름을 확인하세요.")
    st.stop()

# 데이터 전처리
df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)

st.title(f"📊 {user_input}님 대시보드")

# 5. 데이터 입력 폼
with st.form("add_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    d = col1.date_input("날짜", value=date.today())
    g = col2.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
    i = col3.text_input("항목")
    
    col4, col5 = st.columns([1, 2])
    a = col4.number_input("금액", min_value=0, step=1000)
    memo = col5.text_input("메모")
    
    submit = st.form_submit_button("장부에 기록", use_container_width=True)

    if submit and i and a > 0:
        # 새 데이터 생성
        new_row = pd.DataFrame([{
            "날짜": d.strftime("%Y-%m-%d"),
            "구분": g,
            "항목": i,
            "금액": a,
            "메모": memo
        }])
        
        # 기존 데이터와 합치기
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # 날짜 형식 정리 (저장 전)
        updated_df["날짜"] = updated_df["날짜"].dt.strftime("%Y-%m-%d")
        
        # 시트에 업데이트 (인증 정보가 있으므로 이제 에러가 나지 않습니다)
        conn.update(worksheet=target_name, data=updated_df)
        st.success("✅ 성공적으로 저장되었습니다!")
        st.rerun()

st.divider()

# 6. 상세 내역 보기 및 편집
st.subheader("📑 내역 관리")
edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")

if st.button("💾 변경사항 전체 저장"):
    # 편집된 데이터 날짜 처리 후 저장
    edited_df["날짜"] = pd.to_datetime(edited_df["날짜"]).dt.strftime("%Y-%m-%d")
    conn.update(worksheet=target_name, data=edited_df)
    st.success("✅ 시트가 동기화되었습니다!")
    st.rerun()
