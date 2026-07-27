# test_01

`project_a` 由来のループエンジニアリング（Supervisor ＋ Planning/Execution/Review/Reflection ＋ 検証ループ）を、実プロジェクト上で運用・検証するためのリポジトリ。

## 進捗の見かた

進捗の正本は `state/progress.md`（進捗台帳）。全タスクが1行ずつ、Status付きで集計されている。

- タスクIDは `T-NNN`。採番元はこのファイルで、外部サービスに依存しない。
- Status は `planning` / `in-progress` / `blocked` / `review` / `done` / `dropped` の6語のみ。
- 日付は `YYYY-MM-DD` 固定。

外部ツール（別のAI CLI、スクリプト、人間）はこのファイルだけを読めば現状が分かる。

## 開発フロー

1. 計画時に `state/progress.md` に行を追加し `T-NNN` を採番する。
2. 作業ブランチは `feature/T-NNN-<短い説明>`。
3. レビュー可能になったら push し、`gh pr create` でPRを作る。PR本文に `T-NNN` を書く。
4. マージ後、台帳の Status を `done` にし、完了日とPR番号を記入する。

詳細は `CLAUDE.md` と `governance/workflow.md` を参照。
