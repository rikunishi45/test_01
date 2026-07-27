---
name: decisions
description: このプロジェクトのアーキテクチャ決定記録
metadata:
  type: project
---

# アーキテクチャ決定記録

---

## ADR-001: [タイトル]

**Date:** YYYY-MM-DD
**Status:** proposed | accepted | deprecated | superseded by ADR-NNN

### Context（背景）
[この決定に至った状況]

### Decision（決定）
[何を決めたか]

### Consequences（帰結）
[何が容易に・困難に・変わるか]

### Alternatives Considered（検討した代替案）
[選ばなかった選択肢とその理由]

---

## ADR-002: 自動マージの前提としてリポジトリを public 化する

**Date:** 2026-07-27
**Status:** accepted

### Context（背景）

人間の関与を計画のサインオフと異常時の介入に限定し、低リスク変更のマージまでをAIが自律実行する運用（T-004）を目指した。

調査した実運用事例（Stripe、Razorpay、Anthropic社内ほか）はいずれも、自動マージの根拠を**必須ステータスチェックが緑であること**に置いている。エージェント側の権限設定は分類器ベースであり、Anthropic自身が auto mode について「実際に行き過ぎた操作の17%を見逃す」と公表している。したがってサーバー側の機械的な壁が不可欠。

ところが `test_01` は private かつ GitHub Free で、GitHub API が明示的に拒否した：

```
GET /repos/rikunishi45/test_01/rulesets
→ 403 "Upgrade to GitHub Pro or make this repository public to enable this feature."
```

ブランチ保護・ルールセット・必須ステータスチェックが使えず、CIを書いても「緑でなければマージ不可」を強制できない。飾りのチェックマークにしかならない。

### Decision（決定）

リポジトリを public にする。

実行前に全履歴（11コミット・25ファイル）を走査し、トークン形式・秘密鍵・UUID/DATABASE_ID のいずれも検出されないことを確認した。削除済みの `notion-sync.yml` も `${{ secrets.* }}` 参照のみで実値を含まない。

### Consequences（帰結）

- ブランチ保護、ルールセット、必須ステータスチェック、CODEOWNERS、マージキューが無料で利用可能になり、T-004 の Step 6 が実施可能になった
- git履歴を含む全内容が公開される。**public 化は実質的に不可逆**（一度公開された内容は取り消せない）
- 今後このリポジトリに秘密情報・個人情報・非公開の実装を置けない。置く必要が生じた時点で別リポジトリに分離する
- Claude Code の auto mode は、リポジトリが public だと PR本文・issue本文・コミットメッセージへの内部パスや機微情報の混入をより厳しく判定する。安全側に働く

### Alternatives Considered（検討した代替案）

- **GitHub Pro に課金（月$4）** — private のままブランチ保護が使える。コストが発生する点と、マージキューが対象外である可能性（未確認）を理由に選ばなかった
- **Free + private のまま進める** — サーバー側の壁を諦め、Claude Code の `deny` ルールとフックのみで運用する案。`deny` は全権限モードで有効な唯一の壁だが、それ1層だけになり、調査した全事例の構成と整合しないため却下

---

<!-- 新しいADRはこの行の上に、番号をインクリメントして追加する -->
