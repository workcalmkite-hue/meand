import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(
    page_title="가계부",
    page_icon="💰",
    layout="wide",
)

st.title("💰 가계부")

# --------------------
#  세션 상태에 가계부 데이터프레임 초기화
# --------------------
if "ledger" not in st.session_state:
    st.session_state["ledger"] = pd.DataFrame(
        columns=["날짜", "구분", "카테고리", "내용", "금액"]
    )

ledger = st.session_state["ledger"]

st.info("수입/지출을 추가하면 아래 표와 요약이 자동으로 갱신됩니다.")

# --------------------
#  입력 폼
# --------------------
with st.form("add_record_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        d = st.date_input("날짜", value=date.today())
    with col2:
        kind = st.selectbox("구분", ["지출", "수입"])
    with col3:
        category = st.text_input("카테고리 (예: 식비, 월급, 교통비 등)", value="")

    memo = st.text_input("내용/메모", value="")
    amount = st.number_input("금액", min_value=0, step=1000, format="%d")

    submitted = st.form_submit_button("추가하기")

    if submitted:
        if amount == 0:
            st.warning("금액을 0보다 크게 입력해 주세요.")
        else:
            new_row = pd.DataFrame(
                {
                    "날짜": [pd.to_datetime(d)],
                    "구분": [kind],
                    "카테고리": [category if category else "-"],
                    "내용": [memo if memo else "-"],
                    "금액": [amount],
                }
            )
            st.session_state["ledger"] = pd.concat(
                [st.session_state["ledger"], new_row],
                ignore_index=True,
            )
            st.success("✅ 내역이 추가되었습니다!")

# 최신 데이터 다시 가져오기
ledger = st.session_state["ledger"]

st.markdown("---")

# --------------------
#  요약 카드
# --------------------
if len(ledger) > 0:
    col_a, col_b, col_c = st.columns(3)

    total_income = ledger.loc[ledger["구분"] == "수입", "금액"].sum()
    total_expense = ledger.loc[ledger["구분"] == "지출", "금액"].sum()
    balance = total_income - total_expense

    with col_a:
        st.metric("총 수입", f"{total_income:,.0f} 원")
    with col_b:
        st.metric("총 지출", f"{total_expense:,.0f} 원")
    with col_c:
        st.metric("현재 잔액 (수입-지출)", f"{balance:,.0f} 원")

    st.markdown("### 📊 카테고리별 합계")
    if "카테고리" in ledger.columns:
        cat_summary = (
            ledger.groupby(["구분", "카테고리"])["금액"]
            .sum()
            .reset_index()
            .sort_values(["구분", "금액"], ascending=[True, False])
        )
        st.dataframe(cat_summary, use_container_width=True)

    st.markdown("### 📋 전체 내역")
    st.dataframe(
        ledger.sort_values("날짜", ascending=False),
        use_container_width=True,
    )
else:
    st.info("아직 기록된 내역이 없습니다. 위 폼에서 첫 번째 내역을 추가해 보세요 😊")
