#!/usr/bin/env python3
"""進捗台帳の検証とレンダリング。

正本は state/tasks/T-NNN.md（1タスク1ファイル）。
state/progress.md はこのスクリプトが生成する派生物であり、手で編集しない。
1ファイル1タスクにすることで、並列ブランチが同じ行を奪い合うコンフリクトを避ける。

  ledger.py validate   契約違反があれば理由を出して非0終了
  ledger.py render     state/progress.md を再生成
  ledger.py check      progress.md が最新かどうかだけ確認（生成はしない）
"""

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "state" / "tasks"
LEDGER = ROOT / "state" / "progress.md"

STATUSES = ["planning", "in-progress", "blocked", "review", "done", "dropped"]
REQUIRED = ["id", "title", "status", "started", "completed", "pr"]

RE_ID = re.compile(r"^T-\d{3}$")
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_PR = re.compile(r"^#\d+(, ?#\d+)*$")


def parse_frontmatter(path):
    """`---` で挟まれた `key: value` だけを読む最小パーサ。

    PyYAML はランナーに入っている保証がないので依存を持たない。形式は
    validate() が厳格に検査するため、この単純さで足りる。
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter が `---` で始まっていない")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("frontmatter の終端 `---` がない")
    data = {}
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if ":" not in raw:
            raise ValueError(f"`key: value` 形式でない行: {raw!r}")
        key, _, value = raw.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_tasks():
    tasks, errors = [], []
    for path in sorted(TASKS_DIR.glob("T-*.md")):
        try:
            fm = parse_frontmatter(path)
        except ValueError as e:
            errors.append(f"{path.name}: {e}")
            continue
        tasks.append((path, fm))
    return tasks, errors


def validate():
    if not TASKS_DIR.is_dir():
        print(f"ERROR: {TASKS_DIR} が存在しない")
        return 1

    tasks, errors = load_tasks()
    if not tasks and not errors:
        errors.append("state/tasks/ にタスクファイルが1つもない")

    seen = {}
    for path, fm in tasks:
        name = path.name
        missing = [k for k in REQUIRED if k not in fm]
        if missing:
            errors.append(f"{name}: 必須フィールド不足: {', '.join(missing)}")
            continue

        tid = fm["id"]
        if not RE_ID.match(tid):
            errors.append(f"{name}: id が T-NNN 形式でない: {tid!r}")
        if path.stem != tid:
            errors.append(f"{name}: ファイル名が id と一致しない（id={tid}）")
        if tid in seen:
            errors.append(f"{name}: id が {seen[tid]} と重複している: {tid}")
        seen[tid] = name

        if not fm["title"]:
            errors.append(f"{name}: title が空")
        if fm["status"] not in STATUSES:
            errors.append(
                f"{name}: status が語彙外: {fm['status']!r}"
                f"（許可: {', '.join(STATUSES)}）"
            )
        if not RE_DATE.match(fm["started"]):
            errors.append(f"{name}: started が YYYY-MM-DD でない: {fm['started']!r}")

        completed = fm["completed"]
        if completed != "-" and not RE_DATE.match(completed):
            errors.append(f"{name}: completed が YYYY-MM-DD でも '-' でもない: {completed!r}")
        if fm["status"] == "done" and completed == "-":
            errors.append(f"{name}: status が done なのに completed が未設定")
        if fm["status"] != "done" and completed != "-":
            errors.append(f"{name}: status が done でないのに completed が設定されている")

        pr = fm["pr"]
        if pr != "-" and not RE_PR.match(pr):
            errors.append(f"{name}: pr が '#12' 形式でも '-' でもない: {pr!r}")

    if errors:
        print("進捗台帳の契約違反:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK: {len(tasks)} 件のタスクファイルが契約を満たしている")
    return 0


def render_text():
    tasks, _ = load_tasks()
    rows = sorted((fm for _, fm in tasks), key=lambda f: f["id"])

    out = [
        "# Progress Ledger（進捗台帳）",
        "",
        "<!-- 自動生成: scripts/ledger.py render。手で編集しない。",
        "     正本は state/tasks/T-NNN.md（1タスク1ファイル）。 -->",
        "",
        "このプロジェクトの全タスクの進捗を1ファイルに集計する。"
        "**外部ツール（別のAI CLI、スクリプト、人間）が現状を把握するための単一の窓口。**",
        "",
        "- 各タスクの詳細は `state/tasks/T-NNN.md` にある。",
        "- 更新は各タスクファイルを直し、`python3 scripts/ledger.py render` で再生成する。",
        "",
        "---",
        "",
        "## 読み取り規約（機械可読）",
        "",
        "- 日付は `YYYY-MM-DD` 固定。未定は `-`。",
        f"- Status の語彙は次の6つのみ: {', '.join('`%s`' % s for s in STATUSES)}",
        "- `ID` は `T-NNN` の連番（ゼロ埋め3桁）。採番元は `state/tasks/` で、外部サービスに依存しない。",
        "- `PR` 列は PR番号（`#12`）。複数はカンマ区切り。未作成は `-`。",
        "",
        "---",
        "",
        "## タスク一覧",
        "",
        "| ID | タスク | Status | 開始 | 完了 | PR |",
        "|---|---|---|---|---|---|",
    ]
    for fm in rows:
        out.append(
            f"| {fm['id']} | {fm['title']} | {fm['status']} | "
            f"{fm['started']} | {fm['completed']} | {fm['pr']} |"
        )

    counts = {s: sum(1 for f in rows if f["status"] == s) for s in STATUSES}
    out += ["", "---", "", "## 集計", "", "| Status | 件数 |", "|---|---|"]
    out += [f"| {s} | {counts[s]} |" for s in STATUSES]
    out += ["", f"**合計:** {len(rows)} 件", ""]
    return "\n".join(out)


def render():
    LEDGER.write_text(render_text() + "\n", encoding="utf-8")
    print(f"生成: {LEDGER.relative_to(ROOT)}")
    return 0


def check():
    current = LEDGER.read_text(encoding="utf-8") if LEDGER.exists() else ""
    if current.rstrip("\n") != render_text().rstrip("\n"):
        print("ERROR: state/progress.md が state/tasks/ と一致していない")
        print("  `python3 scripts/ledger.py render` を実行して再生成すること")
        return 1
    print("OK: state/progress.md は最新")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = {"validate": validate, "render": render, "check": check}.get(cmd)
    if fn is None:
        print(__doc__)
        sys.exit(2)
    sys.exit(fn())
