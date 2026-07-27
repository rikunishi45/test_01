# test_01 — CLAUDE.md

---

## セッションの基本姿勢 — あなたはSupervisorである

このプロジェクトでは、ユーザーの指示はすべて **Supervisor** として受ける。ユーザーが「Supervisorとして振る舞え」と指定する必要はない。

1. セッション開始時に `governance/supervisor.md` を読み込む。
2. 指示を受けたら複雑度を判定する（`governance/workflow.md` のタスクサイズ基準）。
   - **Small（1〜3ステップ）：** サブエージェントを使わず直接実行してよい。
   - **Medium以上：** 計画を `state/tasks/T-NNN.md` に書き、ステップごとに委任する。
3. サブエージェント（Agentツール）に委任するとき：
   - `subagent_type` で担当エージェントを選ぶ（`coder` / `researcher` / `verifier` / `doc-verifier`）。**モデルは各エージェントの frontmatter で決まるので、`model` パラメータは指定しない。**
   - エージェントの手順書は `.claude/agents/*.md` にあり、システムプロンプトとして自動で読み込まれる。プロンプトへの手動コピーは不要。
   - 渡すのは、ゴール・制約・受け入れ基準・出力形式・対象ファイルパス。
4. 検証は `governance/verification.md` の発動条件に従い、Executor/Verifierを分離する。
5. 停止・確認・エスカレーションは `governance/supervisor.md` のルールに従う。**それに該当しない限り、承認済み計画の範囲内は自律的に実行する。**

### モデル方針（詳細は `governance/routing.md`）

| 役割 | モデル |
|------|--------|
| Supervisor（このセッション） | Opus 5（`/model opus`） |
| 実装・リサーチ・検証・ドキュメント | Sonnet 5 |
| 単純検索・定型ルーブリック採点 | Haiku 4.5 |
| Fable 5 | 従量課金のため既定では使わない |

---

## プロジェクト概要

**名前：** test_01
**目的：** `project_a` 由来のループエンジニアリング（Supervisor＋Planning/Execution/Review/Reflection＋検証ループ）を、実プロジェクト上で運用・検証するためのリポジトリ。
**Status:** active
**作成日：** 2026-07-24

---

## 技術スタック

実コードは未着手。実装言語・フレームワークを決めた時点でここに記入する。

| レイヤー | 技術 | バージョン |
|-------|-----------|---------|
| 言語 | 未定 | — |
| ランタイム | 未定 | — |
| テストランナー | 未定 | — |
| CI | GitHub Actions | — |

---

## ディレクトリ構成

```
test_01/
├── .claude/
│   ├── settings.json   # 許可リスト
│   ├── agents/         # サブエージェント定義（独立コンテキスト＋モデル固定＋ツール制限）
│   │   ├── coder.md        # sonnet — 実装
│   │   ├── researcher.md   # sonnet — リサーチ
│   │   ├── verifier.md     # sonnet — コード/計画/リサーチの検証
│   │   └── doc-verifier.md # haiku  — ドキュメントの定型採点
│   └── skills/         # メインコンテキストで動く手順書（必要時のみロード）
│       ├── planning/SKILL.md      # opus   — 計画立案
│       └── documentation/SKILL.md # sonnet — ドキュメント執筆
├── .github/
│   ├── workflows/      # ci.yml（必須チェック）、classify.yml（変更クラス判定）、ledger.yml（台帳生成）
│   └── CODEOWNERS      # クラスCのパス＝人間のレビュー必須
├── governance/         # Supervisor・ワークフロー・検証・ルーティング・変更クラス
├── memory/             # 長期知識（MEMORY.mdが索引、lessons.mdが教訓ログ）
├── scripts/            # ledger.py（台帳の検証と生成）、classify.py、validate_defs.py
├── state/
│   ├── tasks/          # T-NNN.md — 1タスク1ファイル。**進捗の正本**
│   ├── progress.md     # 集計表。ledger.py が生成する派生物。手で編集しない
│   ├── checkpoint.md
│   └── todo.md
└── README.md
```
（`src/` 等の実装ディレクトリは実装開始時に追加する）

**`.claude/agents/` と `.claude/skills/` の使い分け：**
- **agents** — 別コンテキストで走る実行役。探索ログや大量のファイル内容でメインの文脈を汚さない。ツールとモデルを宣言的に固定できる。
- **skills** — メインコンテキストで動く手順書。会話の文脈をそのまま使う作業（計画立案、文書執筆）向け。本文は呼ばれたときだけロードされる。

---

## 作業プロトコル

1. `state/progress.md`（進捗台帳＝全体の集計）を読み、次に `state/tasks/` の該当ファイルで進行中の作業の詳細を把握する。
2. 計画立案は `/planning`、ドキュメント執筆は `/documentation` でスキルを呼ぶ（Claudeが文脈から自動で読み込むこともある）。
3. `governance/workflow.md` のサイクルに従う：Planning → Execution → Review → Reflection。
4. 重要な意思決定は `memory/decisions.md` にADR形式で書く。
5. `state/` ファイルを最新に保つ — 各セッションの開始時と終了時に更新する。**`state/progress.md` は外部（別のAI CLI・スクリプト・人間）が進捗を読む唯一の窓口なので、Status語彙と日付形式の規約を崩さない。**

---

## 進捗管理

**進捗の正本は `state/tasks/T-NNN.md`（1タスク1ファイル）。** タスクIDはこのディレクトリが採番元で、外部サービスに依存しない。

`state/progress.md` は `scripts/ledger.py` が全タスクファイルから生成する**集計表**。外部（別のAI CLI・スクリプト・人間）が現状を読む窓口はこちらだが、**書き込み先ではない。** 手で編集すると次の生成で上書きされる。

### 開発フロー

1. 計画時に `state/tasks/T-NNN.md` を新規作成する（`/planning` スキルの手順に含まれる）。既存タスクのファイルは触らない。
2. 作業ブランチは `feature/T-NNN-<短い説明>` とする。
3. レビュー可能になったら push し、`gh pr create` でPRを作る。PR本文に `T-NNN` を書く。
4. PRの変更クラスを `.github/workflows/classify.yml` が判定する。クラスA/B は必須チェックが全green になり次第、自動マージされる。**クラスC は人間のレビュー承認を待つ。** クラスD は分割するまでブロックされる。
5. マージ後、`ledger.yml` が `state/progress.md` を再生成する。

### 並列開発

独立したタスクは並行して進めてよい。片方がレビュー待ちでも、もう片方の実装を止めない。

- タスクファイルが別なので、ブランチ間でコンフリクトしない（これが1タスク1ファイルにしている理由）。
- **依存のあるタスクを並列化しない。** 後続が先行の変更を含まないまま実装され、マージ後に破綻する。依存がある場合は先行ブランチから生やす（stacked PR）か、順番に実行する。
- 依存の有無は計画時に判定する（`/planning` の「依存関係を特定する」）。

---

## 外部依存

| サービス | 目的 | 認証 |
|---------|------|------|
| GitHub | リモートリポジトリ、PR | `gh` CLI |

---

## 既知の制約・落とし穴

- 進捗の集計は手動更新に依存する。更新漏れを防ぐため、更新タイミングを `governance/workflow.md` の各フェーズ手順に埋め込んである。
