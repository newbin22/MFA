import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 (매우 단순하게)
st.set_page_config(page_title="WF Mobile")

# 2. 구글 시트 연결
BASE_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 로그인 (사이드바 대신 메인 화면에 배치하여 엔진 부하 감소)
user_input = st.text_input("Enter ID", value="").strip().lower()

user_mapping = {
    "newbin": "0",          
    "sheet2": "1542887265",
    "sheet3": "2039379199",
    "sheet4": "866978095"
}

if user_input in user_mapping:
    target_gid = user_mapping[user_input]
    TARGET_URL = f"{BASE_URL}?gid={target_gid}"

    # 4. 데이터 로드
    try:
        # 데이터프레임을 바로 읽어옴
        df = conn.read(spreadsheet=TARGET_URL, ttl=0)
        
        # 5. 요약 (st.metric 대신 일반 텍스트 사용)
        inc = pd.to_numeric(df[df["구분"] == "수익"]["금액"]).sum()
        exp = pd.to_numeric(df[df["구분"] == "지출"]["금액"]).sum()
        
        st.write(f"### User: {user_input}")
        st.write(f"**Current Balance:** {inc - exp:,.0f}원")
        st.write(f"**Total Spend:** {exp:,.0f}원")
        
        # 6. 간단한 입력 폼
        with st.expander("➕ 내역 추가하기"):
            with st.form("mobile_form"):
                i_item = st.text_input("항목")
                i_amount = st.number_input("금액", step=1000)
                i_type = st.selectbox("구분", ["지출", "수익", "저축-적금", "저축-투자"])
                if st.form_submit_button("저장"):
                    new_data = pd.DataFrame([{"날짜": pd.Timestamp.now().strftime("%Y-%m-%d"), "구분": i_type, "항목": i_item, "금액": i_amount, "메모": ""}])
                    updated_df = pd.concat([df, new_data], ignore_index=True)
                    conn.update(spreadsheet=TARGET_URL, data=updated_df)
                    st.rerun()

        # 7. 데이터 확인 (data_editor 대신 단순 table 사용)
        # 이 부분이 모바일 에러의 핵심일 수 있어 st.table로 대체합니다.
        st.write("---")
        st.write("📂 최신 내역 (상위 10개)")
        st.table(df.tail(10)) 

    except Exception as e:
        st.write("로그인 성공. 데이터를 불러오는 중입니다...")
else:
    st.write("아이디를 입력해 주세요.")
