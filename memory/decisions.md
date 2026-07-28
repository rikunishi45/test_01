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

## ADR-003: main の保護をルールセット2本に分割し、クラスCは管理者bypassでマージする

**Date:** 2026-07-28
**Status:** accepted

### Context（背景）

T-004 Step 6 でルールセットを適用するにあたり、2つの制約が判明した。

**1つ目：コードオーナーは自分のPRを承認できない。** CODEOWNERS の唯一のオーナーは `@rikunishi45` で、PRの作成者も `rikunishi45`。GitHub は自己承認を許可しないため、`require_code_owner_review: true` を素直に適用すると**クラスCのPRが永久にマージ不能**になる。クラスCは `.github/` `.claude/` `governance/` `scripts/` `CLAUDE.md` ＝ 本リポジトリの保守作業のほぼ全域で、T-004 の残ステップ自身もクラスCに当たる。

**2つ目：個人リポジトリでは人間とエージェントが同一のGitHubアイデンティティを共有する。** サーバー側のルールは両者を区別できない。`governance/change-classes.md` が「サーバー側の壁」に期待していた対エージェント防御は、この構成では原理的に成立しない。

なお、当初の懸念だった「`required_approving_review_count: 0` と `require_code_owner_review: true` を同時に設定できるか」は**問題なし**。両者は独立したフィールドで、承認数0でもコードオーナー承認は別枠で強制される。

### Decision（決定）

ルールセットを2本に分け、bypass を片方だけに限定する。

- `main-ci` — 必須ステータスチェック5件、force-push禁止、ブランチ削除禁止。**bypass なし**
- `main-review` — PR必須、コードオーナー承認必須。bypass は Repository admin、モードは `pull_request`（PRのマージ時のみ）

これにより、クラスA/B は承認者0人で auto-merge され、クラスCは管理者が内容を確認したうえで手動マージでき、CIが赤ければ管理者でもマージできず、mainへの直接pushは誰にも許されない。

bypass をルールセット単位でしか設定できないため、1本にまとめると管理者bypassが必須チェックまで飛ばしてしまう。分割はそれを避けるためのもの。

### Consequences（帰結）

- クラスCに対する対エージェント防御は、Step 7（`.claude/settings.json` の `deny`）と Step 8（PreToolUse フック）の**ローカル層のみ**になる。`governance/change-classes.md` の多層表のうち「CODEOWNERS ＋ ルールセット」の行は、対人間には効くが対エージェントには効かない。Step 9 でこの記述を実態に合わせる
- 「別ルールセットの bypass が他方のルールを免除しないこと」は公式ドキュメントに明記がなく、Step 11 で実測する必要がある。この前提が崩れると管理者がCI赤のままマージできてしまう
- クラスDのブロックが有効になったため、今後のPRはクラスをまたいで混ぜられない。`state/` の更新と `.claude/` の変更は別PRにする必要がある

### Alternatives Considered（検討した代替案）

- **GitHub App でエージェントに別アイデンティティを与える** — PR作成者が `xxx[bot]` になり `rikunishi45` がコードオーナーとして承認できるため、bypass 不要でサーバー側の壁が本物になる。当初の設計意図に最も忠実だが、App作成・インストール・秘密鍵の管理が必要でT-004のスコープ外。**後続タスクとして `state/todo.md` に起票**した
- **ルールセット1本＋管理者bypass** — 設定は最も簡単だが、bypassがルールセット単位で効くため必須チェックまで飛ばす。クラスCをCI赤のままマージできてしまうため却下

---

<!-- 新しいADRはこの行の上に、番号をインクリメントして追加する -->
