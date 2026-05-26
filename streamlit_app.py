"""
AI 学習計画生成アプリ（Streamlit版）
APIあり: AI自動生成  /  APIなし: 手動モード
計画表示: カレンダーグリッド
"""

import os
import json
import urllib.request
import calendar
from datetime import date, datetime, timedelta
import streamlit as st

st.set_page_config(
    page_title="AI 学習計画ジェネレーター",
    page_icon="🎯",
    layout="centered",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }

.main-title { font-size: 2rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.2rem; }
.subtitle   { color: #666; margin-bottom: 2rem; }

.plan-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; border-radius: 16px; padding: 1.5rem 2rem; margin-bottom: 1.2rem;
}
.plan-card h2  { margin: 0 0 0.5rem 0; font-size: 1.4rem; }
.plan-card .meta { opacity: 0.85; font-size: 0.9rem; }

/* カレンダー全体 */
.cal-wrapper { margin-bottom: 1.8rem; }
.cal-month-header {
    font-size: 1rem; font-weight: 700; color: #1a1a2e;
    margin: 1.2rem 0 0.5rem 0; letter-spacing: 1px;
}
.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
}
.cal-dow {
    text-align: center; font-size: 0.7rem; font-weight: 700;
    padding: 4px 0; color: #888;
}
.cal-dow.sun { color: #c0392b; }
.cal-dow.sat { color: #2980b9; }

/* 日付セル */
.cal-cell {
    border-radius: 8px;
    padding: 5px 4px 6px 4px;
    min-height: 64px;
    background: #f8f8f8;
    border: 1px solid #eee;
    font-size: 0.72rem;
    position: relative;
    vertical-align: top;
}
.cal-cell.empty   { background: transparent; border-color: transparent; }
.cal-cell.weekend { background: #fef6f6; }
.cal-cell.today   { border: 2px solid #667eea; background: #f0eeff; }
.cal-cell.exam    { border: 2px solid #e74c3c; background: #fff0f0; }
.cal-cell.has-task { background: #fff; }

.cal-day-num {
    font-size: 0.75rem; font-weight: 700; color: #555;
    display: block; margin-bottom: 3px;
}
.cal-cell.weekend .cal-day-num { color: #c0392b; }
.cal-cell.today   .cal-day-num { color: #5540d0; }
.cal-cell.exam    .cal-day-num { color: #e74c3c; }

/* タスクチップ */
.cal-task {
    font-size: 0.65rem; line-height: 1.3;
    border-radius: 4px; padding: 2px 4px;
    margin-top: 2px; display: block;
    white-space: normal; word-break: break-all;
}
.cal-task.study  { background: #e8f0ff; color: #2c3e8a; }
.cal-task.review { background: #fff3cd; color: #7a5000; font-weight: 700; }
.cal-task.exam-label { background: #fde8e8; color: #c0392b; font-weight: 700; }

/* 凡例 */
.legend { display: flex; gap: 12px; flex-wrap: wrap; margin: 0.5rem 0 1rem 0; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 0.75rem; color: #555; }
.legend-dot { width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }

.advice-box { background: #f8f5ff; border-left: 4px solid #764ba2; border-radius: 0 8px 8px 0; padding: 1rem 1.2rem; margin-top: 1rem; }
.advice-box h4  { margin: 0 0 0.6rem 0; color: #764ba2; }
.advice-item    { margin: 0.4rem 0; font-size: 0.9rem; color: #444; }

.stButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white; border: none; border-radius: 10px;
    font-weight: 700; font-size: 1rem; padding: 0.6rem 2rem;
    width: 100%; transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.88; color: white; }
</style>
""", unsafe_allow_html=True)


# ─── 定数 ────────────────────────────────────────────────
WEEKDAYS_SHORT = ["月", "火", "水", "木", "金", "土", "日"]
HOURS_OPTIONS = {
    "30分": 0.5, "1時間": 1.0, "1時間30分": 1.5,
    "2時間": 2.0, "3時間": 3.0, "4時間以上": 4.0,
}


# ─── 手動モード：計画を自動構築 ───────────────────────────
def build_manual_plan(exam_name, exam_date, daily_minutes, subjects):
    today = date.today()
    days_left = (exam_date - today).days
    max_days = min(days_left, 21)
    days = []
    study_day_index = 0
    recent_subjects = []

    for offset in range(max_days):
        d = today + timedelta(days=offset)
        is_weekend = d.weekday() >= 5

        if study_day_index > 0 and study_day_index % 3 == 0:
            recap = "・".join(dict.fromkeys(recent_subjects[-3:]))
            mins = max(20, daily_minutes // 2) if not is_weekend else max(15, daily_minutes // 3)
            days.append({"date": d.isoformat(), "task": f"復習：{recap}", "minutes": mins, "is_review": True})
            recent_subjects = []
            study_day_index += 1
            continue

        if subjects:
            subj = subjects[study_day_index % len(subjects)]
            task_name = subj["name"]
            mins_base = subj.get("minutes", daily_minutes)
        else:
            task_name = exam_name + " 学習"
            mins_base = daily_minutes

        mins = mins_base if not is_weekend else max(20, mins_base // 2)
        days.append({"date": d.isoformat(), "task": task_name, "minutes": mins, "is_review": False})
        recent_subjects.append(task_name)
        study_day_index += 1

    total_hours = round(sum(d["minutes"] for d in days) / 60)
    return {
        "title": f"{exam_name} 学習計画",
        "totalHours": total_hours,
        "advice": [
            "3日おきの復習日は必ず守りましょう。記憶の定着に効果的です。",
            "週末は学習量を抑えて疲れを溜めないようにしましょう。",
            "復習日には問題演習も取り入れると理解が深まります。",
        ],
        "days": days,
    }


# ─── AI モード ────────────────────────────────────────────
def generate_plan_ai(exam_name, exam_date, daily_hours, subjects_text, api_key):
    today = date.today()
    days_left = (exam_date - today).days
    prompt = f"""あなたは学習計画の専門家です。以下の情報をもとに、具体的な学習計画をJSON形式で返してください。

試験名・目標: {exam_name}
試験日: {exam_date.isoformat()}
今日: {today.isoformat()}
残り日数: {days_left}日
1日の学習時間: {daily_hours}時間
得意・苦手: {subjects_text or 'なし'}

JSONのみを返してください。Markdownのコードブロックは不要です。構造は以下の通りです：
{{
  "title": "計画タイトル（短く）",
  "totalHours": 数字（合計学習時間の概算・整数）,
  "advice": ["アドバイス1", "アドバイス2", "アドバイス3"],
  "days": [
    {{ "date": "YYYY-MM-DD", "task": "その日にやること（具体的に40字以内）", "minutes": 数字, "is_review": true or false }}
  ]
}}
daysは最大21日分（3週間）まで。週末は少し軽めにしてください。
【復習ルール】3日おきに必ず復習日を設けてください（4日目、8日目、12日目…）。復習日は is_review: true とし、taskには「復習：〇〇」のように直近3日間の内容をまとめて復習する旨を書いてください。復習日の学習時間は通常日より少し短めにしてください。"""

    payload = json.dumps({
        "model": "claude-opus-4-5",
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    raw = data["content"][0]["text"].strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ─── カレンダー表示 ────────────────────────────────────────
def render_calendar(plan, exam_date):
    today = date.today()
    days_left = (exam_date - today).days
    title = plan.get("title", "学習計画")
    total_hours = plan.get("totalHours", "?")

    # サマリーカード
    st.markdown(f"""
    <div class="plan-card">
      <h2>🎯 {title}</h2>
      <div class="meta">試験まで <strong>{days_left}日</strong>　｜　合計学習時間 <strong>{total_hours}時間</strong></div>
    </div>
    """, unsafe_allow_html=True)

    # 凡例
    st.markdown("""
    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:#e8f0ff;border:1px solid #b3c6ff"></div>学習日</div>
      <div class="legend-item"><div class="legend-dot" style="background:#fff3cd;border:1px solid #ffd700"></div>🔄 復習日</div>
      <div class="legend-item"><div class="legend-dot" style="background:#fde8e8;border:1px solid #f5a0a0"></div>🎯 試験日</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f0eeff;border:2px solid #667eea"></div>今日</div>
    </div>
    """, unsafe_allow_html=True)

    # day_map: date → {task, minutes, is_review}
    day_map = {}
    for d in plan.get("days", []):
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        day_map[dt] = d
    day_map[exam_date] = {"task": "🎯 試験日", "minutes": 0, "is_review": False, "is_exam": True}

    # 表示する月のリストを作成（計画範囲）
    all_dates = sorted(day_map.keys())
    if not all_dates:
        return

    # 月ごとにグループ化
    months = sorted(set((d.year, d.month) for d in all_dates))

    for year, month in months:
        month_label = f"{year}年{month}月"
        st.markdown(f'<div class="cal-month-header">📅 {month_label}</div>', unsafe_allow_html=True)

        # 月の全日付を取得
        _, num_days = calendar.monthrange(year, month)
        first_weekday = date(year, month, 1).weekday()  # 月曜=0

        # 曜日ヘッダー（月〜日）
        dow_html = ""
        dow_labels = ["月", "火", "水", "木", "金", "土", "日"]
        dow_classes = ["", "", "", "", "", "sat", "sun"]
        for lbl, cls in zip(dow_labels, dow_classes):
            dow_html += f'<div class="cal-dow {cls}">{lbl}</div>'

        # セル生成
        cells_html = ""
        # 月初の空白セル
        for _ in range(first_weekday):
            cells_html += '<div class="cal-cell empty"></div>'

        for day_num in range(1, num_days + 1):
            d = date(year, month, day_num)
            is_weekend = d.weekday() >= 5
            is_today = (d == today)
            entry = day_map.get(d)
            is_exam_day = entry and entry.get("is_exam", False)
            is_review = entry and entry.get("is_review", False)
            has_task = entry is not None

            # セルのクラス
            cell_cls = "cal-cell"
            if is_exam_day:
                cell_cls += " exam"
            elif is_today:
                cell_cls += " today"
            elif is_weekend:
                cell_cls += " weekend"
            if has_task and not is_exam_day:
                cell_cls += " has-task"

            # 日付番号
            cells_html += f'<div class="{cell_cls}"><span class="cal-day-num">{day_num}</span>'

            # タスクチップ
            if entry:
                task_text = entry.get("task", "")
                mins = entry.get("minutes", 0)
                if is_exam_day:
                    cells_html += f'<span class="cal-task exam-label">{task_text}</span>'
                elif is_review:
                    short = task_text[:12] + "…" if len(task_text) > 12 else task_text
                    cells_html += f'<span class="cal-task review">🔄 {short}<br>{mins}分</span>'
                else:
                    short = task_text[:10] + "…" if len(task_text) > 10 else task_text
                    cells_html += f'<span class="cal-task study">{short}<br>{mins}分</span>'

            cells_html += '</div>'

        st.markdown(f"""
        <div class="cal-wrapper">
          <div class="cal-grid">{dow_html}{cells_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # アドバイス
    advice = plan.get("advice", [])
    if advice:
        items_html = "".join(f'<div class="advice-item">• {tip}</div>' for tip in advice)
        st.markdown(f"""
        <div class="advice-box">
          <h4>💡 アドバイス</h4>
          {items_html}
        </div>
        """, unsafe_allow_html=True)


def plan_to_markdown(plan, exam_date, exam_name):
    today = date.today()
    days_left = (exam_date - today).days
    lines = [
        f"# {plan.get('title', '学習計画')}",
        f"試験日: {exam_date.isoformat()}  残り: {days_left}日",
        f"合計学習時間: {plan.get('totalHours', '?')}時間\n",
        "## スケジュール\n",
    ]
    week_num = 0
    for i, d in enumerate(plan.get("days", [])):
        if i % 7 == 0:
            week_num += 1
            lines.append(f"\n### 第{week_num}週\n")
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        wd = WEEKDAYS_SHORT[dt.weekday()]
        review_mark = "【復習】" if d.get("is_review") else ""
        lines.append(f"- {dt.strftime('%m/%d')}({wd}) {review_mark}{d['task']}（{d['minutes']}分）")
    lines.append("\n## アドバイス\n")
    for tip in plan.get("advice", []):
        lines.append(f"- {tip}")
    return "\n".join(lines)


# ─── メイン UI ────────────────────────────────────────────
st.markdown('<div class="main-title">🎯 学習計画ジェネレーター</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">試験・目標に向けた学習計画を自動生成します（3日おき復習つき）</div>', unsafe_allow_html=True)

api_key = st.session_state.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))

mode_col, _ = st.columns([2, 3])
with mode_col:
    mode = st.radio(
        "モード",
        ["🤖 AIで自動生成", "✏️ 手動で作成"],
        index=0 if api_key else 1,
        horizontal=True,
        label_visibility="collapsed",
    )

if mode == "🤖 AIで自動生成":
    with st.expander("🔑 API キー設定", expanded=not api_key):
        api_key_input = st.text_input(
            "Anthropic API キー", type="password", value=api_key, placeholder="sk-ant-...",
        )
        if api_key_input:
            st.session_state["api_key"] = api_key_input
            api_key = api_key_input

st.divider()

col1, col2 = st.columns([2, 1])
with col1:
    exam_name = st.text_input("📝 試験名・目標", placeholder="例: 英検2級、TOEIC 700点、定期テスト")
with col2:
    exam_date = st.date_input(
        "📅 試験日",
        value=date.today() + timedelta(days=30),
        min_value=date.today() + timedelta(days=1),
    )

daily_hours_label = st.selectbox("⏰ 1日の学習時間", list(HOURS_OPTIONS.keys()), index=1)
daily_hours = HOURS_OPTIONS[daily_hours_label]
daily_minutes = int(daily_hours * 60)

if mode == "🤖 AIで自動生成":
    subjects_text = st.text_input("📚 得意・苦手科目（任意）", placeholder="例: 数学が苦手、英語は得意")
else:
    st.markdown("##### 📚 科目ごとの学習時間（任意）")
    st.caption("科目を追加すると、3日ごとにローテーションして割り当てます。空欄なら試験名で統一。")

    if "manual_subjects" not in st.session_state:
        st.session_state["manual_subjects"] = [{"name": "", "minutes": daily_minutes}]

    subjects_list = st.session_state["manual_subjects"]
    for idx in range(len(subjects_list)):
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            subjects_list[idx]["name"] = st.text_input(
                f"科目{idx+1}", value=subjects_list[idx]["name"],
                placeholder="例: 数学", key=f"subj_name_{idx}", label_visibility="collapsed"
            )
        with c2:
            subjects_list[idx]["minutes"] = st.number_input(
                "分", value=subjects_list[idx]["minutes"],
                min_value=10, max_value=300, step=10,
                key=f"subj_min_{idx}", label_visibility="collapsed"
            )
        with c3:
            if len(subjects_list) > 1 and st.button("✕", key=f"del_{idx}"):
                subjects_list.pop(idx)
                st.rerun()

    if st.button("＋ 科目を追加", use_container_width=False):
        subjects_list.append({"name": "", "minutes": daily_minutes})
        st.rerun()

st.divider()

btn_label = "✨ AIで学習計画を生成する" if mode == "🤖 AIで自動生成" else "📋 学習計画を作成する"
if st.button(btn_label):
    if not exam_name:
        st.error("試験名・目標を入力してください")
    elif mode == "🤖 AIで自動生成" and not api_key:
        st.error("APIキーを設定するか、手動モードに切り替えてください")
    else:
        if mode == "🤖 AIで自動生成":
            with st.spinner("AIが学習計画を生成中..."):
                try:
                    plan = generate_plan_ai(exam_name, exam_date, daily_hours, subjects_text, api_key)
                    st.session_state["plan"] = plan
                    st.session_state["exam_date"] = exam_date
                    st.session_state["exam_name"] = exam_name
                    st.success("計画が生成されました！")
                except json.JSONDecodeError:
                    st.error("AIの応答を解析できませんでした。もう一度試してください。")
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        else:
            filled = [s for s in st.session_state["manual_subjects"] if s["name"].strip()]
            plan = build_manual_plan(exam_name, exam_date, daily_minutes, filled)
            st.session_state["plan"] = plan
            st.session_state["exam_date"] = exam_date
            st.session_state["exam_name"] = exam_name
            st.success("計画を作成しました！")

if "plan" in st.session_state:
    st.divider()
    render_calendar(st.session_state["plan"], st.session_state["exam_date"])

    st.divider()
    md_text = plan_to_markdown(
        st.session_state["plan"],
        st.session_state["exam_date"],
        st.session_state["exam_name"],
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "📄 Markdown でダウンロード",
            data=md_text,
            file_name=f"study_plan_{st.session_state['exam_name'][:10]}_{date.today()}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "📦 JSON でダウンロード",
            data=json.dumps(st.session_state["plan"], ensure_ascii=False, indent=2),
            file_name=f"study_plan_{st.session_state['exam_name'][:10]}_{date.today()}.json",
            mime="application/json",
            use_container_width=True,
        )