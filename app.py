import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Multi-User", layout="wide")

# 2. 구글 시트 연결
BASE_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 로그인 및 탭 정보 매핑 (GID와 이름을 매칭)
st.sidebar.title("💎 WealthFlow Pro")
user_input = st.sidebar.text_input("접속 아이디를 입력하세요", value="").strip().lower()

# [수정] 각 아이디별로 GID(읽기용)와 실제 시트의 탭 이름(쓰기용)을 정확히 적어주세요.
user_mapping = {
    "newbin": {"gid": "0", "name": "newbin"},
    "sheet2": {"gid": "1542887265", "name": "sheet2"},
    "sheet3": {"gid": "2039379199", "name": "sheet3"},
    "sheet4": {"gid": "866978095", "name": "sheet4"}
}

if not user_input:
    st.title("💰 자산관리 시스템")
    st.info("왼쪽 사이드바에 아이디를 입력해주세요.")
    st.stop()

if user_input not in user_mapping:
    st.error(f"❌ '{user_input}'은 등록되지 않은 ID입니다.")
    st.stop()

# 해당 사용자의 정보 가져오기
target_gid = user_mapping[user_input]["gid"]
target_name = user_mapping[user_input]["name"]  # 쓰기 작업에 사용될 실제 탭 이름
READ_URL = f"{BASE_URL}?gid={target_gid}"

# 4. 데이터 로드
try:
    # 읽을 때는 GID가 포함된 URL을 사용 (가장 안정적)
    df = conn.read(spreadsheet=READ_URL, ttl=0)
    
    if df is None or df.empty:
        df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])
except Exception as e:
    st.error("데이터 로드 중 오류가 발생했습니다.")
    st.stop()

# 데이터 전처리
df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
df = df.sort_values("날짜", ascending=False)

st.title(f"📊 {user_input}님 전용 대시보드")

# 요약 수치 계산 부분 (기존과 동일)
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
        submit = st.form_submit_button("장부에 기록", use_container_width=True)
        
        if submit and i and a > 0:
            new_row = pd.DataFrame([{"날짜": d.strftime("%Y-%m-%d"), "구분": g, "항목": i, "금액": a, "메모": memo}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            
            # [수정] 업데이트 시에는 GID 주소가 아닌 원본 URL과 실제 시트 이름을 전달합니다.
            conn.update(spreadsheet=BASE_URL, worksheet=target_name, data=updated_df)
            st.success("기록 완료!")
            st.rerun()

with col_view:
    st.subheader("📑 상세 내역 관리")
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 전체 변경사항 저장", use_container_width=True):
        # [수정] 업데이트 시에는 원본 URL과 실제 시트 이름을 사용합니다.
        conn.update(spreadsheet=BASE_URL, worksheet=target_name, data=edited_df)
        st.success("구글 시트와 동기화되었습니다!")
        st.rerun()

st.divider()
st.subheader("📈 지출 분포")
exp_df = df[df["구분"] == "지출"]
if not exp_df.empty:
    fig = px.pie(exp_df, values="금액", names="항목", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
