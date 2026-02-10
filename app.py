import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Shared", layout="wide")

# 2. 구글 시트 연결
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 로그인 (단순 아이디 방식)
st.sidebar.title("💎 WealthFlow")
access_id = st.sidebar.text_input("접속 아이디를 입력하세요", value="").strip()

if not access_id:
    st.title("💰 자산관리를 위한 웹페이지")
    st.info("왼쪽 사이드바에 지정 받은 ID를 입력해주세요.")
    st.stop()

# 4. 데이터 로드 (입력한 아이디와 이름이 같은 시트 탭을 가져옴)
try:
    # 아이디가 'family'라면 구글 시트의 'family' 탭을 읽어옵니다.
    df = conn.read(spreadsheet=SHEET_URL, worksheet=access_id, ttl="0s")
except:
    # 탭이 없을 경우 에러 대신 빈 양식을 보여줌
    st.error(f"'{access_id}'라는 이름의 시트 탭을 찾을 수 없습니다. 구글 시트 하단 탭 이름을 확인해주세요.")
    st.stop()

# 데이터 전처리
if not df.empty:
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
    df = df.sort_values("날짜", ascending=False)

# 5. 메인 대시보드 표시
st.title(f"📊 {access_id} 장부 대시보드")

# 상단 요약 수치
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

# 데이터 입력 및 확인
col_in, col_view = st.columns([1, 2])

with col_in:
    st.subheader("➕ 내역 추가")
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("날짜", value=date.today())
        g = st.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = st.text_input("항목")
        a = st.number_input("금액", min_value=0, step=1000)
        submit = st.form_submit_button("장부에 기록", use_container_width=True)
        
        if submit and i and a > 0:
            new_data = pd.DataFrame([{"날짜": d.strftime("%Y-%m-%d"), "구분": g, "항목": i, "금액": a, "메모": ""}])
            updated_df = pd.concat([df, new_data], ignore_index=True)
            # 공유된 링크 권한만으로 저장이 안 될 경우, 아래 버튼으로 수동 업데이트 안내
            conn.update(spreadsheet=SHEET_URL, worksheet=access_id, data=updated_df)
            st.success("기록되었습니다! (반영 안 될 시 새로고침)")
            st.rerun()

with col_view:
    st.subheader("📑 상세 내역")
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 변경사항 전체 저장", use_container_width=True):
        conn.update(spreadsheet=SHEET_URL, worksheet=access_id, data=edited_df)
        st.success("저장 완료!")
        st.rerun()

# 하단 차트
st.subheader("📈 지출 분포")
if not df[df["구분"]=="지출"].empty:
    fig = px.pie(df[df["구분"]=="지출"], values="금액", names="항목", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

