# Gemsrack
- Slack上で`Gem`を作成・実行できる`SlackBot`

## Cloud Run に Slack Bot (Python) をデプロイする

このリポジトリには、Slack の Events / Slash Commands を受け取る `Python/Flask` サーバが入っています。

- **エンドポイント**: `POST /slack/events`
- **ヘルスチェック**: `GET /health`
- **Web UI**: `GET /`（ReactでGem一覧を閲覧）
- **Admin UI**:
  - `GET /admin/login`（ログインページ）
  - `GET /admin/dashboard`（管理画面）
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
export GEMINI_API_KEY="..." # AI Gem を実行する場合
export GEMINI_IMAGE_MODEL="gemini-3-pro-image-preview" # 画像生成Gemで使用（任意）

python main.py
curl -sS localhost:8080/health
```

## Web UI（React）で Gem 一覧を見る

Slack 以外から Gem を確認するために、`frontend/` に React（Vite）製の簡易UIを同梱しています。

### 1) バックエンド（API）を起動

Gem一覧は JSON API で取得します。

- `GET /api/gems`（一覧）
- `GET /api/gems/<name>`（詳細）

Slack と同じ Firestore を見せたい場合は、**Slack の team_id** を `GEMSRACK_TEAM_ID` に設定してください
（単一ワークスペース運用ならこれが一番楽です）。

#### team_id（Workspace ID）の調べ方

以下のどれかが簡単です。

- **Slackをブラウザで開く**: URL が `https://app.slack.com/client/TXXXXXXXXX/...` の形式なら、`TXXXXXXXXX` が team_id です
- **Slack API（Bot token）で確認**:

```bash
curl -sS -H "Authorization: Bearer $SLACK_BOT_TOKEN" https://slack.com/api/auth.test | jq
```

レスポンスの `team_id` が該当します（`jq` が無ければ `| jq` を外してください）。

```bash
export GEMSRACK_TEAM_ID="T0123456789" # 任意。未指定なら "local"
python main.py
```

### 2) フロントエンドを起動（開発）

Vite の dev server から `/api` を `http://localhost:8080` に proxy します（CORS不要）。

```bash
cd frontend
npm install
npm run dev
```

ブラウザで `http://localhost:5173` を開くと、Gem一覧を閲覧できます。

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
- UI は `http://localhost:8080/` で確認できます（Gem一覧）。

### Slack App 側の設定

Slack の App 管理画面で以下を設定します。

- **OAuth & Permissions**
  - Bot Token Scopes に最低限 `commands` と `chat:write` を付与
  - 画像生成Gemを使う場合は `files:write` と `im:write` も付与（DMに画像を送るため）
  - Install to Workspace を実行して `SLACK_BOT_TOKEN` を取得
- **Basic Information**
  - App Credentials の `Signing Secret` を `SLACK_SIGNING_SECRET` として使用
- **Event Subscriptions**
  - Enable Events を ON
  - Request URL を `https://<CloudRunのURL>/slack/events` に設定（末尾のパスまで必須）
  - Subscribe to bot events に例として `app_mention` を追加（`gemsrack/slack/events/app_mention.py`）
- **Interactivity & Shortcuts**
  - Interactivity を ON
  - Request URL を `https://<CloudRunのURL>/slack/events` に設定（末尾のパスまで必須。モーダルの Save などで必須）
- **Slash Commands**（例: `/hello`）
  - Command を `/hello`
  - Request URL を `https://<CloudRunのURL>/slack/events` に設定（末尾のパスまで必須）
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

補足:
- `--source .` でのデプロイは、リポジトリ直下の `Dockerfile` を検出すると **Dockerfileでビルド**されます。
- この Dockerfile は **Reactフロント（`frontend/`）も同梱してビルド**するため、Cloud Run のURLの `/` でGem一覧UIが表示されます。

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

- **作成/更新（互換: 静的テキスト）**: `/gem create <name> <body...>`
- **作成/更新（AI Gem定義: フォーム）**: `/gem create <name>`（モーダルが開きます）
- **作成/更新（AI Gem定義: フラグ）**: `/gem create <name> --summary "..." --system "..." --input "..." --output "..."`
- **実行**: `/gem <name>` または `/gem run <name>`
- **詳細表示**: `/gem show <name>`
- **一覧**: `/gem list`
- **削除**: `/gem delete <name>`
- **公開実行**: `/gem <name> --public`（結果をチャンネルに投稿）

例:
- `/gem create hello おはようございます！`
- `/gem hello`
- `/gem create slide`（モーダルで「概要/システムプロンプト/入力形式/出力形式」を保存）

### 画像生成 Gem（新機能）
- 出力形式に `image_url` を選ぶと、画像生成Gemとして実行できます。
- 実行時の挙動:
  - `--public` 指定あり: 生成画像を Slash コマンドのチャンネルへアップロード
  - `--public` 指定なし: Bot からユーザーのDMへ画像を送信（`im:write` が必要）
- 必要スコープ: `files:write`（必須）と `im:write`（DM送信時）
- 補足: 生成には Gemini 画像生成APIを使用します（環境変数 `GEMINI_API_KEY` 必須）

### 保存先（永続化）
- **Cloud Run**: Firestore（推奨 / 自動で使います）
- **ローカル**: 認証が無い場合はメモリにフォールバック（再起動で消えます）
- 環境変数 `GEM_STORE_BACKEND` で保存先を切り替え可能（`auto` / `firestore` / `memory`）
- Cloud Run では `GEM_STORE_BACKEND=firestore` を推奨（初期化失敗時に起動を止めて Gem 消失を防止）

Cloud Run の実行 Service Account に Firestore 権限が必要です（例: `roles/datastore.user`）。

## 利用計測（KPI）

Gemの実行回数をKPIとして計測するため、実行時に日次カウントを保存します（Cloud RunではFirestore推奨）。

- **集計API**: `GET /api/metrics/gem-usage?days=30&limit=20`
- **保存先切替**: `GEM_METRICS_BACKEND`（`auto` / `firestore` / `memory` / `none`）

## Admin（Gem管理）

Gemの **Slackでの実行可否（enable/disable）** や、より詳細な利用状況を見るために Admin API / UI を用意しています。

- **Web UI（公開UIと完全分離）**
  - `GET /admin/login`
  - `GET /admin/dashboard`
- **ログイン必須**: `ADMIN_PASSWORD`（パスワード）
  - Cloud Run の環境変数に `ADMIN_PASSWORD` を設定してください（推測されにくい文字列）
  - あわせて `SECRET_KEY` も設定してください（セッション署名用）
  - UIのログイン欄にパスワードを入れると、**セッション（HttpOnly Cookie）** でログイン状態になります
- **Admin API**
  - `GET /api/admin/gems`（Gem一覧 + enabled）
  - `PATCH /api/admin/gems/<name>`（`{"enabled": true/false}`）
  - `GET /api/admin/usage?days=30`
  - `POST /api/admin/login` / `POST /api/admin/logout` / `GET /api/admin/me`

### Gemini API（AI Gem 実行）
- Cloud Run の環境変数 `GEMINI_API_KEY` を設定してください
- 省略時はデフォルトで `GEMINI_MODEL=gemini-2.5-flash` を使用します
- 画像生成Gemは `GEMINI_IMAGE_MODEL` を使用します（既定: `gemini-3-pro-image-preview`）

