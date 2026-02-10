import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection
import hashlib

# 1. 페이지 설정 및 디자인 커스텀
st.set_page_config(page_title="WealthFlow Secure Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border: 1px solid #ececf1;
    }
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
    .plus-val { color: #d9534f; font-weight: 700; }
    .minus-val { color: #0275d8; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# 비밀번호 암호화 함수
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# 세션 상태 초기화 (로그인 상태 유지용)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# 2. 구글 시트 연결 설정
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit?gid=1372652953#gid=1372652953" 
conn = st.connection("gsheets", type=GSheetsConnection)

# =============================
# 3. 로그인 / 회원가입 화면
# =============================
st.sidebar.title("💎 WealthFlow Pro")

if not st.session_state.logged_in:
    menu = ["로그인", "회원가입"]
    choice = st.sidebar.selectbox("접속 메뉴", menu)

    # 사용자 명부(Users 탭) 불러오기
    try:
        user_db = conn.read(spreadsheet=SHEET_URL, worksheet="Users", ttl="0s")
    except:
        user_db = pd.DataFrame(columns=["username", "password"])

    if choice == "회원가입":
        st.title("🆕 가계부 계정 생성")
        new_user = st.text_input("아이디(영문/숫자)", key="reg_id").strip()
        new_password = st.text_input("비밀번호", type='password', key="reg_pw")
        
        if st.button("가입하기", use_container_width=True):
            if new_user in user_db['username'].values:
                st.error("이미 존재하는 아이디입니다.")
            elif new_user and new_password:
                new_row = pd.DataFrame([{"username": new_user, "password": make_hashes(new_password)}])
                updated_users = pd.concat([user_db, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=updated_users)
                st.success("회원가입 성공! 로그인 메뉴로 이동하여 접속하세요.")
            else:
                st.warning("아이디와 비밀번호를 모두 입력해주세요.")
        st.stop() # 로그인 전까지 아래 코드를 실행하지 않음

    elif choice == "로그인":
        st.title("🔐 로그인이 필요합니다")
        login_user = st.sidebar.text_input("아이디", key="login_id").strip()
        login_password = st.sidebar.text_input("비밀번호", type='password', key="login_pw")
        
        if st.sidebar.button("로그인", use_container_width=True):
            hashed_pw = make_hashes(login_password)
            if login_user in user_db['username'].values and \
               hashed_pw == str(user_db[user_db['username'] == login_user]['password'].values[0]):
                
                st.session_state.logged_in = True
                st.session_state.user_id = login_user
                st.rerun() 
            else:
                st.sidebar.error("아이디 또는 비밀번호가 틀렸습니다.")
        st.stop()

# =============================
# 4. 로그인 성공 후: 메인 대시보드
# =============================
user_id = st.session_state.user_id

with st.sidebar:
    st.success(f"👤 {user_id}님 접속 중")
    if st.button("로그아웃", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.rerun()
    st.divider()

# 사용자별 장부 데이터 로드
try:
    df = conn.read(spreadsheet=SHEET_URL, worksheet=user_id, ttl="0s")
except:
    df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])

# 데이터 전처리
if not df.empty:
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["금액"] = pd.to_numeric(df["금액"], errors='coerce').fillna(0)
    df = df.sort_values("날짜", ascending=False)

# 대시보드 타이틀
st.title(f"📊 {user_id}님의 재무 대시보드")

# --- 메트릭 섹션 ---
with st.expander("💰 기초 자산 설정", expanded=False):
    c1, c2, c3 = st.columns(3)
    init_cash = c1.number_input("현재 현금 잔액", value=0, step=10000)
    init_sav = c2.number_input("기존 적금 총액", value=0, step=10000)
    init_inv = c3.number_input("기존 투자 총액", value=0, step=10000)

inc_t = df[df["구분"] == "수익"]["금액"].sum()
exp_t = df[df["구분"] == "지출"]["금액"].sum()
sav_t = df[df["구분"] == "저축-적금"]["금액"].sum()
inv_t = df[df["구분"] == "저축-투자"]["금액"].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("💵 가용 현금", f"{init_cash + inc_t - exp_t - sav_t - inv_t:,.0f}원")
m2.metric("🏦 총 적금", f"{init_sav + sav_t:,.0f}원")
m3.metric("📈 총 투자", f"{init_inv + inv_t:,.0f}원")
m4.metric("📉 누적 지출", f"{exp_t:,.0f}원", delta_color="inverse")

st.divider()

# --- 입력 및 상세 내역 ---
st.subheader("📑 상세 거래 내역")
col_input, col_table = st.columns([1, 3])

with col_input:
    st.write("**내역 추가**")
    with st.form("add_form", clear_on_submit=True):
        d = st.date_input("날짜", value=date.today())
        g = st.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = st.text_input("항목")
        a = st.number_input("금액", min_value=0, step=1000)
        m = st.text_input("메모")
        if st.form_submit_button("저장하기", use_container_width=True):
            if i and a > 0:
                new_row = pd.DataFrame([{"날짜": d.strftime("%Y-%m-%d"), "구분": g, "항목": i, "금액": a, "메모": m}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet=user_id, data=updated_df)
                st.success("시트에 기록되었습니다!")
                st.rerun()

with col_table:
    if not df.empty:
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="main_editor")
        if st.button("💾 모든 변경사항 시트에 동기화", use_container_width=True):
            conn.update(spreadsheet=SHEET_URL, worksheet=user_id, data=edited_df)
            st.success("동기화 완료!")
            st.rerun()
    else:
        st.info("데이터가 없습니다. 왼쪽 폼에서 첫 내역을 추가해 보세요.")

st.divider()

# --- 시각화 섹션 ---
col_pie, col_list = st.columns([1, 1])

with col_pie:
    st.subheader("🍕 지출 구성비")
    exp_df = df[df["구분"] == "지출"]
    if not exp_df.empty:
        fig = px.pie(exp_df, values="금액", names="항목", hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("지출 데이터가 없습니다.")

with col_list:
    st.subheader("🗓 최근 날짜별 수지")
    if not df.empty:
        summary = df.copy()
        summary['net'] = summary.apply(lambda x: x['금액'] if x['구분'] == '수익' else (-x['금액'] if x['구분'] == '지출' else 0), axis=1)
        daily = summary.groupby(summary['날짜'].dt.date)['net'].sum().reset_index().head(7)
        for _, row in daily.iterrows():
            cls = "plus-val" if row['net'] >= 0 else "minus-val"
            st.markdown(f"<div class='daily-box'><span>📅 {row['날짜']}</span><span class='{cls}'>{row['net']:+,.0f}원</span></div>", unsafe_allow_html=True)
