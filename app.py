import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Shared", layout="wide")

# 2. 구글 시트 연결
# 주소 끝에 gid 등이 붙어있지 않은지 확인하세요.
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit"
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 사이드바 로그인
st.sidebar.title("💎 WealthFlow")
access_id = st.sidebar.text_input("접속 아이디를 입력하세요 (시트 탭 이름)", value="").strip()

if not access_id:
    st.title("💰 자산관리를 위한 웹페이지")
    st.info("왼쪽 사이드바에 지정 받은 ID(구글 시트 탭 이름)를 입력해주세요.")
    st.stop()

# 4. 데이터 로드 (ttl=0으로 설정하여 실시간 탭 변경 감지)
try:
    # ttl=0은 캐시를 사용하지 않고 즉시 시트의 최신 상태를 읽어옵니다.
    df = conn.read(spreadsheet=SHEET_URL, worksheet=access_id, ttl=0)
except Exception as e:
    st.error(f"❌ '{access_id}'라는 이름의 탭을 찾을 수 없습니다.")
    st.warning("확인 사항:")
    st.write("1. 구글 시트 하단 탭 이름이 아이디와 정확히 일치하는지 (대소문자/공백 확인)")
    st.write("2. 구글 시트 공유 설정이 '편집자'로 되어 있는지")
    # 개발 참고용 실제 에러 메시지 출력
    with st.expander("상세 에러 내용 보기"):
        st.code(str(e))
    st.stop()

# 데이터 전처리 (데이터가 있는 경우에만 실행)
if not df.empty:
    df["날짜"] = pd.to_datetime(df["날짜"], errors='coerce')
    df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
    df = df.sort_values("날짜", ascending=False)
else:
    # 빈 시트일 경우 기본 구조 생성
    df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])

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
            updated_df = pd.concat([df, new_data], ignore_index=True)
            # 데이터 업데이트 시도
            try:
                conn.update(spreadsheet=SHEET_URL, worksheet=access_id, data=updated_df)
                st.success("기록되었습니다! 화면을 새로고침 해주세요.")
                st.rerun()
            except Exception as update_err:
                st.error("데이터 저장 실패. 구글 시트 권한(편집자)을 확인하세요.")
                st.info("임시 조치: 구글 시트에서 직접 입력하거나 서비스 계정 설정이 필요할 수 있습니다.")

with col_view:
    st.subheader("📑 상세 내역")
    # 데이터 에디터 (수정 가능)
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
