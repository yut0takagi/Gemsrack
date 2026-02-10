---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  :root {
    --ca-green: #00a950;
    --text-main: #111;
    --text-sub: #555;
    --border-color: #ddd;
  }

  section {
    font-family: "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif;
    background: #fff;
    color: var(--text-main);
    padding: 60px 80px;
  }

  section::after {
    content: attr(data-marpit-pagination);
    position: absolute;
    bottom: 30px;
    right: 40px;
    font-size: 14px;
    color: #999;
  }

  h1 {
    font-size: 44px;
    margin-bottom: 20px;
  }

  h2 {
    font-size: 28px;
    border-bottom: 2px solid var(--ca-green);
    padding-bottom: 6px;
    margin-bottom: 24px;
  }

  h3 {
    font-size: 22px;
    margin-bottom: 12px;
  }

  p, li {
    font-size: 18px;
    line-height: 1.6;
  }

  .box {
    border: 1px solid var(--border-color);
    padding: 24px;
    margin-top: 20px;
    display: inline-block;
  }

  section.section {
    display: flex;
    align-items: center;
  }

  section.section h1 {
    font-size: 48px;
  }

  .em {
    color: var(--ca-green);
    font-weight: bold;
  }
---

# Gemsrack
Slackで作る、Bizチームのための小さな自動化「Gem」

<div class="box">
<p style="margin:0"><span class="em">作る</span>（テンプレ/AI）→ <span class="em">実行</span>（/gem）→ <span class="em">共有</span>（再利用）</p>
</div>

<p style="margin-top:18px;color:var(--text-sub)">対象: 営業 / CS / マーケ / 企画 / BizOps（Slackで仕事が回っているチーム）</p>

---

## このスライドで伝えたいこと

- **Gemsrackは、Slack上で “業務の型” をGemとして資産化**し、誰でも同じ品質で実行できる仕組み
- **Bizのよくある作業（文章/要約/整形/チェック/テンプレ返信）を最短で自動化**
- **導入は軽く、運用は安全に（公開/非公開・権限・ログ・保存）**

<div class="box">
<p style="margin:0">キーワード: <span class="em">再現性</span> / <span class="em">標準化</span> / <span class="em">Slack起点</span> / <span class="em">小さく始めて育てる</span></p>
</div>

---

## ありがちな課題（Biz現場）

- **同じ作業の繰り返し**: 返信文作成、議事録要約、提案書の叩き台、FAQ整形
- **属人化**: “できる人” の言い回し/手順がチームに残らない
- **品質のばらつき**: 新人・兼務・繁忙でアウトプットが揺れる
- **ツールの分断**: いろいろ散らばり、結局Slackに戻って手作業

<div class="box">
<p style="margin:0">狙いは「<span class="em">時間短縮</span>」だけでなく「<span class="em">品質の平準化</span>」「<span class="em">ナレッジの再利用</span>」</p>
</div>

---

## Before / After（現場の変化）

![bg right:45% w:520](./assets/before-after.svg)

### Before（手作業）
- 「誰かのやり方」を都度聞く / 過去ログを探す
- 文章/要約の品質が人によってブレる
- レビュー/差し戻しが増え、結局時間が溶ける

### After（Gemで標準化）
- **“仕事の型” をボタン1つで再実行**（/gem）
- **チェック観点を埋め込める**ので品質が揃う
- 新人でも同じレベルに寄せやすい（オンボーディング短縮）

---

## Gemsrackがやること

- SlackのSlashコマンドで **Gem（小さな自動化）を作成・実行**
- Gemは **静的テキスト** でも **AI（構造化）** でもOK
- 実行結果は **自分だけ**（DM）にも **チーム共有**（チャンネル）にも出せる
- Web UIで **Gem一覧を棚卸し**（どれが使われているか把握しやすい）

<p style="margin-top:10px;color:var(--text-sub)">“AIチャット” と違い、毎回お願いの仕方を考えなくても、<span class="em">決まった入力→決まった出力</span>で動きます。</p>

---

## Gemとは（業務の「型」）

Gemは、Biz作業を “再現可能な手順” に落としたものです。

- **入力**: 何を渡す？（例: 商談メモ、問い合わせ文、要点箇条書き）
- **処理**: どう考える？（例: 目的、トーン、制約、チェック観点）
- **出力**: 何を返す？（例: 返信テンプレ、要約、ToDo、表形式）

<div class="box">
<p style="margin:0"><span class="em">ポイント</span>: Gemは「個人の便利」から「チームの標準」へ育てられる</p>
</div>

---

## 画像イメージ（差し替えOK）

![w:980](./assets/slack-ui-placeholder.svg)

<p style="color:var(--text-sub)">ここは後で、実際のSlackのモーダル/実行結果のスクショに置き換える想定（いったんプレースホルダ）。</p>

---

## 代表ユースケース（すぐ効く）

- **営業**: 商談メモ→要点/次アクション/リスク、提案骨子、メール草案
- **CS**: 問い合わせ文→切り分け、一次回答テンプレ、エスカレ要約
- **マーケ**: 施策案→仮説/検証設計、SNS文面のバリエーション、LP要約
- **BizOps/企画**: 仕様の要点抽出、レビュー観点チェック、定例議事録の整理

<div class="box">
<p style="margin:0">向いている作業: <span class="em">繰り返す</span> / <span class="em">型がある</span> / <span class="em">品質を揃えたい</span> / <span class="em">Slackで完結させたい</span></p>
</div>

---

## ユースケース深掘り（営業）

![bg right:43% w:500](./assets/usecase-sales.svg)

### 入力（例）
- 商談メモ（箇条書きでもOK）
- 顧客の背景 / 課題 / 現状の運用 / 競合 / 次回までの宿題

### 出力（例）
- 要点（3行）/ 次アクション（担当者/期限）/ リスク（優先度付き）
- 提案骨子（見出し構成）/ フォローアップメール草案（丁寧トーン）

<p style="color:var(--text-sub)">営業の「思考の順番」をGemに閉じ込めると、再現性が上がります。</p>

---

## ユースケース深掘り（CS）

![bg right:43% w:500](./assets/usecase-cs.svg)

### 入力（例）
- 問い合わせ本文 + 事象の発生条件 + 影響範囲 + 直近変更点

### 出力（例）
- 切り分け質問（優先順）/ 一次回答テンプレ（丁寧&簡潔）
- エスカレーション要約（開発が欲しい情報の形式で）

<p style="color:var(--text-sub)">CSは「聞くべき項目」を漏れなく出すだけでも大きく改善します。</p>

---

## 実行イメージ（Slack）

- **一覧**: `/gem list`
- **実行**: `/gem <name>` または `/gem run <name>`
- **詳細**: `/gem show <name>`
- **共有して実行**: `/gem <name> --public`（結果をチャンネル投稿）

<div class="box">
<p style="margin:0">Slack内で完結するので、<span class="em">「使われ続ける」</span>が起きやすい</p>
</div>

---

## 作り方（2種類）

### 1) まずは最短（静的テキスト）

- 例: `/gem create hello おはようございます！`
- 例: `/gem create faq-ask 「状況を教えてください」テンプレ...`

### 2) 型を作る（AI Gem）

- `/gem create <name>` でモーダル
- **概要 / システム / 入力形式 / 出力形式** を保存して “再現性” を担保

<p style="margin-top:10px;color:var(--text-sub)">おすすめ: まずテンプレGemで「何が繰り返し作業か」を特定し、次にAI Gemで品質と速度を上げる。</p>

---

## AI Gemが強いポイント（Biz向け）

- **出力の型を固定**できる（例: 箇条書き・表・JSONなど）
- **チェック観点を埋め込める**（例: 法務/ブランド/NGワード/事実確認）
- **トーンを統一**できる（例: 丁寧/簡潔/社内向け/顧客向け）

<div class="box">
<p style="margin:0">“毎回AIにお願いする” ではなく、<span class="em">使える形にパッケージ化</span>する</p>
</div>

---

## AI Gemの「型」例（出力形式を固定）

例えば「商談要約Gem」の出力を固定すると、レビューしやすく、他の人も使いやすい。

- **要点（3行）**
- **課題（箇条書き）**
- **提案の方向性（3案）**
- **次アクション（担当/期限）**
- **確認事項（質問）**

<div class="box">
<p style="margin:0">型があるほど、チームは “<span class="em">出力を使い回す</span>” 文化になりやすい</p>
</div>

---

## 期待できる効果（例）

- **時間削減**: 文章作成/要約/整形のリードタイム短縮
- **品質の平準化**: ばらつきが減り、レビュー負荷が下がる
- **オンボーディング短縮**: 新人でもGemで標準アウトプットに寄せられる
- **ナレッジの棚卸し**: “よく使う型” が一覧化され、改善が回る

---

## 運用・ガバナンス（安心して使う）

- **公開/非公開**: `--public` でチャンネル共有、通常は個人DMで実行も可能
- **権限とスコープ**: Slack Appのスコープは必要最小（例: `commands`, `chat:write`）
- **保存先**: Cloud Run運用は Firestore（推奨）、ローカルはメモリフォールバック
- **拡張性**: コマンド/イベントを追加して運用に合わせられる

<p style="margin-top:10px;color:var(--text-sub)">「公開投稿は必要なときだけ」「通常は個人DMで試す」運用にすると、チームの心理的安全性も保てます。</p>

---

## システム構成（ざっくり）

- 図: 全体像（差し替えOK）

![w:980](./assets/architecture.svg)

- **Slack**: `/gem` コマンド・イベント受信
- **Cloud Run**: Python/FlaskのBotサーバ（`POST /slack/events`）
- **Firestore**: Gem定義の永続化（Cloud Runで推奨）
- **Gemini API（任意）**: AI Gem実行（環境変数でON）
- **Web UI（React）**: `/` でGem一覧の閲覧（棚卸し用）

---

## 導入ステップ（最短）

- Slack Appを作成し、スコープ設定（`commands`, `chat:write` など）
- Cloud Runへデプロイし、Request URL を `/slack/events` に設定
- まずは **3〜5個のGem** を作る（頻出作業から）
- 使われたGemを見ながら、**入力/出力の型**と**チェック観点**を磨く

<div class="box">
<p style="margin:0">最初は「テンプレGem」→ 次に「AI Gem」で標準化、の順がスムーズ</p>
</div>

---

## 導入の進め方（おすすめの型）

- **Day 0**: よくある作業を棚卸し（10〜20個の候補を出す）
- **Day 1**: 上位3つをテンプレGem化（とにかく使い始める）
- **Week 1**: 利用ログとヒアリングで改善（入力/出力/観点を固める）
- **Week 2**: AI Gem化（品質の平準化・チェック観点の埋め込み）
- **以降**: 「作る」より「育てる」（毎週使われるGemを増やす）

<div class="box">
<p style="margin:0">ゴールはGemの数ではなく、<span class="em">現場の定着</span>と<span class="em">運用の改善サイクル</span></p>
</div>

---

## 効果測定（Bizが見たい指標）

- 図: KPI例（差し替えOK）

![w:980](./assets/kpi.svg)

- **利用回数**: `/gem` 実行回数（チーム/個人）
- **削減時間**: Gemごとの想定短縮（例: 1回あたり5分）×回数
- **品質**: レビュー指摘数、一次回答の解決率、返信速度
- **定着**: “毎週使われるGem” の数、使われないGemの整理

---

## 次の一手（提案）

- Bizの定例から、**10分で作れるGemを3つ**選ぶ
  - 例: 「商談メモ要約」「一次回答テンプレ」「議事録ToDo化」
- 1週間運用して、**型の改善**（入力/出力/NG観点）を1回回す
- 以降は “Gemを増やす” ではなく、**よく使うGemを育てる**

<div class="box">
<p style="margin:0"><span class="em">Gemsrack</span>: Slackを入口に、Bizの仕事を資産化する</p>
</div>

---

## 付録: 画像を本物に差し替えるとき

- `docs/assets/` のSVGは **プレースホルダ**です
- 実際の画面（Slackモーダル、実行結果、Gem一覧UI）スクショがあれば
  - `./assets/slack-ui-placeholder.svg` をスクショに差し替え
  - 必要なら「個人情報/顧客名」をモザイクした版を作成

<div class="box">
<p style="margin:0">スクショをもらえれば、レイアウトに合わせて <span class="em">最適なサイズ/配置</span>までこちらで整えます</p>
</div>