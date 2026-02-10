import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .daily-box {
        padding: 8px 12px;
        border-radius: 8px;
        background: white;
        margin-bottom: 5px;
        border-left: 5px solid #4F46E5;
        display: flex;
        justify-content: space-between;
    }
    .plus-val { color: #d9534f; font-weight: bold; } /* 수익/플러스 */
    .minus-val { color: #0275d8; font-weight: bold; } /* 지출/마이너스 */
    </style>
""", unsafe_allow_html=True)

# =============================
# 세션 상태 초기화
# =============================
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=["날짜", "구분", "항목", "금액", "메모"]
    )

if "config" not in st.session_state:
    st.session_state.config = {"initial_asset": 0, "initial_saving": 0, "initial_invest": 0}

# =============================
# 사이드바 (입력창)
# =============================
with st.sidebar:
    st.title("💎 WealthFlow")
    with st.expander("💰 초기 자산 설정"):
        st.session_state.config["initial_asset"] = st.number_input("보유 현금", value=st.session_state.config["initial_asset"], step=100000)
        st.session_state.config["initial_saving"] = st.number_input("기존 적금", value=st.session_state.config["initial_saving"], step=100000)
        st.session_state.config["initial_invest"] = st.number_input("기존 투자", value=st.session_state.config["initial_invest"], step=100000)
    
    st.divider()
    st.subheader("➕ 내역 추가")
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("날짜", value=date.today())
        g = st.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = st.text_input("항목", placeholder="항목 입력")
        a = st.number_input("금액", min_value=0, step=1000)
        m = st.text_input("메모")
        if st.form_submit_button("기록하기", use_container_width=True):
            if i and a > 0:
                new_row = pd.DataFrame([{"날짜": pd.to_datetime(d), "구분": g, "항목": i, "금액": a, "메모": m}])
                st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
                st.rerun()

# 데이터 가공
df = st.session_state.data.copy()
df["날짜"] = pd.to_datetime(df["날짜"])
df = df.sort_values("날짜", ascending=False)

# 계산
inc = df[df["구분"] == "수익"]["금액"].sum()
exp = df[df["구분"] == "지출"]["금액"].sum()
sav = df[df["구분"] == "저축-적금"]["금액"].sum()
inv = df[df["구분"] == "저축-투자"]["금액"].sum()

current_cash = st.session_state.config["initial_asset"] + inc - exp - sav - inv
total_saving = st.session_state.config["initial_saving"] + sav
total_invest = st.session_state.config["initial_invest"] + inv

# =============================
# 메인 대시보드
# =============================

# 1. 요약 메트릭
m1, m2, m3, m4 = st.columns(4)
m1.metric("💵 가용 현금", f"{current_cash:,.0f}원")
m2.metric("🏦 총 적금", f"{total_saving:,.0f}원")
m3.metric("📈 총 투자", f"{total_invest:,.0f}원")
m4.metric("📉 총 지출", f"{exp:,.0f}원")

st.divider()

# 2. [상단] 상세 내역 편집기
st.subheader("📑 상세 거래 내역")
edited_df = st.data_editor(
    df,
    column_config={
        "구분": st.column_config.SelectboxColumn(options=["수익", "지출", "저축-적금", "저축-투자"]),
        "금액": st.column_config.NumberColumn(format="%d 원"),
        "날짜": st.column_config.DateColumn()
    },
    use_container_width=True, num_rows="dynamic", key="editor_top"
)
if st.button("💾 데이터 변경사항 저장"):
    st.session_state.data = edited_df
    st.rerun()

st.write("")

# 3. [하단] 분석 영역
st.divider()
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("🍕 항목별 지출 비중")
    exp_df = df[df["구분"] == "지출"]
    if not exp_df.empty:
        fig_pie = px.pie(exp_df, values="금액", names="항목", hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("지출 내역이 없습니다.")

with c2:
    st.subheader("🗓 날짜별 수지 요약")
    if not df.empty:
        # 날짜별 수익-지출 합산 (현금 흐름 기준)
        daily_df = df.copy()
        daily_df['val'] = daily_df.apply(lambda x: x['금액'] if x['구분'] == '수익' else (-x['금액'] if x['구분'] == '지출' else 0), axis=1)
        daily_summary = daily_df.groupby(daily_df['날짜'].dt.date)['val'].sum().reset_index()
        daily_summary = daily_summary.sort_values("날짜", ascending=False)

        # 달력 느낌의 리스트 출력
        for _, row in daily_summary.iterrows():
            val = row['val']
            color_class = "plus-val" if val > 0 else "minus-val"
            prefix = "+" if val > 0 else ""
            
            st.markdown(f"""
                <div class="daily-box">
                    <span>📅 <b>{row['날짜'].strftime('%m월 %d일')}</b></span>
                    <span class="{color_class}">{prefix}{val:,.0f} 원</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("데이터가 없습니다.")