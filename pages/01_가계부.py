import streamlit as st
import pandas as pd
from datetime import timedelta

st.set_page_config(
    page_title="엑셀 가계부 분석",
    page_icon="💰",
    layout="wide",
)

st.title("💰 엑셀 가계부 · 기간별 분석 & 피드백")

st.write(
    """
엑셀 가계부 파일을 업로드하면, **기간을 선택해서 지출 내역을 요약**하고  
그 기간을 보면서 **직접 피드백을 작성할 수 있는 페이지**예요.
"""
)

# 💰 금액을 "₩1,234,567" 형태로 표시하는 함수 (표시용 복사본에만 적용)
def format_amount_series(s: pd.Series) -> pd.Series:
    return s.apply(lambda x: f"₩{x:,.0f}" if pd.notnull(x) else "")


# 1️⃣ 파일 업로드
uploaded = st.file_uploader(
    "가계부 엑셀 파일을 업로드하세요 (`.xlsx`, `.xls`)",
    type=["xlsx", "xls"],
)

if uploaded is None:
    st.info("오른쪽에서 엑셀 파일을 선택하면 분석이 시작돼요 😊")
    st.stop()

# 2️⃣ 엑셀 읽기
try:
    df = pd.read_excel(uploaded, sheet_name=0)
except Exception as e:
    st.error(f"파일을 읽는 중 오류가 발생했어요: {e}")
    st.stop()

if df.empty:
    st.warning("엑셀에 데이터가 없는 것 같아요. 내용을 한번 확인해 주세요.")
    st.stop()

# 3️⃣ 컬럼 매핑 (기간 / 금액 / 분류 / 소분류 / 내용 / 수입/지출)
cols = df.columns.tolist()

# 날짜 컬럼
if "기간" in cols:
    date_col = "기간"
else:
    date_candidates = [c for c in cols if "날짜" in str(c) or "일자" in str(c)]
    date_col = date_candidates[0] if date_candidates else cols[0]

# 금액 컬럼
if "금액" in cols:
    amount_col = "금액"
elif "KRW" in cols:
    amount_col = "KRW"
else:
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    amount_col = num_cols[0] if num_cols else cols[0]

# 나머지 컬럼들
main_cat_col = "분류" if "분류" in cols else None
sub_cat_col = "소분류" if "소분류" in cols else None
desc_col = "내용" if "내용" in cols else None
type_col = "수입/지출" if "수입/지출" in cols else None

# 타입 정리
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
df = df.dropna(subset=[date_col])

df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)

if type_col is None:
    df["__구분"] = "지출"
else:
    df["__구분"] = df[type_col].astype(str)


# 4️⃣ 원본 데이터 전체 보기 (금액은 포맷 적용)
st.subheader("1️⃣ 원본 데이터 확인")
st.caption("※ 업로드한 전체 데이터를 모두 표시합니다.")

df_display = df.copy()
if amount_col in df_display.columns:
    df_display[amount_col] = format_amount_series(df_display[amount_col])

st.dataframe(df_display, use_container_width=True)


# 5️⃣ 기간 선택
st.subheader("2️⃣ 분석할 기간 선택하기")

min_date = df[date_col].min().date()
max_date = df[date_col].max().date()

# 기본값: 마지막 날짜 기준 최근 7일
default_start = max_date - timedelta(days=6)
if default_start < min_date:
    default_start = min_date

col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input(
        "시작 날짜",
        value=default_start,
        min_value=min_date,
        max_value=max_date,
    )
with col_end:
    end_date = st.date_input(
        "끝 날짜",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )

if start_date > end_date:
    st.error("❗ 시작 날짜가 끝 날짜보다 늦을 수는 없어요. 날짜를 다시 선택해 주세요.")
    st.stop()

mask = (df[date_col] >= pd.to_datetime(start_date)) & (df[date_col] <= pd.to_datetime(end_date))
fdf = df[mask].copy()

st.caption(f"선택한 기간: **{start_date} ~ {end_date}**, 총 {len(fdf)}건")

if fdf.empty:
    st.warning("선택한 기간에 해당하는 데이터가 없어요. 날짜 범위를 조금 넓혀보세요.")
    st.stop()


# 6️⃣ 요약 카드 (수입 / 지출 / 잔액)
st.subheader("3️⃣ 이번 기간 요약")

total_income = fdf.loc[fdf["__구분"].str.contains("수입"), amount_col].sum()
total_expense = fdf.loc[fdf["__구분"].str.contains("지출"), amount_col].sum()

# 수입/지출 구분이 없어서 전부 지출로 들어가는 경우 대비
if (total_income == 0) and (not fdf["__구분"].str.contains("수입").any()):
    total_expense = fdf[amount_col].sum()

balance = total_income - total_expense

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("총 수입", f"₩{total_income:,.0f}")
with c2:
    st.metric("총 지출", f"₩{total_expense:,.0f}")
with c3:
    st.metric("수입 - 지출", f"₩{balance:,.0f}")


# 7️⃣ 카테고리별 지출 정리
st.subheader("4️⃣ 카테고리별 지출 정리")

if main_cat_col is not None:
    group_cols = [main_cat_col]
    if sub_cat_col is not None:
        group_cols.append(sub_cat_col)

    exp_only = fdf
    if "지출" in fdf["__구분"].unique():
        exp_only = fdf[fdf["__구분"].str.contains("지출")]

    cat_summary = (
        exp_only.groupby(group_cols)[amount_col]
        .sum()
        .reset_index()
        .sort_values(amount_col, ascending=False)
    )

    cat_display = cat_summary.copy()
    cat_display[amount_col] = format_amount_series(cat_display[amount_col])

    st.dataframe(cat_display, use_container_width=True)
else:
    st.info("`분류` 컬럼을 찾지 못해서 카테고리별 합계는 생략했어요.")


# 8️⃣ 일자별 지출 흐름
st.subheader("5️⃣ 일자별 지출 흐름")

daily = (
    fdf.groupby(fdf[date_col].dt.date)[amount_col]
    .sum()
    .reset_index()
    .rename(columns={date_col: "날짜", amount_col: "지출합계"})
)

st.line_chart(
    daily.set_index("날짜")["지출합계"],
    use_container_width=True,
)


# 9️⃣ 피드백 작성 구역
st.subheader("6️⃣ 이번 기간 소비 피드백 작성하기 📝")

st.markdown(
    """
이번 기간 지출을 보면서 아래에 자유롭게 정리해 보세요.  
예: 잘한 소비 / 아쉬운 소비 / 다음 기간에 바꾸고 싶은 점 등
"""
)

col_a, col_b = st.columns(2)

with col_a:
    good = st.text_area(
        "😊 이번 기간, 잘한 소비 / 만족스러운 선택",
        placeholder="예) 운동복을 세일할 때 미리 사두어서, 오래 입을 수 있는 기본템 위주로 잘 샀다.",
        height=150,
        key="good_feedback",
    )

with col_b:
    bad = st.text_area(
        "🤔 이번 기간, 아쉬운 소비 / 줄이고 싶은 패턴",
        placeholder="예) 스트레스 받을 때마다 배달 음식을 시켜서 지출이 늘어났다.",
        height=150,
        key="bad_feedback",
    )

plan = st.text_area(
    "🎯 다음 기간 실천 목표 (3가지 정도 적어보기)",
    placeholder="예)\n1) 배달은 주 1회로 제한하기\n2) 옷은 'One in, One out' 원칙 지키기\n3) 충동구매가 올라오면 24시간 고민하고 사기",
    height=160,
    key="plan_feedback",
)


# 🔟 복사해서 저장하기 좋은 요약 텍스트
st.markdown("---")
st.subheader("7️⃣ 복사해서 저장하기 좋은 요약 텍스트")

title_text = st.text_input(
    "이 기간을 부를 제목을 정해볼까요? (예: 12월 마지막 주 소비 리포트)",
    value=f"{start_date} ~ {end_date} 소비 리포트",
)

if st.button("📋 요약 텍스트 만들기"):
    summary_lines = [
        f"# {title_text}",
        "",
        f"- 기간: {start_date} ~ {end_date}",
        f"- 총 수입: ₩{total_income:,.0f}",
        f"- 총 지출: ₩{total_expense:,.0f}",
        f"- 수입 - 지출: ₩{balance:,.0f}",
        "",
        "## 😊 잘한 소비",
        good if good.strip() else "- (아직 작성 안 함)",
        "",
        "## 🤔 아쉬운 소비",
        bad if bad.strip() else "- (아직 작성 안 함)",
        "",
        "## 🎯 다음 기간 실천 목표",
        plan if plan.strip() else "- (아직 작성 안 함)",
    ]
    summary_text = "\n".join(summary_lines)

    st.success("아래 내용을 통째로 복사해서 일기 / 노션 / 메모장에 붙여넣으면 좋아요!")
    st.code(summary_text, language="markdown")
