---
marp: true
title: Gemsrack - SlackBot on Cloud Run
description: Slack上でGemを作成・実行できるSlackBot（Cloud Run / GitHub Actions 自動デプロイ）
size: 16:9
paginate: true
header: "Gemsrack"
footer: "Cloud Run / Slack Bolt / GitHub Actions"
style: |
  /* CyberAgent “っぽい”ミニマル寄せ（完全再現ではなく雰囲気） */
  :root {
    --fg: #111111;
    --muted: #5b5b5b;
    --bg: #ffffff;
    --bg2: #0b0f14;
    --accent: #00a99d;
    --accent2: #19c37d;
    --codebg: #0f172a;
  }

  section {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
      "Hiragino Sans", "Noto Sans JP", "Yu Gothic", "Meiryo", Arial, sans-serif;
    color: var(--fg);
    background: var(--bg);
    padding: 64px 72px;
    letter-spacing: 0.01em;
  }

  h1 {
    font-size: 54px;
    line-height: 1.05;
    margin: 0 0 18px 0;
    font-weight: 800;
  }
  h2 {
    font-size: 34px;
    line-height: 1.18;
    margin: 0 0 18px 0;
    font-weight: 800;
  }
  h3 {
    font-size: 24px;
    line-height: 1.2;
    margin: 0 0 12px 0;
    font-weight: 800;
  }
  p, li {
    font-size: 22px;
    line-height: 1.45;
  }
  strong { color: var(--accent); }
  a { color: var(--accent); }
  ul { margin: 10px 0 0 0; }
  li { margin: 8px 0; }

  h1::after, h2::after {
    content: "";
    display: block;
    width: 88px;
    height: 6px;
    margin-top: 14px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 999px;
  }

  header, footer {
    font-size: 14px;
    color: var(--muted);
  }

  pre, code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  }
  pre {
    background: var(--codebg);
    color: #e5e7eb;
    padding: 14px 16px;
    border-radius: 12px;
  }
  code {
    background: #eef2ff;
    padding: 2px 6px;
    border-radius: 8px;
  }

  .cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 28px;
    align-items: start;
  }
  .card {
    border: 1px solid #e6e6e6;
    border-radius: 16px;
    padding: 18px 18px;
  }
  .card h3::after { content: none; }

  section.cover {
    background: radial-gradient(1200px 700px at 20% 10%, #102531 0%, var(--bg2) 55%, #070a0f 100%);
    color: #f9fafb;
  }
  section.cover header, section.cover footer { color: rgba(255,255,255,0.65); }
  section.cover strong { color: #7fffd4; }
  section.cover h1::after { background: linear-gradient(90deg, #7fffd4, var(--accent2)); }

  section.dark {
    background: var(--bg2);
    color: #f9fafb;
  }
  section.dark header, section.dark footer { color: rgba(255,255,255,0.65); }
  section.dark code { background: rgba(255,255,255,0.10); color: #f9fafb; }
  section.dark h1::after, section.dark h2::after {
    background: linear-gradient(90deg, var(--accent2), var(--accent));
  }
---

<!-- _class: cover -->

# Gemsrack
Slackで “作業” を “実行” に変える  
小さな自動化（Gem）を増やしていく社内プロダクト

---

## 一言でいうと
**Slack上から業務タスクを安全に実行できる「社内向け自動化の入口」**です。

- 依頼・確認・実行が Slack で完結
- “よくある作業” を Gem として追加していける
- 追加しても運用が増えない（Cloud Run + 自動デプロイ）

---

## なぜ必要？（現場のあるある）
- Slackでの依頼が **人依存・属人化** しやすい
- 手作業の転記/確認が多く、**ミス** と **待ち** が発生
- “ちょっとした自動化” が点在して、**探せない・再利用できない**
- 運用が怖くて仕組み化できない（権限/ログ/秘密情報）

---

## Gemsrack が提供する価値
- **スピード**: Slackから即実行・即レス（待ち時間の削減）
- **品質**: 手順の標準化でミスを減らす
- **再利用**: 「作った自動化」を組織で使い回す
- **ガバナンス**: 実行ログ/秘密情報管理/失敗通知を前提にする

---

## できること（例）
“Gem” は **小さく作って増やす**前提の機能単位です。

<div class="cols">
  <div class="card">
    <h3>チーム運用</h3>
    <ul>
      <li>定例レポート集計→投稿</li>
      <li>リリース告知テンプレ生成</li>
      <li>当番/ローテのリマインド</li>
    </ul>
  </div>
  <div class="card">
    <h3>情報処理</h3>
    <ul>
      <li>URL要約/翻訳/要点抽出</li>
      <li>ファイルの整形（画像/CSV）</li>
      <li>社内FAQ検索→回答案</li>
    </ul>
  </div>
</div>

---

## どう使う？（ユーザー体験）
- **Slash command**: `/xxxxx` で実行（必要なら入力を促す）
- **メンション**: `@Gemsrack 〜して` で実行（会話の流れで）
- 結果は **スレッド** に返して、会話の文脈を崩さない
- 失敗時は理由と次アクションを返す（運用に残さない）

---

## 実績（いま動いているもの）
### 対応済み（MVP）
- **`/hello`**（Slash command）
- **`app_mention`**（メンションイベント）

→ まずは “Gem を増やす土台” を作った段階です。

---

## 導入・運用（ビジネス観点）
- **運用基盤**: Cloud Run（スケール・可用性・運用負担を最小化）
- **更新**: GitHub の `main` への push/merge で自動デプロイ
- **秘密情報**: repoに置かない（Cloud Run env / Secret Manager）
- **監視**: `/health` で疎通、失敗は Slack に通知できる設計へ拡張

---

## 成果指標（KPI例）
- **削減時間**: 1回あたりの作業時間 × 実行回数
- **リードタイム**: 依頼→完了までの時間
- **品質**: 手戻り/ミス/問い合わせの減少
- **定着**: 週次アクティブ利用者、Gem利用回数、継続率

---

## ロードマップ（例）
- **いま**: Gem を増やす土台（Slack受信・拡張構成・デプロイ自動化）
- **次**: よく使う Gem を 5〜10 個作る（価値の可視化）
- **その次**: 実行ログ/権限/承認フロー・スケジュール実行（運用の型）

---

<!-- _class: dark -->

## 付録：技術概要（開発者向け）
- Slack → `POST /slack/events` を Cloud Run で受信
- 実装は **Slack Bolt + Flask**
- コマンド/イベントは **1ファイル=1機能**で増やす

---

<!-- _class: dark -->

## 付録：拡張しやすいディレクトリ構成

```text
gemsrack/
  routes/                 # HTTP ルート
    health.py
    slack.py              # /slack/events
  slack/
    build.py              # Bolt App 初期化
    registry.py           # register() 自動ロード
    commands/             # Slash commands
      hello.py
    events/               # Events
      app_mention.py
```

---

<!-- _class: dark -->

## 付録：ローカル開発（Docker）

```bash
cp .env.example .env
# SLACK_BOT_TOKEN / SLACK_SIGNING_SECRET を設定

docker compose up --build
curl -sS localhost:8080/health
```

---

<!-- _class: dark -->

## 付録：Cloud Run デプロイ（手動）

```bash
gcloud run deploy gemsrack-slackbot \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated
```

- Slack 側 Request URL:  
  `https://<CloudRunURL>/slack/events`

---

<!-- _class: dark -->

## 付録：自動デプロイ（GitHub Actions）
- Trigger: `main` への push（= PR merge 後も同様）
- 認証: Workload Identity Federation（鍵なし）
- 実行: `gcloud run deploy --source .`