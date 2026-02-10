import streamlit as st
import pandas as pd
from datetime import date
from streamlit_gsheets import GSheetsConnection

# ======================================================
# 1. 페이지 설정
# ======================================================
st.set_page_config(
    page_title="WealthFlow Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# 2. Google Sheets 연결
# ======================================================
conn = st.connection("gsheets", type=GSheetsConnection)

# ======================================================
# 3. 사이드바 (유저 선택)
# ======================================================
st.sidebar.title("💎 WealthFlow Pro")
user_input = st.sidebar.text_input("접속 아이디", "").strip().lower()

user_mapping = {
    "newbin": "newbin",
    "sheet2": "sheet2",
    "sheet3": "sheet3"
}

if not user_input or user_input not in user_mapping:
    st.title("💰 자산관리 시스템")
    st.info("왼쪽 사이드바에 아이디를 입력해주세요.")
    st.stop()

worksheet = user_mapping[user_input]

# ======================================================
# 4. 데이터 로드
# ======================================================
try:
    df = conn.read(worksheet=worksheet, ttl=0)

    if df is None or df.empty:
        df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])
    else:
        # 불필요한 index 컬럼 제거
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

        # 타입 정리
        df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
        df["구분"] = df["구분"].astype(str)
        df["항목"] = df["항목"].astype(str)
        df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0).astype(int)
        df["메모"] = df["메모"].astype(str)

except Exception as e:
    st.error("❌ 데이터 로드 실패")
    st.code(str(e))
    st.stop()

# ======================================================
# 5. 상단 대시보드 요약
# ======================================================
st.title(f"📊 {user_input.upper()} 자산 대시보드")

total_income = df[df["구분"] == "수익"]["금액"].sum()
total_expense = df[df["구분"] == "지출"]["금액"].sum()
total_saving = df[df["구분"].str.startswith("저축")]["금액"].sum()
current_balance = total_income - total_expense

c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 현재 잔액", f"{current_balance:,.0f} 원")
c2.metric("📈 총 수익", f"{total_income:,.0f} 원")
c3.metric("📉 총 지출", f"{total_expense:,.0f} 원")
c4.metric("🏦 총 저축", f"{total_saving:,.0f} 원")

st.divider()

# ======================================================
# 6. 사이드바 입력 폼
# ======================================================
st.sidebar.subheader("✏️ 내역 추가")

with st.sidebar.form("add_form", clear_on_submit=True):
    d = st.date_input("날짜", value=date.today())
    g = st.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
    i = st.text_input("항목")
    a = st.number_input("금액", min_value=0, step=1000)
    memo = st.text_input("메모")
    submit = st.form_submit_button("저장")

if submit:
    if not i or a <= 0:
        st.warning("항목과 금액을 정확히 입력해주세요.")
    else:
        try:
            new_row = pd.DataFrame([{
                "날짜": d.strftime("%Y-%m-%d"),
                "구분": g,
                "항목": i,
                "금액": int(a),
                "메모": memo
            }])

            base_df = df.copy()
            base_df["날짜"] = base_df["날짜"].dt.strftime("%Y-%m-%d")

            updated_df = pd.concat([base_df, new_row], ignore_index=True)
            updated_df = updated_df.fillna("")
            updated_df = updated_df.reset_index(drop=True)

            conn.update(
                worksheet=worksheet,
                data=updated_df
            )

            st.success("✅ 저장 완료!")
            st.rerun()

        except Exception as e:
            st.error("❌ 저장 실패")
            st.code(str(e))

# ======================================================
# 7. 전체 내역 테이블
# ======================================================
st.subheader("📑 전체 내역")

if not df.empty:
    display_df = df.copy()
    display_df["날짜"] = display_df["날짜"].dt.strftime("%Y-%m-%d")

    st.dataframe(
        display_df.sort_values("날짜", ascending=False),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("아직 입력된 내역이 없습니다.")



