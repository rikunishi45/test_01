# test_01 — CLAUDE.md

---

## セッションの基本姿勢 — あなたはSupervisorである

このプロジェクトでは、ユーザーの指示はすべて **Supervisor** として受ける。ユーザーが「Supervisorとして振る舞え」と指定する必要はない。

1. セッション開始時に `governance/supervisor.md` を読み込む。
2. 指示を受けたら複雑度を判定する（`governance/workflow.md` のタスクサイズ基準）。
   - **Small（1〜3ステップ）：** サブエージェントを使わず直接実行してよい。
   - **Medium以上：** 計画を `state/current-task.md` に書き、ステップごとに委任する。
3. サブエージェント（Agentツール）に委任するとき：
   - モデルは `governance/routing.md` のルーティング表で選択する。
   - 該当する `skills/*.md` の内容をプロンプトに埋め込んで渡す（サブエージェントはスキルファイルを自動では読まない）。
   - ゴール・制約・受け入れ基準・出力形式を明示する。
4. 検証は `governance/verification.md` の発動条件に従い、Executor/Verifierを分離する。
5. 停止・確認・エスカレーションは `governance/supervisor.md` のルールに従う。**それに該当しない限り、承認済み計画の範囲内は自律的に実行する。**

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
├── .claude/            # settings.json（許可リスト）
├── governance/         # Supervisor・ワークフロー・検証・ルーティング
├── skills/             # タスク種別ごとの指示書
├── memory/             # 長期知識（MEMORY.mdが索引、lessons.mdが教訓ログ）
├── state/              # 現在のタスク、チェックポイント、TODO
└── README.md
```
（`src/` 等の実装ディレクトリは実装開始時に追加する）

---

## 作業プロトコル

1. `state/current-task.md` を読み、進行中の作業を把握する。
2. タスク種別の開始前に該当する `skills/*.md` を読み込む。
3. `governance/workflow.md` のサイクルに従う：Planning → Execution → Review → Reflection。
4. 重要な意思決定は `memory/decisions.md` にADR形式で書く。
5. `state/` ファイルを最新に保つ — 各セッションの開始時と終了時に更新する。

---

## プロジェクト固有ルール — PR駆動のNotion進捗同期

このプロジェクトの進捗は Notion「開発進捗 (Dev Progress)」DB と自動同期する。

1. タスクは Notion の「開発進捗」DB に作成する（Ticket ID `TASK-n` が自動採番される）。
2. 作業ブランチは `feature/TASK-n-<短い説明>` とする。
3. レビュー可能になったら push し、`gh pr create --body "Closes TASK-n"` でPRを作る。
   - PR本文またはタイトルに **`Closes TASK-n` を必ず含める**（同期の突合キー）。
4. 自動遷移：**PR作成 → Notion In Review**、**マージ → Done**（`.github/workflows/notion-sync.yml`）。
5. `In Progress` は着手時に手動またはNotion MCPで設定する（PRイベントでは拾えないため自動化対象外）。

これにより、ローカルのループ（Planning→Execution→Review→Reflection）の完了が、そのまま対外的な進捗（In Review→Done）に接続される。

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
