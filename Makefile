# AI Girlfriend Bot - Makefile

.PHONY: help install start stop restart logs status clean persona knowledge stats

# デフォルトターゲット
help:
	@echo "AI Girlfriend Bot - 仮想女友ロボット"
	@echo ""
	@echo "利用可能なコマンド:"
	@echo "  make install     - 依存関係をインストール"
	@echo "  make start       - サービスを起動 (Docker)"
	@echo "  make start-local - ローカルで実行"
	@echo "  make stop        - サービスを停止"
	@echo "  make restart     - サービスを再起動"
	@echo "  make logs        - ログを表示"
	@echo "  make status      - ステータスを表示"
	@echo "  make clean       - データをクリーン"
	@echo "  make persona     - キャラクターを編集"
	@echo "  make knowledge   - 知識をインポート"
	@echo "  make stats       - 統計を表示"
	@echo "  make build       - Dockerイメージをビルド"
	@echo "  make shell       - コンテナに入る"

# 依存関係をインストール
install:
	pip install -r requirements.txt

# Docker起動
start:
	docker-compose up -d
	@echo "✅ サービスが起動しました"
	@echo "ログを表示: make logs"

# Redis付き起動
start-redis:
	docker-compose --profile with-redis up -d
	@echo "✅ サービスが起動しました（Redis含む）"

# ローカル起動
start-local:
	python -m src.bot

# サービスを停止
stop:
	docker-compose down
	@echo "✅ サービスが停止しました"

# サービスを再起動
restart: stop start

# ログを表示
logs:
	docker-compose logs -f --tail=100

# ステータスを表示
status:
	@echo "📊 コンテナステータス:"
	@docker-compose ps
	@echo ""
	@echo "📊 リソース使用状況:"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# データをクリーン
clean:
	@echo "⚠️  これによりすべてのデータが削除されます!"
	@read -p "確認? [y/N] " confirm && [ $$confirm = y ] && \
		docker-compose down -v && \
		rm -rf data/* logs/* && \
		echo "✅ データがクリーンされました" || \
		echo "❌ キャンセルされました"

# キャラクターを編集
persona:
	python tools/persona_editor.py

# 知識をインポート
knowledge:
	@echo "知識インポートツール"
	@echo "使い方: python tools/knowledge_importer.py [file|dir|text|stats] <引数>"

# 統計を表示
stats:
	python tools/knowledge_importer.py stats

# イメージをビルド
build:
	docker-compose build

# コンテナに入る
shell:
	docker-compose exec ai-girlfriend-bot /bin/sh

# コードを更新
update:
	git pull
	docker-compose build
	docker-compose up -d

# データをバックアップ
backup:
	@mkdir -p backups
	@tar -czf backups/backup-$$(date +%Y%m%d-%H%M%S).tar.gz data/ config/
	@echo "✅ バックアップ完了"

# データをリストア
restore:
	@ls -t backups/ | head -5
	@read -p "バックアップファイル名を入力: " file && \
		tar -xzf backups/$$file && \
		echo "✅ リストア完了"

# テスト
test:
	pytest tests/ -v

# コードフォーマット
format:
	black src/ tools/
	isort src/ tools/

# コードチェック
lint:
	flake8 src/ tools/
	mypy src/

# 完全デプロイ
deploy: build start
	@echo "🚀 デプロイ完了!"
