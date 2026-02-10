import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from streamlit_gsheets import GSheetsConnection
import hashlib

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Secure", layout="wide")

# 비밀번호 암호화 함수 (보안용)
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# 2. 구글 시트 연결
SHEET_URL = "https://docs.google.com/spreadsheets/d/1se066IRVdZ_JA2phYiGqCxr1RAVibqFOZhYTqrd81yg/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# =============================
# 3. 로그인 / 회원가입 로직
# =============================
st.sidebar.title("🔐 개인 자산 관리 로그인")

menu = ["로그인", "회원가입"]
choice = st.sidebar.selectbox("메뉴", menu)

# 사용자 명부 불러오기 (첫 번째 탭인 'Users' 탭을 사용한다고 가정)
try:
    user_db = conn.read(spreadsheet=SHEET_URL, worksheet="Users", ttl="0s")
except:
    user_db = pd.DataFrame(columns=["username", "password"])

if choice == "회원가입":
    st.subheader("🆕 새로운 계정 생성")
    new_user = st.text_input("사용할 아이디(영문/숫자)", key="reg_id").strip()
    new_password = st.text_input("비밀번호", type='password', key="reg_pw")
    
    if st.button("가입하기"):
        if new_user in user_db['username'].values:
            st.error("이미 존재하는 아이디입니다.")
        elif new_user and new_password:
            # 명부에 추가
            new_row = pd.DataFrame([{"username": new_user, "password": make_hashes(new_password)}])
            updated_users = pd.concat([user_db, new_row], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Users", data=updated_users)
            st.success("회원가입 완료! 로그인 메뉴로 이동해주세요.")
        else:
            st.warning("아이디와 비밀번호를 모두 입력해주세요.")

elif choice == "로그인":
    login_user = st.sidebar.text_input("아이디", key="login_id").strip()
    login_password = st.sidebar.text_input("비밀번호", type='password', key="login_pw")
    
    if st.sidebar.checkbox("로그인"):
        # 비밀번호 확인
        hashed_pw = make_hashes(login_password)
        if login_user in user_db['username'].values and \
           hashed_pw == user_db[user_db['username'] == login_user]['password'].values[0]:
            
            st.session_state.logged_in = True
            st.session_state.user_id = login_user
        else:
            st.sidebar.error("아이디 또는 비밀번호가 틀렸습니다.")
            st.stop()
    else:
        st.info("로그인 해주세요.")
        st.stop()

# =============================
# 4. 로그인 성공 후 장부 로직
# =============================
user_id = st.session_state.user_id
st.success(f"👤 {user_id} 님 환영합니다!")

# 해당 유저의 탭 데이터 로드
try:
    df = conn.read(spreadsheet=SHEET_URL, worksheet=user_id, ttl="0s")
except:
    df = pd.DataFrame(columns=["날짜", "구분", "항목", "금액", "메모"])

# [이후 내역 추가, 시각화 로직은 기존과 동일...]
# (생략된 부분은 이전 코드와 같습니다. 그대로 유지하시면 됩니다.)
