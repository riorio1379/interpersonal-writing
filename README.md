# interpersonal-writing（対人文章）

日本語 | [English](README.en.md)

人に送る文面を、相手との関係と用件に合わせて書くための AI エージェント用スキルです。Claude Code・Codex・Cursor など、SKILL.md を読めるエージェントで使えます。

- 対象：メール、LINE や Slack などのチャット、問い合わせフォーム、フリマの取引メッセージ
- 相手：家族・友人・職場・大学の教員・社外の相手・カスタマーセンターや役所の窓口
- 言語：日本語が中心。英語はメール（教員・企業・カスタマーサポート宛）

## できること

1. **相手との関係から、敬語の段階（0〜5）を決めます。** 家族へのLINE（段階0）から、初めて連絡する企業（段階5）まで。段階ごとに、文末・挨拶・宛名・結びの形が決まっています
2. **媒体と用件ごとの型に当てて書きます。** 媒体はメール・チャット・問い合わせフォーム・フリマの取引メッセージ。用件は依頼・質問・不具合の連絡・苦情・お礼・お詫び・断り・催促・日程調整・提出・返信。フリマは購入前の質問・値下げの相談・発送・受け取りと評価・届いた物の問題・キャンセルの場面を、メルカリの公式ガイドに沿って書きます
3. **書いた文面を機械で検査します。** `scripts/check.py` が、二重敬語や相手の動作への謙譲語、日付と曜日のずれ、丁寧すぎ、メールの署名の抜けなどを拾います。チャットでは挨拶だけの1通や全員への通知（@channel）、フリマでは電話番号・SNS・メルカリの外での支払いへの誘導も拾います
4. **自分の署名や呼び方を覚えさせられます。** 設定ファイル（profile）に、署名・相手ごとの段階・家族の呼び方・使わない語を書いておくと、毎回それに合わせます

敬語は多いほど丁寧になるわけではありません。文化審議会の「敬語の指針」も、過剰な敬語は丁寧にならないとしています。このスキルは、段階の中でいちばん簡素な形を選ぶように作っています。

## 入れ方

```bash
npx skills add <owner>/interpersonal-writing
```

Claude Code のプラグインとして入れる場合：

```text
/plugin marketplace add <owner>/interpersonal-writing
/plugin install interpersonal-writing@interpersonal-writing
```

手で入れる場合は、`skills/interpersonal-writing/` フォルダを `~/.claude/skills/` に写します。

## 設定ファイル（profile）

```bash
mkdir -p ~/.config/interpersonal-writing
cp skills/interpersonal-writing/profile.example.md ~/.config/interpersonal-writing/profile.md
```

写したファイルに、自分の署名・相手ごとの段階・呼び方を書きます。スキルの更新で上書きされないよう、スキルのフォルダの外に置きます。別の場所に置くときは環境変数 `INTERPERSONAL_WRITING_PROFILE` にパスを入れます。

## 使い方

エージェントに頼むだけです。

```text
就活中の企業の採用担当に、面接日程を変えてほしいとメールしたい。候補は10月28日と30日の午後。
```

```text
このメールの敬語を直して：（文面）
```

検査だけを使うこともできます（Python 3.11 以上・追加のライブラリ不要）。

```bash
python3 skills/interpersonal-writing/scripts/check.py mail.txt --level 4 --medium email --context job
```

```text
段階4・email・署名=job（profile: ~/.config/interpersonal-writing/profile.md）
[誤り] 7行目「ご確認してください」 「お（ご）〜する」は謙譲語Ⅰ。相手にしてもらう動作に「お（ご）〜してください／していただく」は使えない → 「して」を削る：ご確認ください／ご連絡いただけますか（敬語の指針 p.31・問【10】p.37）
[誤り] 9行目「10月21日（火）」 曜日が合っていない（2026年10月21日は水曜日） → （水）（カレンダー）
合計：誤り2・型0・注意0
```

## 段階の目安

| 段階 | 関係 | 例 |
|---|---|---|
| 0 | 家族 | 親・きょうだいへの LINE |
| 1 | 友人 | 友達への LINE |
| 2 | 身内の仕事仲間 | アルバイト先の同僚のグループ |
| 3 | 内の目上 | アルバイト先の店長 |
| 4 | 外の相手 | やり取りが続いている企業の担当者・教員・窓口 |
| 5 | 外の初対面 | 初めて連絡する企業・教員 |

詳しくは [references/levels.md](skills/interpersonal-writing/references/levels.md)。

## 根拠

規則の根拠は、公的機関・大学・業界団体・プラットフォームの公式資料だけです。中心は文化審議会答申「敬語の指針」（2007年）で、ページと問の番号まで記録しています。根拠が見つからない規則は「慣用」「私の判断」と明記しています。一覧は [references/sources.md](skills/interpersonal-writing/references/sources.md)。

## 試験

```bash
python3 -m unittest discover -s tests
```

拾うべき誤り（二重敬語・相手の動作への謙譲語など）を拾うことと、指針が「問題ない」とする言い方（とんでもございません・お伺いする・ご利用いただきまして など）を拾わないことを確かめています。

## 参考にしたスキル

構成の参考にしました（文言は写していません）。chezou/slop-nuki、robtar97/japanese-writing-skills、clawic/skills、yunyoumao/academic-email-jp-skill、ronantakizawa/japanese-email、davila7/claude-code-templates（いずれも MIT）。

## ライセンス

MIT
