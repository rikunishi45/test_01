# Progress Ledger（進捗台帳）

<!-- 自動生成: scripts/ledger.py render。手で編集しない。
     正本は state/tasks/T-NNN.md（1タスク1ファイル）。 -->

このプロジェクトの全タスクの進捗を1ファイルに集計する。**外部ツール（別のAI CLI、スクリプト、人間）が現状を把握するための単一の窓口。**

- 各タスクの詳細は `state/tasks/T-NNN.md` にある。
- 更新は各タスクファイルを直し、`python3 scripts/ledger.py render` で再生成する。

---

## 読み取り規約（機械可読）

- 日付は `YYYY-MM-DD` 固定。未定は `-`。
- Status の語彙は次の6つのみ: `planning`, `in-progress`, `blocked`, `review`, `done`, `dropped`
- `ID` は `T-NNN` の連番（ゼロ埋め3桁）。採番元は `state/tasks/` で、外部サービスに依存しない。
- `PR` 列は PR番号（`#12`）。複数はカンマ区切り。未作成は `-`。

---

## タスク一覧

| ID | タスク | Status | 開始 | 完了 | PR |
|---|---|---|---|---|---|
| T-001 | エージェント/スキル移行とモデル割り当ての宣言化 | done | 2026-07-27 | 2026-07-27 | #2 |
| T-002 | 進捗台帳の新設とワークフローへの組み込み | done | 2026-07-27 | 2026-07-27 | #2 |
| T-003 | Notion同期の削除と進捗台帳への一本化 | done | 2026-07-27 | 2026-07-27 | #2 |
| T-004 | 自律開発運用の整備（クラス分類・CI・リポジトリガード・エージェント権限） | in-progress | 2026-07-27 | - | #3 |
| T-005 | GitHub App による台帳自動生成の復旧（Actions内限定） | planning | 2026-07-30 | - | - |

---

## 集計

| Status | 件数 |
|---|---|
| planning | 1 |
| in-progress | 1 |
| blocked | 0 |
| review | 0 |
| done | 3 |
| dropped | 0 |

**合計:** 5 件

