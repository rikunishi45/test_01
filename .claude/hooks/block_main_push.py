#!/usr/bin/env python3
"""PreToolUse フック: main ブランチへの直接 `git push` を遮断する（Step 7 の穴埋め）。

`.claude/settings.json` の `deny` は glob（文字列パターン）でしか判定できないため、
以下のような経路を取りこぼす:
  - `git push` （引数なし。upstream 経由で main を直接押す）
  - `git push origin` （リフスペック省略。カレントブランチが main の場合）
  - `git push origin <ローカルブランチ名>:main` （ローカルのブランチ名がmainでない）

このフックは実際の push 先ブランチ名を（カレントブランチ or リフスペックから）
解決し、main を指していれば理由を伴ってブロックする。

fail closed の範囲: 「本当に判定できない」場合のみブロックする。
  - コマンドの引用符が壊れていてトークン化できない
  - `--all` / `--mirror` 等、mainを含む可能性を否定できない一括push
  - 明示的な参照がなく、かつカレントブランチ名を取得できない
それ以外の、main以外へのpushだと明確に判定できる場合はブロックしない
（判定できるケースまで一律ブロックすると通常のfeatureブランチ運用が壊れるため）。

出力契約は block_class_c_merge.py と同じ（hookSpecificOutput.permissionDecision）。
"""

import json
import os
import shlex
import subprocess
import sys

GIT_TIMEOUT_SEC = 10
MAIN_BRANCH = "main"


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
    sys.exit(0)


def split_subcommands(command):
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
        if tok in ("&&", "||", ";", "|"):
            if current:
                subcommands.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        subcommands.append(current)
    return subcommands


def match_git_push(tokens):
    """トークン列が `git push` 呼び出しなら、`push` 以降の残り引数を返す。"""
    if not tokens or tokens[0] != "git":
        return None
    i = 1
    # `git -C <path>` / `git -c key=val` のグローバルオプションをスキップする。
    while i < len(tokens):
        t = tokens[i]
        if t in ("-C", "-c"):
            i += 2
            continue
        if (t.startswith("-C") or t.startswith("-c")) and len(t) > 2:
            i += 1
            continue
        break
    if i < len(tokens) and tokens[i] == "push":
        return tokens[i + 1:]
    return None


def strip_refs_heads(name):
    prefix = "refs/heads/"
    if name.startswith(prefix):
        return name[len(prefix):]
    return name


def get_current_branch(cwd):
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SEC,
            cwd=cwd,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    branch = r.stdout.strip()
    if not branch or branch == "HEAD":
        # detached HEAD。ブランチ名では判断できない。
        return None
    return branch


_VALUE_TAKING_FLAGS = {"--repo", "--receive-pack", "--push-option", "-o"}


def evaluate_push(push_args, cwd):
    """push 先が main かどうかを判定する。

    戻り値: (should_block: bool, reason: str | None)
    """
    if any(a in ("--all", "--mirror", "--branches") for a in push_args):
        return True, (
            "`--all`/`--mirror`/`--branches` は main を含む可能性があるブランチ一括push "
            "のため安全側でブロックしました。"
        )

    positional = []
    i = 0
    while i < len(push_args):
        arg = push_args[i]
        if arg in _VALUE_TAKING_FLAGS:
            i += 2
            continue
        if arg.startswith("-"):
            i += 1
            continue
        positional.append(arg)
        i += 1

    if not positional:
        # `git push` 単体。upstream に現在のブランチを push する。
        branch = get_current_branch(cwd)
        if branch is None:
            return True, (
                "リフスペックが省略された `git push` で、現在のブランチ名を取得できな"
                "かったため、main への push でないことを確認できず安全側でブロックしました。"
            )
        if branch == MAIN_BRANCH:
            return True, f"現在のブランチ `{MAIN_BRANCH}` への直接pushをブロックしました。"
        return False, None

    remote = positional[0]
    refspecs = positional[1:]

    if not refspecs:
        # `git push <remote>`。リフスペック省略時は現在のブランチと同名のリモート
        # ブランチに push される（push.default=simple/current の一般的な既定値）。
        branch = get_current_branch(cwd)
        if branch is None:
            return True, (
                f"`git push {remote}` でリフスペックが省略されており、現在のブランチ名を"
                "取得できなかったため安全側でブロックしました。"
            )
        if branch == MAIN_BRANCH:
            return True, (
                f"現在のブランチ `{MAIN_BRANCH}` を `{remote}` へ直接pushする操作を"
                "ブロックしました。"
            )
        return False, None

    for refspec in refspecs:
        spec = refspec.lstrip("+")  # 先頭の `+` は force指定
        dest = spec.split(":", 1)[1] if ":" in spec else spec
        dest = strip_refs_heads(dest)
        if dest == MAIN_BRANCH:
            return True, (
                f"`{remote}` の `{MAIN_BRANCH}` ブランチへの直接push（refspec=`{refspec}`）"
                "をブロックしました。"
            )

    return False, None


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

    cwd = input_data.get("cwd") or os.getcwd()

    subcommands = split_subcommands(command)
    if subcommands is None:
        deny(
            "コマンドの引用符が対応しておらず解析できなかったため、"
            "main への直接pushでないことを確認できず安全側でブロックしました。"
        )
        return

    for tokens in subcommands:
        push_args = match_git_push(tokens)
        if push_args is None:
            continue
        should_block, reason = evaluate_push(push_args, cwd)
        if should_block:
            deny(reason)
            return

    allow()


if __name__ == "__main__":
    main()
