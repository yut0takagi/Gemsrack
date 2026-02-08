# Gemsrack
- Slack上で`Gem`を作成・実行できる`SlackBot`

## Cloud Run に Slack Bot (Python) をデプロイする

このリポジトリには、Slack の Events / Slash Commands を受け取る最小の Python サーバが入っています。

- **エンドポイント**: `POST /slack/events`
- **ヘルスチェック**: `GET /health`
- **必要な環境変数**:
  - `SLACK_BOT_TOKEN`（`xoxb-...`）
  - `SLACK_SIGNING_SECRET`

### ローカル起動（Python）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_SIGNING_SECRET="..."

python main.py
curl -sS localhost:8080/health
```

### ローカル起動（Docker / docker compose）

`.env` を用意します（雛形: `.env.example`）。

```bash
cp .env.example .env
# .env を編集して SLACK_BOT_TOKEN / SLACK_SIGNING_SECRET を設定

docker compose up --build
# 起動直後は準備中のことがあるので、通らない場合は数秒待って再実行
curl -sS localhost:8080/health
```

補足:
- `.env` を作らなくても起動はしますが、その場合 `POST /slack/events` は 500 を返します（Slack 未設定のため）。
- `.env` は `.gitignore` 済みです（秘密情報の誤コミット防止）。

### Slack App 側の設定

Slack の App 管理画面で以下を設定します。

- **OAuth & Permissions**
  - Bot Token Scopes に最低限 `commands` と `chat:write` を付与（必要に応じて追加）
  - Install to Workspace を実行して `SLACK_BOT_TOKEN` を取得
- **Basic Information**
  - App Credentials の `Signing Secret` を `SLACK_SIGNING_SECRET` として使用
- **Event Subscriptions**
  - Enable Events を ON
  - Request URL を `https://<CloudRunのURL>/slack/events` に設定
  - Subscribe to bot events に例として `app_mention` を追加（`gemsrack/slack/events/app_mention.py`）
- **Slash Commands**（例: `/hello`）
  - Command を `/hello`
  - Request URL を `https://<CloudRunのURL>/slack/events` に設定

### Cloud Run へデプロイ（例: Artifact Registry を使わない最短）

GCP プロジェクト/リージョンは適宜置き換えてください。

```bash
gcloud config set project YOUR_PROJECT_ID

gcloud run deploy gemsrack-slackbot \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars SLACK_BOT_TOKEN="xoxb-...",SLACK_SIGNING_SECRET="..."
```

デプロイ後、表示される URL に対して Slack 側の Request URL を
`<CloudRunのURL>/slack/events` へ設定してください。

## 追加実装のガイド（今後コマンド/イベントを増やす）

### Slash Command を増やす
- 例: `gemsrack/slack/commands/ping.py` を作成
- ファイル内に `register(slack_app)` を定義する
- 自動で読み込まれます（アプリ起動時に `gemsrack.slack.commands` 配下を探索）

### Event を増やす
- 例: `gemsrack/slack/events/reaction_added.py` を作成
- ファイル内に `register(slack_app)` を定義する
- 自動で読み込まれます（アプリ起動時に `gemsrack.slack.events` 配下を探索）
