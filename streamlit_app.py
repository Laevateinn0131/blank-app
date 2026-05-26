"""
AI 学習計画生成アプリ（にゃんこ大戦争風）
"""

import os
import json
import urllib.request
from datetime import date, datetime, timedelta
import streamlit as st

st.set_page_config(
    page_title="にゃんこ学習大戦争",
    page_icon="🐱",
    layout="centered",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DotGothic16&family=Noto+Sans+JP:wght@400;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'DotGothic16', 'Noto Sans JP', monospace !important;
    background-color: #1a0a2e !important;
}

.stApp {
    background: #1a0a2e;
}

/* タイトル画面 */
.nyanko-title {
    text-align: center;
    padding: 1.5rem 0 0.5rem 0;
}
.nyanko-title h1 {
    font-size: 2.2rem;
    color: #FFD700;
    text-shadow: 3px 3px 0px #c00, -1px -1px 0px #c00, 1px -1px 0px #c00, -1px 1px 0px #c00;
    letter-spacing: 4px;
    margin: 0;
    line-height: 1.2;
}
.nyanko-title .sub {
    color: #FF8C00;
    font-size: 0.85rem;
    letter-spacing: 2px;
    margin-top: 4px;
}

/* HPバー風ステータス */
.hp-bar-container {
    background: #0d001a;
    border: 2px solid #444;
    border-radius: 4px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
}
.hp-label {
    color: #aaa;
    font-size: 0.7rem;
    margin-bottom: 4px;
    letter-spacing: 1px;
}
.hp-bar-outer {
    background: #111;
    border: 1px solid #333;
    border-radius: 2px;
    height: 16px;
    position: relative;
    overflow: hidden;
}
.hp-bar-inner {
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s;
}
.hp-bar-green  { background: linear-gradient(90deg, #2ecc40, #00ff88); }
.hp-bar-yellow { background: linear-gradient(90deg, #f0a500, #ffd700); }
.hp-bar-red    { background: linear-gradient(90deg, #c0392b, #ff4136); }
.hp-bar-blue   { background: linear-gradient(90deg, #0074d9, #7fdbff); }
.hp-bar-text {
    position: absolute;
    right: 6px;
    top: 0;
    line-height: 16px;
    font-size: 0.65rem;
    color: #fff;
    font-weight: bold;
}

/* ステージ選択カード */
.stage-card {
    background: #0d001a;
    border: 2px solid #555;
    border-radius: 6px;
    padding: 0.7rem 1rem;
    margin: 0.4rem 0;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}
.stage-card:hover {
    border-color: #FFD700;
    background: #1a0a2e;
}
.stage-card.selected {
    border-color: #FFD700;
    background: #2a1a00;
}
.stage-number {
    color: #FFD700;
    font-size: 0.7rem;
    letter-spacing: 1px;
}
.stage-name {
    color: #fff;
    font-size: 0.9rem;
    font-weight: bold;
}

/* バトルフィールド（スケジュール） */
.battle-field {
    background: #0a001a;
    border: 2px solid #444;
    border-top: 4px solid #FFD700;
    border-radius: 0 0 6px 6px;
    padding: 0.5rem;
    margin-top: -2px;
}

/* 敵キャラ行 */
.enemy-row {
    display: flex;
    align-items: center;
    padding: 5px 8px;
    border-bottom: 1px solid #1a0a2e;
    gap: 8px;
}
.enemy-row:last-child { border-bottom: none; }
.enemy-icon {
    font-size: 1.2rem;
    min-width: 28px;
    text-align: center;
}
.enemy-date {
    color: #FFD700;
    font-size: 0.75rem;
    min-width: 48px;
    letter-spacing: 1px;
}
.enemy-wd-normal { color: #aaa; font-size: 0.7rem; min-width: 20px; }
.enemy-wd-weekend { color: #ff4444; font-size: 0.7rem; min-width: 20px; }
.enemy-task { color: #ddd; font-size: 0.8rem; flex: 1; }
.enemy-mins { color: #00ff88; font-size: 0.75rem; font-weight: bold; min-width: 40px; text-align: right; }

/* 週ヘッダー */
.week-banner {
    background: #FFD700;
    color: #000;
    font-size: 0.75rem;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 3px 10px;
    margin: 6px 0 0 0;
    border-radius: 3px 3px 0 0;
    display: inline-block;
}

/* ドロップ/報酬ボックス（アドバイス） */
.reward-box {
    background: #0d001a;
    border: 2px solid #FFD700;
    border-radius: 6px;
    padding: 0.8rem 1rem;
    margin-top: 1rem;
}
.reward-title {
    color: #FFD700;
    font-size: 0.8rem;
    letter-spacing: 2px;
    margin-bottom: 0.5rem;
}
.reward-item {
    color: #fff;
    font-size: 0.82rem;
    padding: 3px 0;
    display: flex;
    align-items: flex-start;
    gap: 6px;
}
.reward-bullet { color: #FFD700; }

/* ボス登場バナー（合計） */
.boss-banner {
    background: linear-gradient(90deg, #c00 0%, #800 50%, #c00 100%);
    border: 2px solid #ff4444;
    border-radius: 4px;
    padding: 0.6rem 1rem;
    text-align: center;
    margin: 0.8rem 0;
}
.boss-banner .boss-text {
    color: #FFD700;
    font-size: 1.1rem;
    letter-spacing: 3px;
    font-weight: bold;
    text-shadow: 2px 2px 0 #000;
}
.boss-banner .boss-sub {
    color: #ffa;
    font-size: 0.75rem;
    letter-spacing: 1px;
}

/* Streamlit ウィジェット上書き */
.stTextInput > div > div > input {
    background: #0d001a !important;
    color: #fff !important;
    border: 2px solid #555 !important;
    border-radius: 4px !important;
    font-family: 'DotGothic16', monospace !important;
}
.stTextInput > div > div > input:focus {
    border-color: #FFD700 !important;
    box-shadow: none !important;
}
.stSelectbox > div > div {
    background: #0d001a !important;
    color: #fff !important;
    border: 2px solid #555 !important;
    border-radius: 4px !important;
    font-family: 'DotGothic16', monospace !important;
}
.stDateInput > div > div > input {
    background: #0d001a !important;
    color: #fff !important;
    border: 2px solid #555 !important;
    font-family: 'DotGothic16', monospace !important;
}
label, .stSelectbox label, .stTextInput label, .stDateInput label {
    color: #aaa !important;
    font-family: 'DotGothic16', monospace !important;
    font-size: 0.8rem !important;
    letter-spacing: 1px !important;
}

/* ボタン */
.stButton > button {
    background: #c00 !important;
    color: #FFD700 !important;
    border: 2px solid #ff4444 !important;
    border-radius: 4px !important;
    font-family: 'DotGothic16', monospace !important;
    font-size: 1rem !important;
    font-weight: bold !important;
    letter-spacing: 3px !important;
    width: 100% !important;
    padding: 0.6rem !important;
    text-shadow: 1px 1px 0 #000 !important;
    transition: background 0.15s !important;
}
.stButton > button:hover {
    background: #e00 !important;
    color: #fff !important;
}

/* エキスパンダー */
.streamlit-expanderHeader {
    background: #0d001a !important;
    color: #FFD700 !important;
    border: 2px solid #555 !important;
    font-family: 'DotGothic16', monospace !important;
    font-size: 0.8rem !important;
}
.streamlit-expanderContent {
    background: #0d001a !important;
    border: 2px solid #555 !important;
    border-top: none !important;
}

/* ダウンロードボタン */
.stDownloadButton > button {
    background: #003366 !important;
    color: #7fdbff !important;
    border: 2px solid #0074d9 !important;
    border-radius: 4px !important;
    font-family: 'DotGothic16', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 1px !important;
    padding: 0.4rem !important;
}

/* セパレータ */
hr { border-color: #333 !important; }

/* アラート */
.stAlert {
    font-family: 'DotGothic16', monospace !important;
    background: #0d001a !important;
    border-left: 4px solid #FFD700 !important;
    color: #fff !important;
}

/* スピナー */
.stSpinner > div { color: #FFD700 !important; }

/* サイドバー非表示 */
section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)


WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
HOURS_OPTIONS = {
    "30分": 0.5,
    "1時間": 1.0,
    "1時間30分": 1.5,
    "2時間": 2.0,
    "3時間": 3.0,
    "4時間以上": 4.0,
}

# 敵キャラアイコン（曜日・負荷によって変える）
def get_enemy_icon(weekday: int, minutes: int) -> str:
    if weekday >= 5:  # 週末
        return "😴"
    if minutes >= 120:
        return "👿"
    if minutes >= 90:
        return "😤"
    if minutes >= 60:
        return "😾"
    return "🐱"

def generate_plan(exam_name, exam_date, daily_hours, subjects, api_key):
    today = date.today()
    days_left = (exam_date - today).days
    prompt = f"""あなたは学習計画の専門家です。以下の情報をもとに、具体的な学習計画をJSON形式で返してください。

試験名・目標: {exam_name}
試験日: {exam_date.isoformat()}
今日: {today.isoformat()}
残り日数: {days_left}日
1日の学習時間: {daily_hours}時間
得意・苦手: {subjects or 'なし'}

JSONのみを返してください。Markdownのコードブロックは不要です。構造は以下の通りです：
{{
  "title": "計画タイトル（短く）",
  "totalHours": 数字（合計学習時間の概算・整数）,
  "advice": ["アドバイス1", "アドバイス2", "アドバイス3"],
  "days": [
    {{ "date": "YYYY-MM-DD", "task": "その日にやること（具体的に40字以内）", "minutes": 数字 }}
  ]
}}
daysは最大21日分（3週間）まで。週末は少し軽めにしてください。"""

    payload = json.dumps({
        "model": "claude-opus-4-5",
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    raw = data["content"][0]["text"].strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def render_plan(plan, exam_date):
    today = date.today()
    days_left = (exam_date - today).days
    total_hours = plan.get("totalHours", 0)
    title = plan.get("title", "学習計画")

    # HP バー（残り日数）
    max_days = max(days_left, 1)
    days_pct = min(100, int(days_left / max(days_left, 60) * 100))
    hp_class = "hp-bar-green" if days_pct > 50 else ("hp-bar-yellow" if days_pct > 25 else "hp-bar-red")

    st.markdown(f"""
    <div class="boss-banner">
      <div class="boss-text">⚔️ {title} ⚔️</div>
      <div class="boss-sub">～ 学習バトル開始！ ～</div>
    </div>
    <div style="display:flex; gap:8px;">
      <div class="hp-bar-container" style="flex:1">
        <div class="hp-label">⏳ 残り日数</div>
        <div class="hp-bar-outer">
          <div class="hp-bar-inner {hp_class}" style="width:{days_pct}%"></div>
          <span class="hp-bar-text">{days_left}日</span>
        </div>
      </div>
      <div class="hp-bar-container" style="flex:1">
        <div class="hp-label">📚 合計学習時間</div>
        <div class="hp-bar-outer">
          <div class="hp-bar-inner hp-bar-blue" style="width:100%"></div>
          <span class="hp-bar-text">{total_hours}時間</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # スケジュール
    days = plan.get("days", [])
    week_num = 0
    html_rows = ""
    for i, d in enumerate(days):
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        wd = WEEKDAYS[dt.weekday()]
        is_weekend = dt.weekday() >= 5
        minutes = d.get("minutes", 0)
        icon = get_enemy_icon(dt.weekday(), minutes)
        wd_class = "enemy-wd-weekend" if is_weekend else "enemy-wd-normal"

        if i % 7 == 0:
            week_num += 1
            if i > 0:
                html_rows += '</div>'
            html_rows += f'<div class="week-banner">📅 第{week_num}週</div><div class="battle-field">'

        html_rows += f"""
        <div class="enemy-row">
          <span class="enemy-icon">{icon}</span>
          <span class="enemy-date">{dt.strftime('%m/%d')}</span>
          <span class="{wd_class}">({wd})</span>
          <span class="enemy-task">{d.get('task','')}</span>
          <span class="enemy-mins">+{minutes}分</span>
        </div>"""

    if days:
        html_rows += '</div>'

    st.markdown(f'<div style="margin-top:1rem">{html_rows}</div>', unsafe_allow_html=True)

    # アドバイス（報酬ボックス）
    advice = plan.get("advice", [])
    if advice:
        items = "".join(
            f'<div class="reward-item"><span class="reward-bullet">►</span>{tip}</div>'
            for tip in advice
        )
        st.markdown(f"""
        <div class="reward-box">
          <div class="reward-title">🎁 ドロップ報酬：作戦ヒント</div>
          {items}
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
        wd = WEEKDAYS[dt.weekday()]
        lines.append(f"- {dt.strftime('%m/%d')}({wd}) {d['task']}（{d['minutes']}分）")
    lines.append("\n## アドバイス\n")
    for tip in plan.get("advice", []):
        lines.append(f"- {tip}")
    return "\n".join(lines)


# ─── タイトル ─────────────────────────────────────────────
st.markdown("""
<div class="nyanko-title">
  <h1>🐱 にゃんこ学習大戦争 🐱</h1>
  <div class="sub">～ AI POWERED STUDY BATTLE ～</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# API キー
with st.expander("🔑 APIキー設定（タップして開く）"):
    api_key_input = st.text_input(
        "Anthropic API キー",
        type="password",
        value=st.session_state.get("api_key", os.environ.get("ANTHROPIC_API_KEY", "")),
        placeholder="sk-ant-...",
    )
    if api_key_input:
        st.session_state["api_key"] = api_key_input

api_key = st.session_state.get("api_key", "")

st.markdown('<div style="color:#aaa; font-size:0.75rem; letter-spacing:1px; margin:0.5rem 0">▼ バトル情報を入力せよ ▼</div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])
with col1:
    exam_name = st.text_input("🎯 ボス名（試験・目標）", placeholder="例：英検2級、TOEIC 700点")
with col2:
    exam_date = st.date_input(
        "📅 決戦日",
        value=date.today() + timedelta(days=30),
        min_value=date.today() + timedelta(days=1),
    )

daily_hours_label = st.selectbox("⚔️ 1日の戦闘時間", list(HOURS_OPTIONS.keys()), index=1)
daily_hours = HOURS_OPTIONS[daily_hours_label]

subjects = st.text_input("📊 得意・苦手科目（任意）", placeholder="例：数学が苦手、英語は得意")

st.markdown("---")

if st.button("🐱 出撃！学習計画を生成する"):
    if not exam_name:
        st.error("⚠ ボス名（試験名）を入力してください！")
    elif not api_key:
        st.error("⚠ APIキーを設定してください！")
    else:
        with st.spinner("🐾 にゃんこたちが作戦会議中..."):
            try:
                plan = generate_plan(exam_name, exam_date, daily_hours, subjects, api_key)
                st.session_state["plan"] = plan
                st.session_state["exam_date"] = exam_date
                st.session_state["exam_name"] = exam_name
                st.success("🎉 作戦決定！バトル開始にゃ！")
            except json.JSONDecodeError:
                st.error("⚠ AIの応答を解析できませんでした。もう一度試してください。")
            except Exception as e:
                st.error(f"⚠ エラーが発生しました: {e}")

if "plan" in st.session_state:
    st.markdown("---")
    render_plan(st.session_state["plan"], st.session_state["exam_date"])

    st.markdown("---")
    md_text = plan_to_markdown(
        st.session_state["plan"],
        st.session_state["exam_date"],
        st.session_state["exam_name"],
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "📄 作戦書（MD）をダウンロード",
            data=md_text,
            file_name=f"study_plan_{st.session_state['exam_name'][:10]}_{date.today()}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col_b:
        st.download_button(
            "📦 データ（JSON）をダウンロード",
            data=json.dumps(st.session_state["plan"], ensure_ascii=False, indent=2),
            file_name=f"study_plan_{st.session_state['exam_name'][:10]}_{date.today()}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown(
        '<div style="text-align:center; color:#555; font-size:0.7rem; margin-top:1rem; letter-spacing:2px">🐱 NYANKO GAKUSHUU DAISENSOU 🐱</div>',
        unsafe_allow_html=True,
    )