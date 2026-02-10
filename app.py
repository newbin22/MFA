import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Shared", layout="wide")

# 2. 구글 시트 연결
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 로그인
st.sidebar.title("💎 WealthFlow")
access_id = st.sidebar.text_input("접속 아이디를 입력하세요", value="").strip()

if not access_id:
    st.title("💰 자산관리를 위한 웹페이지")
    st.info("왼쪽 사이드바에 사용하실 ID를 입력해주세요. 처음이시면 새 ID를 만드시면 됩니다.")
    st.stop()

# 기본 데이터 구조
EMPTY_DF = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])

# 4. 데이터 로드 및 자동 생성 로직
try:
    # 일단 읽어오기 시도
    df = conn.read(spreadsheet=SHEET_URL, worksheet=access_id, ttl=0)
except Exception:
    # 탭이 없어서 에러가 난 경우
    st.warning(f"🤔 '{access_id}' 아이디가 존재하지 않습니다.")
    if st.button(f"✨ '{access_id}'로 새 장부 만들기"):
        try:
            # 새 탭에 기본 헤더만 담아서 업데이트 (이때 구글 시트에 새 탭이 생성됩니다)
            conn.update(spreadsheet=SHEET_URL, worksheet=access_id, data=EMPTY_DF)
            st.success(f"✅ '{access_id}' 장부가 성공적으로 생성되었습니다!")
            st.rerun()
        except Exception as create_err:
            st.error("장부 생성에 실패했습니다. 구글 시트가 '편집자' 권한으로 공유되어 있는지 확인해주세요.")
            st.stop()
    st.stop()

# 데이터 전처리 (데이터가 있는 경우)
if not df.empty:
    df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
    df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
    df = df.sort_values("날짜", ascending=False)
else:
    df = EMPTY_DF.copy()

# 5. 메인 대시보드 표시
st.title(f"📊 {access_id} 장부 대시보드")

# 상단 요약 수치 계산
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

# 6. 데이터 입력 및 확인
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
            # 기존 데이터와 병합
            updated_df = pd.concat([df, new_data], ignore_index=True)
            try:
                conn.update(spreadsheet=SHEET_URL, worksheet=access_id, data=updated_df)
                st.success("기록되었습니다!")
                st.rerun()
            except:
                st.error("저장에 실패했습니다. 권한을 확인하세요.")

with col_view:
    st.subheader("📑 상세 내역")
    # 편집기에서 삭제나 수정 후 저장 가능
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("💾 변경사항 전체 저장", use_container_width=True):
        try:
            conn.update(spreadsheet=SHEET_URL, worksheet=access_id, data=edited_df)
            st.success("전체 저장 완료!")
            st.rerun()
        except:
            st.error("저장에 실패했습니다.")

# 7. 하단 차트
st.subheader("📈 지출 분포")
exp_only = df[df["구분"] == "지출"]
if not exp_only.empty:
    fig = px.pie(exp_only, values="금액", names="항목", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("지출 내역이 있어야 차트가 표시됩니다.")

