#!/usr/bin/env python3
"""
AI 学習計画生成 CLI ツール
Anthropic API を使って、試験・目標に向けた学習計画を自動生成します。
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta


# ─── カラー出力 ───────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[32m"
    CYAN   = "\033[36m"
    YELLOW = "\033[33m"
    RED    = "\033[31m"
    BLUE   = "\033[34m"
    WHITE  = "\033[97m"


def color(text: str, *codes: str) -> str:
    return "".join(codes) + text + C.RESET


def header(text: str) -> None:
    print(f"\n{color('  ' + text + '  ', C.BOLD, C.WHITE)}")
    print(color("  " + "─" * len(text), C.DIM))


def success(text: str) -> None:
    print(color("  ✓ " + text, C.GREEN))


def info(text: str) -> None:
    print(color("  " + text, C.DIM))


def warn(text: str) -> None:
    print(color("  ⚠ " + text, C.YELLOW))


# ─── 入力ヘルパー ─────────────────────────────────────────
def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    try:
        val = input(color(f"  {prompt}{hint}: ", C.CYAN)).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val if val else default


def ask_date(prompt: str) -> date:
    while True:
        raw = ask(prompt + " (YYYY-MM-DD)")
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            warn("日付は YYYY-MM-DD 形式で入力してください（例: 2025-06-30）")


def ask_hours(prompt: str) -> float:
    options = {"1": 0.5, "2": 1.0, "3": 1.5, "4": 2.0, "5": 3.0, "6": 4.0}
    print(color(f"\n  {prompt}", C.CYAN))
    labels = ["30分", "1時間", "1時間30分", "2時間", "3時間", "4時間以上"]
    for k, v in zip(options.keys(), labels):
        print(f"    {color(k, C.BOLD)}) {v}")
    while True:
        ch = ask("番号を選択", "2")
        if ch in options:
            return options[ch]
        warn("1〜6 の番号を入力してください")


# ─── AI 計画生成 ──────────────────────────────────────────
def generate_plan(
    exam_name: str,
    exam_date: date,
    daily_hours: float,
    subjects: str,
    api_key: str,
) -> dict:
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

    raw = data["content"][0]["text"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ─── 計画表示 ─────────────────────────────────────────────
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def display_plan(plan: dict, exam_date: date) -> None:
    today = date.today()
    days_left = (exam_date - today).days

    header(plan.get("title", "学習計画"))
    print()
    print(f"  {color('残り', C.DIM)} {color(str(days_left) + '日', C.BOLD)}  "
          f"{color('合計学習時間', C.DIM)} {color(str(plan.get('totalHours', '?')) + '時間', C.BOLD)}")
    print()

    # スケジュール
    print(color("  ── スケジュール ──", C.DIM))
    days = plan.get("days", [])
    week_num = 0
    for i, d in enumerate(days):
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        wd = WEEKDAYS[dt.weekday()]
        is_weekend = dt.weekday() >= 5

        if i % 7 == 0:
            week_num += 1
            print(color(f"\n  【第{week_num}週】", C.BOLD))

        date_str = dt.strftime("%m/%d")
        wd_colored = color(f"({wd})", C.RED if is_weekend else C.DIM)
        task = d.get("task", "")
        mins = d.get("minutes", 0)
        mins_str = color(f"{mins}分", C.YELLOW)

        print(f"    {color(date_str, C.BOLD)} {wd_colored}  {task}  {mins_str}")

    # アドバイス
    print()
    print(color("  ── アドバイス ──", C.DIM))
    for tip in plan.get("advice", []):
        print(f"    {color('•', C.BLUE)} {tip}")

    print()


# ─── 保存 ─────────────────────────────────────────────────
def save_plan(plan: dict, exam_name: str) -> None:
    safe_name = exam_name.replace(" ", "_").replace("/", "-")[:20]
    filename = f"study_plan_{safe_name}_{date.today().isoformat()}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    success(f"計画を保存しました: {filename}")


def export_text(plan: dict, exam_date: date, exam_name: str) -> None:
    lines = []
    lines.append(f"# {plan.get('title', '学習計画')}")
    lines.append(f"試験日: {exam_date.isoformat()}  残り: {(exam_date - date.today()).days}日")
    lines.append(f"合計学習時間: {plan.get('totalHours', '?')}時間\n")
    lines.append("## スケジュール\n")

    days = plan.get("days", [])
    week_num = 0
    for i, d in enumerate(days):
        if i % 7 == 0:
            week_num += 1
            lines.append(f"\n### 第{week_num}週\n")
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        wd = WEEKDAYS[dt.weekday()]
        lines.append(f"- {dt.strftime('%m/%d')}({wd}) {d['task']}（{d['minutes']}分）")

    lines.append("\n## アドバイス\n")
    for tip in plan.get("advice", []):
        lines.append(f"- {tip}")

    safe_name = exam_name.replace(" ", "_").replace("/", "-")[:20]
    filename = f"study_plan_{safe_name}_{date.today().isoformat()}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    success(f"Markdown を保存しました: {filename}")


# ─── メイン ───────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="AI 学習計画生成 CLI")
    parser.add_argument("--api-key", help="Anthropic API キー（省略時は環境変数 ANTHROPIC_API_KEY を使用）")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        warn("ANTHROPIC_API_KEY が設定されていません。")
        warn("環境変数に設定するか --api-key オプションで渡してください。")
        sys.exit(1)

    print(color("\n╔══════════════════════════════╗", C.DIM))
    print(color("║   AI 学習計画ジェネレーター  ║", C.BOLD))
    print(color("╚══════════════════════════════╝\n", C.DIM))

    # 入力
    exam_name  = ask("試験名・目標（例: 英検2級、TOEIC 700点）")
    if not exam_name:
        warn("試験名を入力してください")
        sys.exit(1)

    exam_date  = ask_date("試験日")
    if exam_date <= date.today():
        warn("試験日は明日以降を指定してください")
        sys.exit(1)

    daily_hours = ask_hours("1日に使える学習時間")
    subjects    = ask("得意・苦手科目（任意、Enterでスキップ）")

    # 生成
    print()
    print(color("  ⟳ AIが計画を生成中です...", C.CYAN))
    try:
        plan = generate_plan(exam_name, exam_date, daily_hours, subjects, api_key)
    except json.JSONDecodeError:
        warn("AIの応答を解析できませんでした。もう一度試してください。")
        sys.exit(1)
    except Exception as e:
        warn(f"エラーが発生しました: {e}")
        sys.exit(1)

    # 表示
    display_plan(plan, exam_date)

    # 保存確認
    print(color("  ── 保存オプション ──", C.DIM))
    print(f"    {color('1', C.BOLD)}) JSON として保存")
    print(f"    {color('2', C.BOLD)}) Markdown として保存")
    print(f"    {color('3', C.BOLD)}) 両方保存")
    print(f"    {color('0', C.BOLD)}) 保存しない")
    ch = ask("選択", "0")
    if ch in ("1", "3"):
        save_plan(plan, exam_name)
    if ch in ("2", "3"):
        export_text(plan, exam_date, exam_name)

    print()
    success("完了！頑張ってください 🎯")
    print()


if __name__ == "__main__":
    main()