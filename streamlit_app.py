"""
AI 学習計画生成アプリ（Streamlit版）
- APIあり: AI自動生成（単元・範囲を詳細指定）
- APIなし: 手動モード（科目→単元リストで計画）
- 表示: カレンダーグリッド
"""

import os
import json
import urllib.request
import calendar
from datetime import date, datetime, timedelta
import streamlit as st

st.set_page_config(page_title="AI 学習計画ジェネレーター", page_icon="🎯", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }

.main-title { font-size: 2rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.2rem; }
.subtitle   { color: #666; margin-bottom: 1.5rem; }

.plan-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; border-radius: 16px; padding: 1.5rem 2rem; margin-bottom: 1.2rem;
}
.plan-card h2  { margin: 0 0 0.5rem 0; font-size: 1.4rem; }
.plan-card .meta { opacity: 0.85; font-size: 0.9rem; }

.subj-block {
    border: 1.5px solid #ddd; border-radius: 10px;
    padding: 0.8rem 1rem; margin-bottom: 0.8rem; background: #fafafa;
}
.subj-block-title {
    font-weight: 700; font-size: 0.9rem; color: #333; margin-bottom: 0.5rem;
}
.unit-row {
    display: flex; align-items: center; gap: 6px;
    margin-bottom: 4px; font-size: 0.82rem;
}

/* カレンダー */
.cal-wrapper { margin-bottom: 1.8rem; }
.cal-month-header { font-size: 1rem; font-weight: 700; color: #1a1a2e; margin: 1.2rem 0 0.5rem 0; letter-spacing: 1px; }
.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; }
.cal-dow { text-align: center; font-size: 0.7rem; font-weight: 700; padding: 4px 0; color: #888; }
.cal-dow.sat { color: #2980b9; }
.cal-dow.sun { color: #c0392b; }
.cal-cell {
    border-radius: 8px; padding: 5px 4px 6px 4px; min-height: 68px;
    background: #f8f8f8; border: 1px solid #eee; font-size: 0.72rem; vertical-align: top;
}
.cal-cell.empty   { background: transparent; border-color: transparent; }
.cal-cell.weekend { background: #fef6f6; }
.cal-cell.today   { border: 2px solid #667eea; background: #f0eeff; }
.cal-cell.exam    { border: 2px solid #e74c3c; background: #fff0f0; }
.cal-cell.has-task { background: #fff; }
.cal-day-num { font-size: 0.75rem; font-weight: 700; color: #555; display: block; margin-bottom: 3px; }
.cal-cell.weekend .cal-day-num { color: #c0392b; }
.cal-cell.today   .cal-day-num { color: #5540d0; }
.cal-cell.exam    .cal-day-num { color: #e74c3c; }
.cal-task { font-size: 0.63rem; line-height: 1.3; border-radius: 4px; padding: 2px 4px; margin-top: 2px; display: block; word-break: break-all; }
.cal-task.study  { background: #e8f0ff; color: #2c3e8a; }
.cal-task.review { background: #fff3cd; color: #7a5000; font-weight: 700; }
.cal-task.exam-label { background: #fde8e8; color: #c0392b; font-weight: 700; }
.cal-subj-label { font-size: 0.58rem; color: #888; display: block; margin-top: 1px; }

.legend { display: flex; gap: 12px; flex-wrap: wrap; margin: 0.5rem 0 1rem 0; }
.legend-item { display: flex; align-items: center; gap: 4px; font-size: 0.75rem; color: #555; }
.legend-dot { width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }

.advice-box { background: #f8f5ff; border-left: 4px solid #764ba2; border-radius: 0 8px 8px 0; padding: 1rem 1.2rem; margin-top: 1rem; }
.advice-box h4   { margin: 0 0 0.6rem 0; color: #764ba2; }
.advice-item     { margin: 0.4rem 0; font-size: 0.9rem; color: #444; }

.stButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white; border: none; border-radius: 10px;
    font-weight: 700; font-size: 1rem; padding: 0.6rem 2rem;
    width: 100%; transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.88; color: white; }
</style>
""", unsafe_allow_html=True)

WEEKDAYS_SHORT = ["月", "火", "水", "木", "金", "土", "日"]
HOURS_OPTIONS = {"30分": 0.5, "1時間": 1.0, "1時間30分": 1.5, "2時間": 2.0, "3時間": 3.0, "4時間以上": 4.0}


# ─── 手動モード：単元リストから計画を構築 ─────────────────────
def build_manual_plan(exam_name: str, exam_date: date, daily_minutes: int, subjects: list) -> dict:
    """
    subjects: [
      {"name": "数学", "units": [
        {"name": "二次関数", "minutes": 60, "memo": "教科書p.30-50"},
        ...
      ]},
      ...
    ]
    単元を順に1日1つ割り当て → 3日ごとに復習日を挟む
    """
    today = date.today()
    days_left = (exam_date - today).days
    max_days = min(days_left, 42)  # 最大6週間

    # 単元をフラットなキューに展開
    unit_queue = []
    for subj in subjects:
        for unit in subj.get("units", []):
            if unit.get("name", "").strip():
                unit_queue.append({
                    "subj": subj["name"],
                    "unit": unit["name"],
                    "minutes": unit.get("minutes", daily_minutes),
                    "memo": unit.get("memo", ""),
                })
    if not unit_queue:
        unit_queue = [{"subj": exam_name, "unit": exam_name + " 学習", "minutes": daily_minutes, "memo": ""}]

    days = []
    unit_idx = 0
    study_count = 0       # 直近の学習日数（3になったら復習）
    recent_units: list[str] = []

    for offset in range(max_days):
        d = today + timedelta(days=offset)
        is_weekend = d.weekday() >= 5

        # 単元を全部消化したら終了
        if unit_idx >= len(unit_queue) and study_count < 3:
            break

        # 3日学習したら復習日
        if study_count > 0 and study_count % 3 == 0:
            recap_units = "・".join(dict.fromkeys(recent_units[-3:]))
            mins = max(20, daily_minutes // 2) if not is_weekend else max(15, daily_minutes // 3)
            days.append({
                "date": d.isoformat(),
                "task": f"復習：{recap_units}",
                "minutes": mins,
                "is_review": True,
                "subject": "",
                "memo": "",
            })
            recent_units = []
            study_count += 1
            continue

        if unit_idx >= len(unit_queue):
            break

        u = unit_queue[unit_idx]
        mins = u["minutes"] if not is_weekend else max(20, u["minutes"] // 2)
        days.append({
            "date": d.isoformat(),
            "task": u["unit"],
            "minutes": mins,
            "is_review": False,
            "subject": u["subj"],
            "memo": u["memo"],
        })
        recent_units.append(f'{u["subj"]}:{u["unit"]}')
        unit_idx += 1
        study_count += 1

    total_hours = round(sum(d["minutes"] for d in days) / 60)
    return {
        "title": f"{exam_name} 学習計画",
        "totalHours": total_hours,
        "advice": [
            "3日おきの復習日は必ず守りましょう。記憶の定着に効果的です。",
            "単元ごとに理解度をチェックし、苦手な単元は早めに追加復習しましょう。",
            "週末は問題演習に充てると実践力が身につきます。",
        ],
        "days": days,
    }


# ─── AI モード ─────────────────────────────────────────────
def generate_plan_ai(exam_name, exam_date, daily_hours, subjects_detail, api_key):
    today = date.today()
    days_left = (exam_date - today).days

    # subjects_detail を読みやすいテキストに変換
    subj_text = ""
    for s in subjects_detail:
        if not s.get("name", "").strip():
            continue
        units = s.get("units", [])
        filled = [u for u in units if u.get("name", "").strip()]
        if filled:
            unit_lines = "\n".join(
                f'    - {u["name"]}（目安{u.get("minutes", int(daily_hours*60))}分）'
                + (f'  ※{u["memo"]}' if u.get("memo") else "")
                for u in filled
            )
            subj_text += f'  【{s["name"]}】\n{unit_lines}\n'
        else:
            subj_text += f'  【{s["name"]}】（単元未指定）\n'

    prompt = f"""あなたは学習計画の専門家です。以下の情報をもとに、具体的な学習計画をJSON形式で返してください。

試験名・目標: {exam_name}
試験日: {exam_date.isoformat()}
今日: {today.isoformat()}
残り日数: {days_left}日
1日の学習時間: {daily_hours}時間

学習する科目・単元（優先的に計画に組み込んでください）:
{subj_text if subj_text else "（指定なし）"}

JSONのみを返してください。Markdownのコードブロックは不要です。構造は以下の通りです：
{{
  "title": "計画タイトル（短く）",
  "totalHours": 数字（合計学習時間の概算・整数）,
  "advice": ["アドバイス1", "アドバイス2", "アドバイス3"],
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "task": "単元名など（具体的に40字以内）",
      "subject": "科目名",
      "minutes": 数字,
      "memo": "補足メモ（任意）",
      "is_review": true or false
    }}
  ]
}}
daysは最大42日分（6週間）まで。指定された単元をすべて計画に盛り込んでください。週末は少し軽めに。
【復習ルール】3日おきに必ず復習日を設けてください。復習日は is_review: true とし、直近3日で学習した単元をまとめて復習する旨をtaskに書いてください。"""

    payload = json.dumps({
        "model": "claude-opus-4-5",
        "max_tokens": 4096,
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


# ─── カレンダー表示 ───────────────────────────────────────
def render_calendar(plan, exam_date):
    today = date.today()
    days_left = (exam_date - today).days
    title = plan.get("title", "学習計画")
    total_hours = plan.get("totalHours", "?")

    st.markdown(f"""
    <div class="plan-card">
      <h2>🎯 {title}</h2>
      <div class="meta">試験まで <strong>{days_left}日</strong>　｜　合計学習時間 <strong>{total_hours}時間</strong></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="legend">
      <div class="legend-item"><div class="legend-dot" style="background:#e8f0ff;border:1px solid #b3c6ff"></div>学習日</div>
      <div class="legend-item"><div class="legend-dot" style="background:#fff3cd;border:1px solid #ffd700"></div>🔄 復習日</div>
      <div class="legend-item"><div class="legend-dot" style="background:#fde8e8;border:1px solid #f5a0a0"></div>🎯 試験日</div>
      <div class="legend-item"><div class="legend-dot" style="background:#f0eeff;border:2px solid #667eea"></div>今日</div>
    </div>
    """, unsafe_allow_html=True)

    day_map = {}
    for d in plan.get("days", []):
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        day_map[dt] = d
    day_map[exam_date] = {"task": "🎯 試験日", "minutes": 0, "is_review": False, "is_exam": True, "subject": "", "memo": ""}

    all_dates = sorted(day_map.keys())
    if not all_dates:
        return

    months = sorted(set((d.year, d.month) for d in all_dates))

    for year, month in months:
        st.markdown(f'<div class="cal-month-header">📅 {year}年{month}月</div>', unsafe_allow_html=True)
        _, num_days = calendar.monthrange(year, month)
        first_weekday = date(year, month, 1).weekday()

        dow_html = ""
        for lbl, cls in zip(["月","火","水","木","金","土","日"], ["","","","","","sat","sun"]):
            dow_html += f'<div class="cal-dow {cls}">{lbl}</div>'

        cells_html = "".join('<div class="cal-cell empty"></div>' for _ in range(first_weekday))

        for day_num in range(1, num_days + 1):
            d = date(year, month, day_num)
            is_weekend = d.weekday() >= 5
            is_today = (d == today)
            entry = day_map.get(d)
            is_exam_day = entry and entry.get("is_exam", False)
            is_review = entry and entry.get("is_review", False)

            cell_cls = "cal-cell"
            if is_exam_day:       cell_cls += " exam"
            elif is_today:        cell_cls += " today"
            elif is_weekend:      cell_cls += " weekend"
            if entry and not is_exam_day: cell_cls += " has-task"

            cells_html += f'<div class="{cell_cls}"><span class="cal-day-num">{day_num}</span>'

            if entry:
                task = entry.get("task", "")
                mins = entry.get("minutes", 0)
                subj = entry.get("subject", "")
                memo = entry.get("memo", "")
                short_task = task[:10] + "…" if len(task) > 10 else task
                short_memo = f' ({memo[:8]}…)' if memo and len(memo) > 8 else (f' ({memo})' if memo else "")

                if is_exam_day:
                    cells_html += f'<span class="cal-task exam-label">{task}</span>'
                elif is_review:
                    cells_html += f'<span class="cal-task review">🔄 {short_task}<br>{mins}分</span>'
                else:
                    cells_html += f'<span class="cal-task study">{short_task}<br>{mins}分</span>'
                    if subj:
                        cells_html += f'<span class="cal-subj-label">📘 {subj}{short_memo}</span>'

            cells_html += '</div>'

        st.markdown(f'<div class="cal-wrapper"><div class="cal-grid">{dow_html}{cells_html}</div></div>', unsafe_allow_html=True)

    advice = plan.get("advice", [])
    if advice:
        items_html = "".join(f'<div class="advice-item">• {tip}</div>' for tip in advice)
        st.markdown(f'<div class="advice-box"><h4>💡 アドバイス</h4>{items_html}</div>', unsafe_allow_html=True)


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
        subj = f'[{d["subject"]}] ' if d.get("subject") else ""
        memo = f'  ※{d["memo"]}' if d.get("memo") else ""
        lines.append(f"- {dt.strftime('%m/%d')}({wd}) {review_mark}{subj}{d['task']}（{d['minutes']}分）{memo}")
    lines.append("\n## アドバイス\n")
    for tip in plan.get("advice", []):
        lines.append(f"- {tip}")
    return "\n".join(lines)


# ─── 科目・単元入力ウィジェット ────────────────────────────
def subjects_editor(daily_minutes: int):
    """
    session_state["subjects"] を編集するUI。
    subjects = [{"name": str, "units": [{"name": str, "minutes": int, "memo": str}]}]
    """
    if "subjects" not in st.session_state:
        st.session_state["subjects"] = [
            {"name": "", "units": [{"name": "", "minutes": daily_minutes, "memo": ""}]}
        ]

    subjects = st.session_state["subjects"]
    to_delete_subj = None

    for si, subj in enumerate(subjects):
        with st.container():
            st.markdown(f'<div class="subj-block">', unsafe_allow_html=True)

            sc1, sc2 = st.columns([5, 1])
            with sc1:
                subj["name"] = st.text_input(
                    "科目名", value=subj["name"],
                    placeholder="例：数学、英語、物理",
                    key=f"subj_{si}", label_visibility="visible"
                )
            with sc2:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                if st.button("科目を削除", key=f"del_subj_{si}"):
                    to_delete_subj = si

            # 単元リスト
            st.caption("単元・範囲（行を追加して具体的に入力）")
            col_headers = st.columns([3, 1, 2])
            col_headers[0].markdown("<small>**単元名・範囲**</small>", unsafe_allow_html=True)
            col_headers[1].markdown("<small>**時間(分)**</small>", unsafe_allow_html=True)
            col_headers[2].markdown("<small>**メモ（教科書ページなど）**</small>", unsafe_allow_html=True)

            to_delete_unit = None
            for ui, unit in enumerate(subj["units"]):
                uc1, uc2, uc3, uc4 = st.columns([3, 1, 2, 0.5])
                with uc1:
                    unit["name"] = st.text_input(
                        "単元", value=unit["name"],
                        placeholder="例：二次関数",
                        key=f"unit_name_{si}_{ui}", label_visibility="collapsed"
                    )
                with uc2:
                    unit["minutes"] = st.number_input(
                        "分", value=unit["minutes"],
                        min_value=10, max_value=300, step=10,
                        key=f"unit_min_{si}_{ui}", label_visibility="collapsed"
                    )
                with uc3:
                    unit["memo"] = st.text_input(
                        "メモ", value=unit.get("memo", ""),
                        placeholder="例：p.30-50、苦手",
                        key=f"unit_memo_{si}_{ui}", label_visibility="collapsed"
                    )
                with uc4:
                    if len(subj["units"]) > 1 and st.button("✕", key=f"del_unit_{si}_{ui}"):
                        to_delete_unit = ui

            if to_delete_unit is not None:
                subj["units"].pop(to_delete_unit)
                st.rerun()

            if st.button("＋ 単元を追加", key=f"add_unit_{si}"):
                subj["units"].append({"name": "", "minutes": daily_minutes, "memo": ""})
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

    if to_delete_subj is not None:
        subjects.pop(to_delete_subj)
        st.rerun()

    if st.button("＋ 科目を追加"):
        subjects.append({"name": "", "units": [{"name": "", "minutes": daily_minutes, "memo": ""}]})
        st.rerun()

    return subjects


# ─── メイン UI ────────────────────────────────────────────
st.markdown('<div class="main-title">🎯 学習計画ジェネレーター</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">科目・単元を指定して、3日おき復習つきの学習計画を作成します</div>', unsafe_allow_html=True)

api_key = st.session_state.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))

mode_col, _ = st.columns([2, 3])
with mode_col:
    mode = st.radio(
        "モード", ["🤖 AIで自動生成", "✏️ 手動で作成"],
        index=0 if api_key else 1, horizontal=True, label_visibility="collapsed",
    )

if mode == "🤖 AIで自動生成":
    with st.expander("🔑 API キー設定", expanded=not api_key):
        api_key_input = st.text_input("Anthropic API キー", type="password", value=api_key, placeholder="sk-ant-...")
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

st.divider()
st.markdown("##### 📚 科目・単元の入力")
subjects = subjects_editor(daily_minutes)

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
                    plan = generate_plan_ai(exam_name, exam_date, daily_hours, subjects, api_key)
                    st.session_state["plan"] = plan
                    st.session_state["exam_date"] = exam_date
                    st.session_state["exam_name"] = exam_name
                    st.success("計画が生成されました！")
                except json.JSONDecodeError:
                    st.error("AIの応答を解析できませんでした。もう一度試してください。")
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        else:
            plan = build_manual_plan(exam_name, exam_date, daily_minutes, subjects)
            st.session_state["plan"] = plan
            st.session_state["exam_date"] = exam_date
            st.session_state["exam_name"] = exam_name
            st.success("計画を作成しました！")

if "plan" in st.session_state:
    st.divider()
    render_calendar(st.session_state["plan"], st.session_state["exam_date"])

    st.divider()
    md_text = plan_to_markdown(
        st.session_state["plan"], st.session_state["exam_date"], st.session_state["exam_name"],
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "📄 Markdown でダウンロード", data=md_text,
            file_name=f"study_plan_{st.session_state['exam_name'][:10]}_{date.today()}.md",
            mime="text/markdown", use_container_width=True,
        )
    with col_b:
        st.download_button(
            "📦 JSON でダウンロード",
            data=json.dumps(st.session_state["plan"], ensure_ascii=False, indent=2),
            file_name=f"study_plan_{st.session_state['exam_name'][:10]}_{date.today()}.json",
            mime="application/json", use_container_width=True,
        )