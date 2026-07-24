# test_01

PR駆動でNotion「開発進捗 (Dev Progress)」DBのステータスを自動同期する検証用リポジトリ。

## 進捗同期のルール

PRのタイトルまたは本文に `Closes TASK-<n>`（例: `Closes TASK-2`）を書くと、`.github/workflows/notion-sync.yml` が動作する:

- PR作成 / 再オープン → Notionの対象タスクを **In Review** へ
- PRマージ → **Done** へ

`TASK-<n>` はNotion側の Ticket ID（自動採番）に対応する。

## セットアップ済みSecrets

- `NOTION_TOKEN` — Notion内部インテグレーションのトークン
- `NOTION_DATABASE_ID` — 対象DBのID
