# Progress Ledger（進捗台帳）

このプロジェクトの全タスクの進捗を1ファイルに集計する。**外部ツール（別のAI CLI、スクリプト、人間）が現状を把握するための単一の窓口。**

- 追記型。完了したタスクも削除せず、Status を `done` にして残す。
- 1タスク＝1行。詳細は `state/current-task.md`（進行中のみ）と各PRを参照する。
- 更新タイミングは `governance/workflow.md` に規定：**計画時に行を追加、フェーズ完了時に Status を更新、振り返り時に完了へ**。

---

## 読み取り規約（機械可読）

パースする側が依存してよい取り決め：

- 日付は `YYYY-MM-DD` 固定。未定は `-`。
- **Status の語彙は以下の6つのみ。** これ以外の値を書かない。

| Status | 意味 |
|---|---|
| `planning` | 計画中。まだ実行に入っていない |
| `in-progress` | 実行中 |
| `blocked` | ブロック中。`Notes` にブロッカーを書く |
| `review` | 成果物完成、検証／サインオフ待ち |
| `done` | 完了（検証PASS＋必要なサインオフ取得済み） |
| `dropped` | 中止。`Notes` に理由を書く |

- `ID` は `T-NNN` の連番（ゼロ埋め3桁）。採番はこのファイルが正本で、外部サービスに依存しない。
- `PR` 列は PR番号（`#12`）。複数ある場合はカンマ区切り。未作成は `-`。

---

## タスク一覧

| ID | タスク | Status | 開始 | 完了 | PR | Notes |
|---|---|---|---|---|---|---|
| T-001 | エージェント/スキル移行とモデル割り当ての宣言化 | review | 2026-07-27 | - | #2 | `skills/*.md` を `.claude/agents/` と `.claude/skills/` へ移行。routing.md を Opus 5/Sonnet 5/Haiku 4.5 構成に整理 |
| T-002 | 進捗台帳（このファイル）の新設とワークフローへの組み込み | review | 2026-07-27 | - | #2 | T-001 と同一ブランチ |
| T-003 | Notion同期の削除と進捗台帳への一本化 | review | 2026-07-27 | - | #2 | `.github/workflows/notion-sync.yml` を削除。GitHub Secrets（`NOTION_TOKEN`／`NOTION_DATABASE_ID`）も削除済み |

---

## 集計

<!-- タスクを更新したらここも更新する -->

| Status | 件数 |
|---|---|
| planning | 0 |
| in-progress | 0 |
| blocked | 0 |
| review | 3 |
| done | 0 |
| dropped | 0 |

**最終更新：** 2026-07-27
