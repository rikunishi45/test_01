# test_01 — CLAUDE.md

---

## セッションの基本姿勢 — あなたはSupervisorである

このプロジェクトでは、ユーザーの指示はすべて **Supervisor** として受ける。ユーザーが「Supervisorとして振る舞え」と指定する必要はない。

1. セッション開始時に `governance/supervisor.md` を読み込む。
2. 指示を受けたら複雑度を判定する（`governance/workflow.md` のタスクサイズ基準）。
   - **Small（1〜3ステップ）：** サブエージェントを使わず直接実行してよい。
   - **Medium以上：** 計画を `state/current-task.md` に書き、ステップごとに委任する。
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
**目的：** PR駆動のNotion進捗同期と、`project_a` 由来のループエンジニアリング（Supervisor＋Planning/Execution/Review/Reflection＋検証ループ）を、実プロジェクト上で運用・検証するためのリポジトリ。
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
├── .github/workflows/  # notion-sync.yml（PR→Notion 進捗同期）
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
├── governance/         # Supervisor・ワークフロー・検証・ルーティング
├── memory/             # 長期知識（MEMORY.mdが索引、lessons.mdが教訓ログ）
├── state/              # progress.md（進捗台帳＝集計の正本）、現在のタスク、チェックポイント、TODO
└── README.md
```
（`src/` 等の実装ディレクトリは実装開始時に追加する）

**`.claude/agents/` と `.claude/skills/` の使い分け：**
- **agents** — 別コンテキストで走る実行役。探索ログや大量のファイル内容でメインの文脈を汚さない。ツールとモデルを宣言的に固定できる。
- **skills** — メインコンテキストで動く手順書。会話の文脈をそのまま使う作業（計画立案、文書執筆）向け。本文は呼ばれたときだけロードされる。

---

## 作業プロトコル

1. `state/progress.md`（進捗台帳）と `state/current-task.md` を読み、全体の進捗と進行中の作業を把握する。
2. 計画立案は `/planning`、ドキュメント執筆は `/documentation` でスキルを呼ぶ（Claudeが文脈から自動で読み込むこともある）。
3. `governance/workflow.md` のサイクルに従う：Planning → Execution → Review → Reflection。
4. 重要な意思決定は `memory/decisions.md` にADR形式で書く。
5. `state/` ファイルを最新に保つ — 各セッションの開始時と終了時に更新する。**`state/progress.md` は外部（別のAI CLI・スクリプト・人間）が進捗を読む唯一の窓口なので、Status語彙と日付形式の規約を崩さない。**

---

## 進捗管理

**進捗の正本はリポジトリ内の `state/progress.md`（進捗台帳）。** タスクIDは `T-NNN` で、このファイルが採番元。外部サービスに依存しない。

### 開発フロー

1. 計画時に `state/progress.md` に行を追加し `T-NNN` を採番する（`/planning` スキルの手順に含まれる）。
2. 作業ブランチは `feature/T-NNN-<短い説明>` とする。
3. レビュー可能になったら push し、`gh pr create` でPRを作る。PR本文に `T-NNN` を書いて台帳と対応付ける。
4. マージ後、`state/progress.md` の Status を `done` にし、完了日とPR番号を記入する（`governance/workflow.md` の振り返りフェーズ）。

### 補助：Notion同期（任意）

`.github/workflows/notion-sync.yml` が、PRのタイトル／本文に `TASK-<n>` があれば Notion「開発進捗」DB のStatusを更新する（PR作成→In Review、マージ→Done）。

- **`TASK-<n>` を書かなければスキップされ、ワークフローは正常終了する。** Notionを使わない場合は何も書かなくてよい。
- **注意：`TASK-<n>` を書いたのに対応するNotionページが無いと、ワークフローは exit 1 で失敗する（PRに赤いバツが付く）。** Notion側にページを作ってある場合のみ書くこと。
- 参照しているのはPRのタイトルと本文だけで、ブランチ名は見ていない。

---

## 外部依存

| サービス | 目的 | 認証 |
|---------|------|------|
| Notion API | PR駆動での進捗ステータス更新 | GitHub Secrets: `NOTION_TOKEN`（内部インテグレーション）／`NOTION_DATABASE_ID` |
| GitHub Actions | notion-sync.yml の実行基盤 | リポジトリ標準 |

---

## 既知の制約・落とし穴

- `In Progress` はPRイベントで拾えないため自動化対象外（手動設定）。
- Notion の Ticket ID は Project/Task 共通の連番で採番される（Task IDは連続しないことがある）。
- `NOTION_TOKEN` はGitHub Secretsのみに保持し、コードやログに出さない。
