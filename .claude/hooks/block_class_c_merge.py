#!/usr/bin/env python3
"""PreToolUse フック: `gh pr merge` によるクラスC/D PRの手動マージを遮断する。

なぜ必要か（T-004 Step 8）:
  リポジトリのオーナーとエージェントが同一のGitHubアカウントを共有しているため、
  サーバー側のルールセットだけではエージェントによるクラスCの自動/手動マージを
  止められない。`.claude/settings.json` の `deny` は静的なコマンド文字列にしか
  反応しないため、「対象PRの変更クラス」という動的な条件では判定できない。
  このフックがその判定を担う。

判定ロジックは `scripts/classify.py` を再利用する（判定を二重に持たない）。

契約（Claude Code の PreToolUse フック）:
  - stdin から `{"tool_name": ..., "tool_input": {"command": ...}, "cwd": ...}` を読む。
  - ブロックする場合は stdout に
      {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny"},
       "systemMessage": "<理由>"}
    を出力し、exit 0 する（hookify 等の公式プラグインと同じ実装パターン）。
  - 許可する場合は何も出力せず exit 0 する（通常の権限フローに委ねる）。
  - 判定不能な場合は fail closed（ブロックする）。
"""

import json
import os
import shlex
import subprocess
import sys
import tempfile

GH_TIMEOUT_SEC = 20
CLASSIFY_TIMEOUT_SEC = 15

SEPARATOR_RE_SPLIT_TOKENS = {"&&", "||", ";", "|"}


def deny(reason):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    # Claude に返る理由。これが無いとブロックの根拠が伝わらず、
                    # 別の書き方で再試行されうる。systemMessage は人間向けの表示。
                    "permissionDecisionReason": reason,
                },
                "systemMessage": reason,
            }
        )
    )
    sys.exit(0)


def allow():
    # 何も出力しない = このフックは判断を持たない。通常の権限フロー（allow/ask/deny）に委ねる。
    sys.exit(0)


def split_subcommands(command):
    """`&&` `||` `;` `|` で連結されたコマンドをトークン列のリストに分割する。

    シェルの完全な文法は再実装しない。引用符の対応が取れない等でトークン化に
    失敗した場合は None を返し、呼び出し側で fail closed する。
    """
    padded = command
    for sep in ("&&", "||", ";", "|"):
        padded = padded.replace(sep, f" {sep} ")
    try:
        tokens = shlex.split(padded)
    except ValueError:
        return None

    subcommands = []
    current = []
    for tok in tokens:
        if tok in SEPARATOR_RE_SPLIT_TOKENS:
            if current:
                subcommands.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        subcommands.append(current)
    return subcommands


def match_gh_pr_merge(tokens):
    """トークン列が `gh pr merge` 呼び出しなら、`merge` 以降の残り引数を返す。"""
    if not tokens or tokens[0] != "gh":
        return None
    i = 1
    # gh のグローバルオプション（--repo/-R とその値）をスキップする。
    while i < len(tokens):
        t = tokens[i]
        if t in ("--repo", "-R", "--hostname"):
            i += 2
            continue
        if t.startswith("--repo=") or (t.startswith("-R") and len(t) > 2):
            i += 1
            continue
        break
    if i + 1 < len(tokens) and tokens[i] == "pr" and tokens[i + 1] == "merge":
        return tokens[i + 2:]
    return None


def extract_ref_and_repo(merge_args):
    """`gh pr merge` の残り引数から PR参照（番号/URL/ブランチ）と --repo を取り出す。"""
    ref = None
    repo = None
    i = 0
    while i < len(merge_args):
        arg = merge_args[i]
        if arg in ("--repo", "-R"):
            if i + 1 < len(merge_args):
                repo = merge_args[i + 1]
                i += 2
                continue
            i += 1
            continue
        if arg.startswith("--repo="):
            repo = arg.split("=", 1)[1]
            i += 1
            continue
        if arg.startswith("-R") and len(arg) > 2:
            repo = arg[2:]
            i += 1
            continue
        if arg.startswith("-"):
            i += 1
            continue
        if ref is None:
            ref = arg
        i += 1
    return ref, repo


def resolve_project_dir(input_data):
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    cwd = input_data.get("cwd")
    if cwd and os.path.isdir(cwd):
        return cwd
    # フォールバック: このスクリプトの2階層上（.claude/hooks/ -> リポジトリルート）
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def gh_pr_view(ref, repo, cwd):
    cmd = ["gh", "pr", "view"]
    if ref:
        cmd.append(ref)
    if repo:
        cmd.extend(["--repo", repo])
    cmd.extend(["--json", "number,files"])
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=GH_TIMEOUT_SEC, cwd=cwd
    )


def main():
    try:
        raw = sys.stdin.read()
        input_data = json.loads(raw) if raw.strip() else {}
    except Exception:
        deny("フック入力(stdin)を解析できなかったため、安全側でブロックしました。")
        return

    if input_data.get("tool_name") != "Bash":
        allow()
        return

    command = (input_data.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str) or not command.strip():
        allow()
        return

    subcommands = split_subcommands(command)
    if subcommands is None:
        deny(
            "コマンドの引用符が対応しておらず解析できなかったため、"
            "gh pr merge かどうか判定できず安全側でブロックしました。"
        )
        return

    merge_args = None
    for tokens in subcommands:
        m = match_gh_pr_merge(tokens)
        if m is not None:
            merge_args = m
            break

    if merge_args is None:
        allow()
        return

    ref, repo = extract_ref_and_repo(merge_args)
    project_dir = resolve_project_dir(input_data)
    cwd = input_data.get("cwd") or project_dir

    try:
        view = gh_pr_view(ref, repo, cwd)
    except subprocess.TimeoutExpired:
        deny(
            "`gh pr view` がタイムアウトしました（ネットワーク断の可能性）。"
            "対象PRの変更クラスを判定できないため gh pr merge を安全側でブロックしました。"
        )
        return
    except Exception as e:
        deny(f"`gh pr view` の実行に失敗したため安全側でブロックしました: {e}")
        return

    if view.returncode != 0:
        deny(
            "対象PRの情報を取得できなかったため（`gh pr view` が失敗）、"
            f"gh pr merge を安全側でブロックしました。stderr: {view.stderr.strip()[:300]}"
        )
        return

    try:
        pr_data = json.loads(view.stdout)
        pr_number = pr_data["number"]
        paths = [f["path"] for f in pr_data.get("files", [])]
    except Exception as e:
        deny(f"`gh pr view` の出力を解析できなかったため安全側でブロックしました: {e}")
        return

    classify_path = os.path.join(project_dir, "scripts", "classify.py")
    if not os.path.isfile(classify_path):
        deny(
            "変更クラス判定スクリプト(scripts/classify.py)が見つからなかったため、"
            "安全側でブロックしました。"
        )
        return

    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix="pr-paths-", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for p in paths:
                f.write(p + "\n")

        proc = subprocess.run(
            [sys.executable, classify_path, "--from-file", tmp_path],
            capture_output=True,
            text=True,
            timeout=CLASSIFY_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        deny("変更クラス判定がタイムアウトしたため安全側でブロックしました。")
        return
    except Exception as e:
        deny(f"変更クラス判定の実行に失敗したため安全側でブロックしました: {e}")
        return
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if proc.returncode == 0:
        # クラス A/B。エージェントによる gh pr merge を妨げない。
        allow()
        return
    elif proc.returncode == 1:
        deny(
            f"PR #{pr_number} はクラスC（ガードレール・実行可能コード）です。"
            "governance/change-classes.md により、人間のレビューとマージ承認が必須です。"
            "gh pr merge によるエージェントでの手動マージをブロックしました。"
        )
        return
    elif proc.returncode == 2:
        deny(
            f"PR #{pr_number} はクラスD（クラスCと他クラスの混在）です。"
            "分割するまでマージできません。gh pr merge をブロックしました。"
        )
        return
    else:
        deny(
            f"変更クラス判定が想定外の終了コード({proc.returncode})を返したため、"
            "安全側でブロックしました。"
        )
        return


if __name__ == "__main__":
    main()
