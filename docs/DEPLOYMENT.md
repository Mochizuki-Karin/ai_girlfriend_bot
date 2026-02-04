# AIガールフレンドボット - デプロイガイド

このドキュメントでは、AIガールフレンドボットを様々な環境にデプロイする方法について詳しく説明します。

## 目次

1. [クイックデプロイ](#クイックデプロイ)
2. [Dockerデプロイ](#dockerデプロイ)
3. [ローカルデプロイ](#ローカルデプロイ)
4. [本番環境デプロイ](#本番環境デプロイ)
5. [クラウドプラットフォームデプロイ](#クラウドプラットフォームデプロイ)
6. [トラブルシューティング](#トラブルシューティング)

---

## クイックデプロイ

### スタートアップスクリプトを使用（推奨）

```bash
# 1. プロジェクトを解凍
tar -xzf ai_girlfriend_bot.tar.gz
cd ai_girlfriend_bot

# 2. 環境変数を設定
cp .env.example .env
# .env ファイルを編集し、APIキーを入力

# 3. スタートアップスクリプトを実行
chmod +x start.sh
./start.sh
```

---

## Dockerデプロイ

### 基本デプロイ

```bash
# すべてのサービスを起動
docker-compose up -d

# ログを確認
docker-compose logs -f

# サービスを停止
docker-compose down
```

### Redisキャッシュ付き

```bash
docker-compose --profile with-redis up -d
```

### ローカルモデル付き (Ollama)

```bash
# Ollamaを含むサービスを起動
docker-compose --profile with-ollama up -d

# モデルをダウンロード
docker-compose exec ollama ollama pull qwen:7b

# ローカルモデルを使用するように設定
# .envを編集:
# DEFAULT_LLM_PROVIDER=local
# LOCAL_MODEL_URL=http://ollama:11434
# LOCAL_MODEL_NAME=qwen:7b
```

### Makefileを使用

```bash
# イメージをビルド
make build

# サービスを起動
make start

# ステータスを確認
make status

# ログを確認
make logs

# サービスを停止
make stop
```

---

## ローカルデプロイ

### 環境要件

- Python 3.11+
- 4GB+ RAM
- (オプション) ローカルモデル用GPU

### インストール手順

```bash
# 1. 仮想環境を作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 依存関係をインストール
pip install -r requirements.txt

# 3. 環境変数を設定
cp .env.example .env
# .env ファイルを編集

# 4. 実行
python -m src.bot
```

---

## 本番環境デプロイ

### Docker Swarmを使用

```bash
# Swarmを初期化
docker swarm init

# デプロイ
docker stack deploy -c docker-compose.yml ai-gf-bot

# サービスを確認
docker stack ps ai-gf-bot

# サービスを更新
docker service update ai-gf-bot_ai-girlfriend-bot
```

### Kubernetesを使用

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-girlfriend-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-girlfriend-bot
  template:
    metadata:
      labels:
        app: ai-girlfriend-bot
    spec:
      containers:
      - name: bot
        image: ai-girlfriend-bot:latest
        envFrom:
        - secretRef:
            name: bot-secrets
        volumeMounts:
        - name: data
          mountPath: /app/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: bot-data-pvc
```

デプロイ：

```bash
# シークレットを作成
kubectl create secret generic bot-secrets \
  --from-literal=TELEGRAM_BOT_TOKEN=xxx \
  --from-literal=OPENAI_API_KEY=xxx

# デプロイ
kubectl apply -f k8s-deployment.yaml

# ステータスを確認
kubectl get pods
kubectl logs -f deployment/ai-girlfriend-bot
```

---

## クラウドプラットフォームデプロイ

### 阿里雲 ECS にデプロイ

```bash
# 1. ECS インスタンスを作成（推奨 2コア4GB）
# 2. Docker をインストール
curl -fsSL https://get.docker.com | sh

# 3. プロジェクトをクローン
git clone <your-repo>
cd ai_girlfriend_bot

# 4. 環境変数を設定
vi .env

# 5. 起動
docker-compose up -d
```

### AWS EC2 にデプロイ

```bash
# 1. EC2 インスタンスを起動
# 2. Docker をインストール
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# 3. Docker Compose をインストール
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. プロジェクトをデプロイ
cd ~/ai_girlfriend_bot
docker-compose up -d
```

### Railway にデプロイ

```bash
# 1. Railway CLI をインストール
npm install -g @railway/cli

# 2. ログイン
railway login

# 3. プロジェクトを初期化
railway init

# 4. 環境変数を設定
railway variables set TELEGRAM_BOT_TOKEN=xxx
railway variables set OPENAI_API_KEY=xxx

# 5. デプロイ
railway up
```

### Render にデプロイ

1. プロジェクトを GitHub にフォーク
2. Render で Web Service を作成
3. Docker 環境を選択
4. 環境変数を追加
5. デプロイ

### Heroku にデプロイ

```bash
# 1. Heroku CLI をインストール
# 2. ログイン
heroku login

# 3. アプリケーションを作成
heroku create your-bot-name

# 4. 環境変数を設定
heroku config:set TELEGRAM_BOT_TOKEN=xxx
heroku config:set OPENAI_API_KEY=xxx

# 5. デプロイ
git push heroku main
```

---

## モニタリングとログ

### Prometheus + Grafana を使用

```yaml
# docker-compose.yml に追加
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
```

### ログ収集

```bash
# リアルタイムログを確認
docker-compose logs -f --tail=100

# ログをエクスポート
docker-compose logs > bot_logs_$(date +%Y%m%d).txt

# ログローテーションを使用
docker-compose logs -f | rotatelogs logs/bot.log 86400
```

---

## バックアップと復元

### 自動バックアップ

```bash
# バックアップスクリプトを作成
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# データをバックアップ
tar -czf $BACKUP_DIR/data.tar.gz data/
tar -czf $BACKUP_DIR/config.tar.gz config/

# 最近7日間のバックアップを保持
find /backups -type d -mtime +7 -exec rm -rf {} \;
EOF

chmod +x backup.sh

# スケジュールタスクに追加
crontab -e
# 追加: 0 2 * * * /path/to/backup.sh
```

### Makefileを使用

```bash
# バックアップ
make backup

# 復元
make restore
```

---

## トラブルシューティング

### よくある問題

#### 1. コンテナが起動できない

```bash
# ログを確認
docker-compose logs ai-girlfriend-bot

# 環境変数を確認
docker-compose config

# コンテナを再構築
docker-compose down
docker-compose up -d --build
```

#### 2. LLM API に接続できない

```bash
# ネットワークを確認
docker-compose exec ai-girlfriend-bot ping api.openai.com

# APIキーを確認
docker-compose exec ai-girlfriend-bot env | grep API_KEY

# APIをテスト
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

#### 3. メモリ不足

```bash
# メモリ使用状況を確認
docker stats

# コンテナメモリを制限
docker-compose up -d --memory=2g

# スワップパーティションを使用
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. データベース破損

```bash
# 現在のデータをバックアップ
cp -r data data.backup.$(date +%Y%m%d)

# データベースをリセット
docker-compose down
rm -rf data/chroma/*
docker-compose up -d

# バックアップから復元
cp -r data.backup.20240204/* data/
```

### デバッグモード

```bash
# デバッグログを有効化
DEBUG=1 docker-compose up -d

# コンテナ内でデバッグ
docker-compose exec ai-girlfriend-bot /bin/sh

# Pythonを手動実行
docker-compose exec ai-girlfriend-bot python -m src.bot
```

---

## パフォーマンス最適化

### 1. Redisキャッシュを使用

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
```

```env
# .env
USE_REDIS=true
REDIS_URL=redis://redis:6379/0
```

### 2. モデル量子化

```python
# 8bit量子化を使用
load_in_8bit=True

# 4bit量子化を使用 (QLoRA)
load_in_4bit=True
bnb_4bit_compute_dtype=torch.bfloat16
```

### 3. バッチリクエスト処理

```python
# 返信をバッチ生成
responses = await asyncio.gather(*[
    generate_response(user_id, msg)
    for user_id, msg in batch
])
```

---

## セキュリティ推奨事項

1. **APIキーを保護**
   - Docker Secrets または K8s Secrets を使用
   - コードにキーをハードコードしない
   - 定期的にキーをローテーション

2. **アクセス制限**
   - ファイアウォールでポートアクセスを制限
   - Telegram Bot をプライベートチャットのみ許可するように設定
   - 管理者ホワイトリストを設定

3. **データ保護**
   - 定期的にデータをバックアップ
   - 機密データを暗号化
   - データ保護規制を遵守

---

## 更新とメンテナンス

```bash
# コードを更新
git pull

# イメージを再構築
docker-compose build --no-cache

# ローリングアップデート
docker-compose up -d

# 古いイメージをクリーンアップ
docker image prune -f
```

---
**デプロイが順調に行きますように！** 🤖💕
