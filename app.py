import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Shared", layout="wide")

# 2. 구글 시트 연결
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 로그인
st.sidebar.title("💎 WealthFlow")
access_id = st.sidebar.text_input("접속 아이디를 입력하세요", value="").strip()

if not access_id:
    st.title("💰 자산관리를 위한 웹페이지")
    st.info("왼쪽 사이드바에 사용하실 ID를 입력해주세요. 처음이시면 새 ID를 입력 후 장부를 생성하세요.")
    st.stop()

# 가계부 기본 필수 헤더
HEADER = ["날짜", "구분", "항목", "금액", "메모"]

# 4. 데이터 로드 로직
try:
    # ttl=0으로 설정하여 캐시 없이 실시간 확인
    df = conn.read(spreadsheet=SHEET_URL, worksheet=access_id, ttl=0)
    
    # 탭은 존재하지만 데이터가 아예 없는 경우(헤더도 없는 경우) 처리
    if df is None or df.empty and len(df.columns) < 5:
        df = pd.DataFrame(columns=HEADER)
except Exception:
    # 탭이 존재하지 않을 때 실행
    st.warning(f"🤔 '{access_id}' 장부가 아직 없습니다.")
    if st.button(f"✨ '{access_id}' 아이디로 새 장부 만들기", use_container_width=True):
        try:
            # 제목 줄(헤더)이 포함된 빈 데이터프레임 생성 후 업로드
            init_df = pd.DataFrame(columns=HEADER)
            conn.update(spreadsheet=SHEET_URL, worksheet=access_id, data=init_df)
            st.success(f"✅ '{access_id}' 장부가 생성되었습니다! 잠시 후 자동으로 새로고침됩니다.")
            st.rerun()
        except Exception as e:
            st.error("장부 생성 실패. 구글 시트 공유 권한을 다시 확인해주세요.")
            st.stop()
    st.stop()

# 데이터 전처리
df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
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

# 6. 데이터 입력 및 편집
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
            new_row = pd.DataFrame([{"날짜": d.strftime("%Y-%m-%d"), "구분": g, "항목": i, "금액": a, "메모": ""}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet=access_id, data=updated_df)
            st.success("기록 완료!")
            st.rerun()

with col_view:
    st.subheader("📑 상세 내역 확인 및 수정")
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 변경사항 저장", use_container_width=True):
        conn.update(spreadsheet=SHEET_URL, worksheet=access_id, data=edited_df)
        st.success("저장되었습니다!")
        st.rerun()

# 7. 지출 차트
st.subheader("📈 지출 분포")
exp_df = df[df["구분"] == "지출"]
if not exp_df.empty:
    fig = px.pie(exp_df, values="금액", names="항목", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
