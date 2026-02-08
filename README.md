# Gemsrack
- Slack上で`Gem`を作成・実行できる`SlackBot`

## Cloud Run に Slack Bot (Python) をデプロイする

このリポジトリには、Slack の Events / Slash Commands を受け取る `Python/Flask` サーバが入っています。

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
  - 追加で `/gem` も作成（Request URL は同じ）

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

## GitHub の main push で自動デプロイ（GitHub Actions）

このリポジトリには `.github/workflows/deploy-cloud-run.yml` を同梱しています。  
**鍵ファイル不要**の Workload Identity Federation で GitHub Actions から Cloud Run にデプロイします。

### 1) GCP 側（Workload Identity Federation + SA）

以下は例です（`ORG/REPO` とプロジェクト番号などは置き換え）。

```bash
PROJECT_ID=gemsrack
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
REGION=asia-northeast1

POOL_ID=github
PROVIDER_ID=github
SA_NAME=gemsrack-gha-deployer
REPO="ORG/REPO" # 例: yutotakagi/Gemsrack

gcloud iam workload-identity-pools create "${POOL_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions pool"

gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" \
  --display-name="GitHub provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="attribute.repository=='${REPO}'"

gcloud iam service-accounts create "${SA_NAME}" --project "${PROJECT_ID}"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Cloud Run へのデプロイに必要な権限（最小寄せ。必要に応じて追加）
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.admin"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudbuild.builds.editor"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.admin"
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}" \
  --role="roles/iam.workloadIdentityUser"

WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
echo "WIF Provider: ${WIF_PROVIDER}"
echo "Service Account: ${SA_EMAIL}"
```

### 2) GitHub 側（Secrets）

GitHub リポジトリの **Settings → Secrets and variables → Actions** に以下を追加:
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: 上の `WIF Provider` の値
- `GCP_SERVICE_ACCOUNT_EMAIL`: 上の `Service Account` の値

※ Slack の `SLACK_BOT_TOKEN` / `SLACK_SIGNING_SECRET` は **Cloud Run 側に保持**しておく運用がおすすめです  
（workflow は既存の環境変数を上書きしないため、GitHub Secrets に Slack 秘密値を置かずに済みます）。

## 追加実装のガイド（今後コマンド/イベントを増やす）

### Slash Command を増やす
- 例: `gemsrack/slack/commands/ping.py` を作成
- ファイル内に `register(slack_app)` を定義する
- 自動で読み込まれます（アプリ起動時に `gemsrack.slack.commands` 配下を探索）

### Event を増やす
- 例: `gemsrack/slack/events/reaction_added.py` を作成
- ファイル内に `register(slack_app)` を定義する
- 自動で読み込まれます（アプリ起動時に `gemsrack.slack.events` 配下を探索）

## Gem 機能（作成・実行）

`/gem` コマンドで “Gem（小さな自動化）” を作成・実行できます。

- **作成/更新**: `/gem create <name> <body...>`
- **実行**: `/gem <name>` または `/gem run <name>`
- **一覧**: `/gem list`
- **削除**: `/gem delete <name>`
- **公開実行**: `/gem <name> --public`（結果をチャンネルに投稿）

例:
- `/gem create hello おはようございます！`
- `/gem hello`

### 保存先（永続化）
- **Cloud Run**: Firestore（推奨 / 自動で使います）
- **ローカル**: 認証が無い場合はメモリにフォールバック（再起動で消えます）

Cloud Run の実行 Service Account に Firestore 権限が必要です（例: `roles/datastore.user`）。
