import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import json
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="WealthFlow Pro", layout="wide")

# 2. 구글 시트 연결 설정
def get_gspread_client():
    creds_info = json.loads(st.secrets["connections"]["gsheets"]["service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)

try:
    client = get_gspread_client()
    spreadsheet_id = st.secrets["connections"]["gsheets"]["spreadsheet"]
    sh = client.open_by_key(spreadsheet_id)
except Exception as e:
    st.error(f"구글 시트 연결 실패: {e}")
    st.stop()

# 3. 사이드바 및 사용자 설정
st.sidebar.title("💎 WealthFlow Pro")
user_input = st.sidebar.text_input("접속 아이디", value="").strip().lower()

user_mapping = {
    "newbin": "newbin", 
    "sheet2": "sheet2",
    "sheet3": "sheet3"
}

if not user_input or user_input not in user_mapping:
    st.title("💰 자산관리 시스템")
    st.info("왼쪽 사이드바에 등록된 아이디를 입력해주세요.")
    st.stop()

target_worksheet_name = user_mapping[user_input]

# 4. 데이터 로드 함수
def load_data(ws_name):
    try:
        ws = sh.worksheet(ws_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # 날짜와 금액 형식 정리
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).astype(int)
            # 텍스트 컬럼 보장
            df['item'] = df['item'].astype(str)
            df['memo'] = df['memo'].astype(str)
        else:
            df = pd.DataFrame(columns=["date", "category", "item", "amount", "memo"])
            
        return df, ws
    except Exception as e:
        st.error(f"워크시트 로드 실패: {e}")
        return pd.DataFrame(columns=["date", "category", "item", "amount", "memo"]), None

df, worksheet = load_data(target_worksheet_name)

# 5. 메인 화면 상단: 입력 폼
st.title(f"📊 {user_input.upper()}님 대시보드")

with st.expander("➕ 새로운 내역 기록하기", expanded=False):
    with st.form("add_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        d = col1.date_input("날짜", value=date.today())
        g = col2.selectbox("구분", ["수익", "지출", "저축-적금", "저축-투자"])
        i = col3.text_input("항목")
        
        col4, col5 = st.columns([1, 2])
        a = col4.number_input("금액", min_value=0, step=1000)
        m = col5.text_input("메모")
        submit = st.form_submit_button("장부에 기록", use_container_width=True)

        if submit:
            if not i or a <= 0:
                st.warning("항목과 금액을 입력해주세요.")
            elif worksheet:
                try:
                    new_data = [str(d), g, i, int(a), m]
                    worksheet.append_row(new_data)
                    st.success("✅ 저장 완료!")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

st.divider()

# 6. 메인 화면 중간: 데이터 편집 (수정/삭제 기능 강화)
st.subheader("📑 내역 관리")
st.caption("💡 수정: 셀 더블클릭 / 삭제: 행 선택 후 Delete 키 / 추가: 표 하단 (+) 버튼")

if not df.empty:
    # 데이터 에디터 (수정 가능 여부 명시적 설정)
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "date": st.column_config.DateColumn("날짜", format="YYYY-MM-DD", required=True),
            "category": st.column_config.SelectboxColumn("구분", options=["수익", "지출", "저축-적금", "저축-투자"], required=True),
            "item": st.column_config.TextColumn("항목", required=True, disabled=False), # disabled=False 명시
            "amount": st.column_config.NumberColumn("금액", format="%d원", required=True),
            "memo": st.column_config.TextColumn("메모", disabled=False) # disabled=False 명시
        },
        hide_index=True,
    )

    col_btn, _ = st.columns([1, 4])
    if col_btn.button("💾 변경사항 저장하기", use_container_width=True):
        try:
            with st.spinner("구글 시트에 동기화 중..."):
                save_df = edited_df.copy()
                # 저장 전 데이터 포맷팅
                save_df['date'] = save_df['date'].apply(lambda x: str(x))
                save_df['amount'] = save_df['amount'].astype(int)
                
                # 데이터 업데이트 (헤더 포함)
                new_all_data = [save_df.columns.values.tolist()] + save_df.values.tolist()
                
                worksheet.clear()
                worksheet.update('A1', new_all_data)
                
                st.success("✅ 변경사항이 구글 시트에 반영되었습니다!")
                st.rerun()
        except Exception as e:
            st.error(f"저장 중 오류 발생: {e}")
else:
    st.info("표시할 데이터가 없습니다.")

st.divider()

# 7. 메인 화면 하단: 통계 분석
if not df.empty:
    st.subheader("📈 지출 분석 리포트")
    expense_df = df[df['category'] == '지출'].copy()

    if not expense_df.empty:
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("#### 📅 날짜별 지출 합계")
            expense_df['date'] = pd.to_datetime(expense_df['date'])
            daily_expense = expense_df.groupby('date')['amount'].sum().reset_index()
            fig_bar = px.bar(daily_expense, x='date', y='amount', color_discrete_sequence=['#FF4B4B'])
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.markdown("#### 🍕 항목별 지출 비율")
            item_expense = expense_df.groupby('item')['amount'].sum().reset_index()
            fig_pie = px.pie(item_expense, values='amount', names='item', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)
