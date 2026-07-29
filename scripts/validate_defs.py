#!/usr/bin/env python3
"""エージェント／スキル定義と、ドキュメント間リンクの検証。

frontmatter が壊れるとモデルルーティングが例外を出さずに黙って崩れる
（`model` を落とすとメインの会話モデルを継承してしまう）ため、CIで止める。
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / ".claude" / "agents"
SKILLS_DIR = ROOT / ".claude" / "skills"

VALID_MODELS = {"opus", "sonnet", "haiku", "fable", "inherit"}
RE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# governance/routing.md の方針。Supervisor 以外を Opus に上げるのは要レビュー。
DISALLOWED_FOR_SUBAGENTS = {"opus", "fable"}


def parse_frontmatter(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("frontmatter が `---` で始まっていない")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("frontmatter の終端 `---` がない")
    data = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            raise ValueError(f"`key: value` 形式でない行: {raw!r}")
        key, _, value = raw.partition(":")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def check_definitions():
    errors = []

    for path in sorted(AGENTS_DIR.glob("*.md")):
        try:
            fm = parse_frontmatter(path)
        except ValueError as e:
            errors.append(f"{path.name}: {e}")
            continue
        for field in ("name", "description", "model"):
            if not fm.get(field):
                errors.append(f"{path.name}: 必須フィールド `{field}` がない")
        name = fm.get("name", "")
        if name and not RE_NAME.match(name):
            errors.append(f"{path.name}: name が kebab-case でない: {name!r}")
        if name and path.stem != name:
            errors.append(f"{path.name}: ファイル名が name と一致しない（name={name}）")
        model = fm.get("model", "")
        if model and model not in VALID_MODELS:
            errors.append(
                f"{path.name}: model が不正: {model!r}"
                f"（許可: {', '.join(sorted(VALID_MODELS))}）"
            )
        if model in DISALLOWED_FOR_SUBAGENTS:
            errors.append(
                f"{path.name}: サブエージェントに {model!r} を割り当てている。"
                " governance/routing.md では実行役は sonnet／単純作業は haiku。"
                " 意図的なら routing.md に例外として明記すること"
            )

    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        try:
            fm = parse_frontmatter(path)
        except ValueError as e:
            errors.append(f"{path.parent.name}/SKILL.md: {e}")
            continue
        for field in ("name", "description"):
            if not fm.get(field):
                errors.append(f"{path.parent.name}/SKILL.md: 必須フィールド `{field}` がない")
        name = fm.get("name", "")
        if name and path.parent.name != name:
            errors.append(
                f"{path.parent.name}/SKILL.md: ディレクトリ名が name と一致しない（name={name}）"
            )
        model = fm.get("model")
        if model and model not in VALID_MODELS:
            errors.append(f"{path.parent.name}/SKILL.md: model が不正: {model!r}")

    return errors


# インラインコード内のパス（`state/tasks/` など）を拾う。存在しない参照は
# エージェントが読めない手順書を意味するので落とす。
RE_INLINE_PATH = re.compile(r"`([A-Za-z0-9_.\-/]+\.(?:md|py|json|yml|yaml))`")
RE_PLACEHOLDER = re.compile(r"NNN|[*{}<>]")


def gitignored(targets):
    """gitignore 対象のパスの集合を返す。判定できなければ空集合を返す。

    gitignore されたファイルは意図的にリポジトリに存在しないため、参照が
    解決できないのは正常。これを除外しないと、ローカルには在るがCIの
    チェックアウトには無いファイル（`.claude/settings.local.json` など）への
    言及が、ローカルで通ってCIでだけ落ちる（実測: PR #11）。
    """
    if not targets:
        return set()
    try:
        r = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            input="\n".join(targets),
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=10,
        )
    except Exception:
        # git が無い・タイムアウト等。除外なしで従来どおり検証する。
        return set()
    return {line.strip() for line in r.stdout.splitlines() if line.strip()}


def check_references():
    unresolved = []
    for path in sorted(ROOT.rglob("*.md")):
        if ".git/" in str(path) or "/worktrees/" in str(path):
            continue
        rel = path.relative_to(ROOT)
        for target in set(RE_INLINE_PATH.findall(path.read_text(encoding="utf-8"))):
            # ディレクトリを含まない裸のファイル名（`workflow.md` など）は文中の
            # 呼称であってパス参照ではないので対象外。プレースホルダも同様。
            if "/" not in target:
                continue
            if target.startswith(("http", "~")) or RE_PLACEHOLDER.search(target):
                continue
            # リポジトリルート相対、または参照元ファイルからの相対で解決できればよい
            if (ROOT / target).exists() or (path.parent / target).exists():
                continue
            unresolved.append((rel, target))

    # 解決できなかったものだけを gitignore 判定にかける（git 呼び出しは1回）
    ignored = gitignored([target for _, target in unresolved])
    return [
        f"{rel}: 存在しないファイルを参照している: `{target}`"
        for rel, target in unresolved
        if target not in ignored
    ]


if __name__ == "__main__":
    all_errors = check_definitions() + check_references()
    if all_errors:
        print("定義／参照の検証エラー:")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    print("OK: エージェント／スキル定義とドキュメント参照は整合している")
