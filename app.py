import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 디자인 커스텀
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경색 및 폰트 설정 */
    .stApp { background-color: #f8f9fa; }
    
    /* 상단 메트릭 카드 디자인 */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #ececf1;
    }
    
    /* 날짜별 수지 박스 디자인 */
    .daily-box {
        padding: 12px 18px;
        border-radius: 10px;
        background: white;
        margin-bottom: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 6px solid #4F46E5;
    }
    .plus-val { color: #d9534f; font-weight: 700; font-size: 1.1rem; }
    .minus-val { color: #0275d8; font-weight: 700; font-size: 1.1rem; }
    
    /* 섹션 구분선 */
    hr { margin: 2rem 0; }
    </style>
""", unsafe_allow_html=True)

# =============================
# 2. 구글 시트 데이터 로드
# =============================
# [중요] 여기에 본인의 구글 시트 주소를 넣으세요!
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit?gid=0#gid=0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # 실시간 반영을 위해 ttl=0 설정
    df = conn.read(spreadsheet=SHEET_URL, ttl="0s")
except Exception as e:
    st.error("구글 시트 연결에 문제가 발생했습니다. URL과 권한 설정을 확인해주세요.")
    df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])

# 데이터 클리닝
if not df.empty:
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
    df = df.sort_values("날짜", ascending=False)

# =============================
# 3. 사이드바: 자산 설정 및 내역 추가
# =============================
with st.sidebar:
    st.title("💎 WealthFlow")
    
    with st.expander("💰 기초 자산 설정 (최초 1회)"):
        init_asset = st.number_input("현재 가용 현금", value=0, step=100000)
        init_saving = st.number_input("총 적금액", value=0, step=100000)
        init_invest = st.number_input("총 투자액", value=0, step=100000)
    
    st.divider()
    st.subheader("➕ 내역 추가")
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("날짜", value=date.today())
        g = st.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = st.text_input("항목 (예: 월급, 점심값)")
        a = st.number_input("금액", min_value=0, step=1000)
        m = st.text_input("메모")
        
        if st.form_submit_button("장부 기록하기", use_container_width=True):
            if i and a > 0:
                new_row = pd.DataFrame([{
                    "날짜": d.strftime("%Y-%m-%d"), 
                    "구분": g, "항목": i, "금액": a, "메모": m
                }])
                # 데이터 병합 및 구글 시트 저장
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                st.success("저장 완료!")
                st.rerun()
            else:
                st.warning("항목명과 금액을 확인해주세요.")

# =============================
# 4. 상단 메트릭 (대시보드)
# =============================
# 계산 로직
inc_total = df[df["구분"] == "수익"]["금액"].sum()
exp_total = df[df["구분"] == "지출"]["금액"].sum()
sav_total = df[df["구분"] == "저축-적금"]["금액"].sum()
inv_total = df[df["구분"] == "저축-투자"]["금액"].sum()

current_cash = init_asset + inc_total - exp_total - sav_total - inv_total
total_savings = init_saving + sav_total
total_invests = init_invest + inv_total

st.title("📊 재무 현황 대시보드")
m1, m2, m3, m4 = st.columns(4)
m1.metric("💵 가용 현금", f"{current_cash:,.0f} 원")
m2.metric("🏦 총 적금액", f"{total_savings:,.0f} 원", delta=f"+{sav_total:,.0f}")
m3.metric("📈 총 투자액", f"{total_invests:,.0f} 원", delta=f"+{inv_total:,.0f}")
m4.metric("📉 총 지출", f"{exp_total:,.0f} 원", delta_color="inverse")

st.divider()

# =============================
# 5. [상단] 데이터 편집기
# =============================
st.subheader("📑 상세 거래 내역")
if not df.empty:
    # 스트림릿 데이터 에디터 활용
    edited_df = st.data_editor(
        df,
        column_config={
            "날짜": st.column_config.DateColumn("날짜"),
            "구분": st.column_config.SelectboxColumn("구분", options=["수익", "지출", "저축-적금", "저축-투자"]),
            "금액": st.column_config.NumberColumn("금액", format="%d 원"),
        },
        use_container_width=True,
        num_rows="dynamic",
        key="data_editor"
    )
    
    if st.button("💾 변경사항 전체 저장", use_container_width=True):
        conn.update(spreadsheet=SHEET_URL, data=edited_df)
        st.success("구글 시트에 성공적으로 동기화되었습니다!")
        st.rerun()
else:
    st.info("데이터가 없습니다. 사이드바에서 첫 내역을 입력해 보세요.")

st.divider()

# =============================
# 6. [하단] 시각화 분석
# =============================
col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("🍕 항목별 지출 비중")
    exp_df = df[df["구분"] == "지출"]
    if not exp_df.empty:
        fig_pie = px.pie(
            exp_df, values="금액", names="항목", 
            hole=0.5, 
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.write("표시할 지출 데이터가 없습니다.")

with col_right:
    st.subheader("🗓 날짜별 수지 요약")
    if not df.empty:
        # 날짜별 합계 계산 (수익은 +, 지출은 -)
        daily_df = df.copy()
        daily_df['net'] = daily_df.apply(
            lambda x: x['금액'] if x['구분'] == '수익' else (-x['금액'] if x['구분'] == '지출' else 0), 
            axis=1
        )
        summary = daily_df.groupby(daily_df['날짜'].dt.date)['net'].sum().reset_index()
        summary = summary.sort_values("날짜", ascending=False).head(10) # 최근 10일만

        for _, row in summary.iterrows():
            val = row['net']
            cls = "plus-val" if val >= 0 else "minus-val"
            symbol = "▲" if val >= 0 else "▼"
            
            st.markdown(f"""
                <div class="daily-box">
                    <span>📅 <b>{row['날짜'].strftime('%m월 %d일')}</b></span>
                    <span class="{cls}">{symbol} {abs(val):,.0f} 원</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.write("데이터가 없습니다.")
