#!/usr/bin/env python3
"""変更クラス（A/B/C/D）を差分のパスから機械的に判定する。

分類をエージェントの自己申告にしないための仕組み。実行者が自分の成果物を
採点しないという governance/verification.md の原則を、マージ可否にも適用する。

  classify.py <変更ファイル...>
  classify.py --from-file <パス一覧のファイル>   # 1行1パス

終了コード: 0 = 自動マージ可（A/B）、1 = 人間必須（C）、2 = 分割要求（D）
未知のパスは C に倒す（fail closed）。
"""

import os
import sys

# 先に一致したものが勝つ。順序に意味がある。
RULES = [
    # C: ガードレール自体と実行可能コード。ここを自動マージ可にすると、
    # エージェントが自分の制約を緩めるPRを無人でマージできてしまう。
    ("C", (".github/", ".claude/", "governance/", "scripts/", "src/", "CLAUDE.md")),
    # B: 検証を足すだけ、または機械的な整形。
    ("B", ("tests/", "package-lock.json", "poetry.lock", "uv.lock", "requirements.txt")),
    # A: 人間もエージェントも読むだけの文書と状態ファイル。
    ("A", ("README.md", "memory/", "state/", "docs/")),
]

LABEL = {
    "A": "A（ドキュメント・状態ファイル）",
    "B": "B（テスト追加・整形・依存のピン止め）",
    "C": "C（ガードレール・実行可能コード）",
    "D": "D（クラスCと他クラスの混在）",
}


def classify_file(path):
    for cls, prefixes in RULES:
        if any(path == p or path.startswith(p) for p in prefixes):
            return cls
    return "C"  # 未知のパスは安全側


def classify(paths):
    per_file = {p: classify_file(p) for p in paths}
    classes = set(per_file.values())
    if "C" in classes and len(classes) > 1:
        return "D", per_file
    if "C" in classes:
        return "C", per_file
    if "B" in classes:
        return "B", per_file
    return "A", per_file


def main(paths):
    if not paths:
        print("変更ファイルがない。判定不能なため C として扱う。")
        result, per_file = "C", {}
    else:
        result, per_file = classify(paths)

    print(f"判定: クラス {result} — {LABEL[result]}\n")
    print("ファイル別:")
    for path in sorted(per_file):
        print(f"  [{per_file[path]}] {path}")
    print()

    if result in ("A", "B"):
        print("→ CIが全green であれば自動マージ可。")
        code = 0
    elif result == "C":
        print("→ 人間のレビューとマージが必須。自動マージは行わない。")
        code = 1
    else:
        print("→ ブロック。クラスCの変更と他クラスの変更を別々のPRに分割すること。")
        print("  混在したままだと、レビューが必要な変更が低リスクな変更に紛れて通る。")
        code = 2

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## 変更クラス: {result}\n\n{LABEL[result]}\n\n")
            for path in sorted(per_file):
                f.write(f"- `{per_file[path]}` — `{path}`\n")

    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"class={result}\n")
            f.write(f"automergeable={'true' if code == 0 else 'false'}\n")

    return code


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--from-file"]:
        # シェル配列を経由しないための入口。空白を含むパスでも壊れない。
        with open(args[1], encoding="utf-8") as fh:
            args = fh.read().splitlines()
    sys.exit(main([p for p in args if p.strip()]))
