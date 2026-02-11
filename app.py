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
            # 날짜를 datetime 형식으로 변환하여 정렬 준비
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0).astype(int)
            df['item'] = df['item'].astype(str)
            df['memo'] = df['memo'].astype(str)
            # 로드 시점에도 날짜순 정렬 (과거 -> 최신)
            df = df.sort_values('date').reset_index(drop=True)
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
                    # 신규 데이터 추가 후 전체 정렬 로직 작동
                    new_row = pd.DataFrame([{"date": d, "category": g, "item": i, "amount": int(a), "memo": m}])
                    full_df = pd.concat([df, new_row], ignore_index=True)
                    
                    # [핵심] 날짜순 정렬 후 시트 업데이트
                    full_df['date'] = pd.to_datetime(full_df['date']).dt.date
                    full_df = full_df.sort_values('date')
                    
                    save_data = [full_df.columns.values.tolist()] + full_df.astype(str).values.tolist()
                    worksheet.clear()
                    worksheet.update('A1', save_data)
                    
                    st.success("✅ 날짜 순으로 정렬되어 저장되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

st.divider()

# 6. 메인 화면 중간: 데이터 편집 (수정 시에도 자동 정렬 반영)
st.subheader("📑 내역 편집 및 관리")
st.caption("💡 수정/삭제 후 '변경사항 저장하기'를 누르면 자동으로 날짜순(시계열) 정렬됩니다.")

if not df.empty:
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "date": st.column_config.DateColumn("날짜", format="YYYY-MM-DD", required=True),
            "category": st.column_config.SelectboxColumn("구분", options=["수익", "지출", "저축-적금", "저축-투자"], required=True),
            "item": st.column_config.TextColumn("항목", required=True),
            "amount": st.column_config.NumberColumn("금액", format="%d원", required=True),
            "memo": st.column_config.TextColumn("메모")
        },
        hide_index=True,
    )

    col_btn, _ = st.columns([1, 4])
    if col_btn.button("💾 변경사항 저장하기", use_container_width=True):
        try:
            with st.spinner("날짜순으로 정렬하여 저장 중..."):
                save_df = edited_df.copy()
                # [핵심] 저장 직전 날짜순 정렬 수행
                save_df['date'] = pd.to_datetime(save_df['date']).dt.date
                save_df = save_df.sort_values('date')
                
                # 데이터 포맷팅 및 업데이트
                new_all_data = [save_df.columns.values.tolist()] + save_df.astype(str).values.tolist()
                worksheet.clear()
                worksheet.update('A1', new_all_data)
                
                st.success("✅ 시계열 정렬 및 저장이 완료되었습니다!")
                st.rerun()
        except Exception as e:
            st.error(f"저장 중 오류 발생: {e}")
else:
    st.info("데이터가 없습니다.")

st.divider()

# 7. 메인 화면 하단: 통계 분석 (정렬된 데이터를 바탕으로 그래프 생성)
if not df.empty:
    st.subheader("📈 지출 분석 리포트")
    expense_df = df[df['category'] == '지출'].copy()

    if not expense_df.empty:
        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("#### 📅 날짜별 지출 합계")
            expense_df['date'] = pd.to_datetime(expense_df['date'])
            daily_expense = expense_df.groupby('date')['amount'].sum().reset_index()
            # 그래프도 시간 흐름대로 표시
            fig_bar = px.bar(daily_expense.sort_values('date'), x='date', y='amount', color_discrete_sequence=['#FF4B4B'])
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.markdown("#### 🍕 항목별 지출 비율")
            item_expense = expense_df.groupby('item')['amount'].sum().reset_index()
            fig_pie = px.pie(item_expense, values='amount', names='item', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)
