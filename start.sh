#!/bin/bash

# AIガールフレンドボット起動スクリプト

set -e

# 色の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║              AIガールフレンドボット - 仮想彼女ロボット        ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# .envファイルを確認
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .envファイルが存在しません、テンプレートから作成しています...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}APIキーを設定するために.envファイルを編集してください${NC}"
    exit 1
fi

# Dockerを確認
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Dockerがインストールされていません。Dockerをインストールしてください${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Composeがインストールされていません。Docker Composeをインストールしてください${NC}"
    exit 1
fi

# 必要なディレクトリを作成
echo -e "${BLUE}📁 データディレクトリを作成中...${NC}"
mkdir -p data logs

# メニュー
echo ""
echo "起動方法を選択してください："
echo ""
echo "1) 🐳 Docker Compose (推奨)"
echo "2) 🐳 Docker Compose + Redis"
echo "3) 🐳 Docker Compose + Ollama (ローカルモデル)"
echo "4) 🐍 ローカル Python 実行"
echo "5) 🛠️  ツールメニュー"
echo "6) ❌ 終了"
echo ""
read -p "選択 [1-6]: " choice

case $choice in
    1)
        echo -e "${GREEN}🚀 Docker Composeで起動中...${NC}"
        docker-compose up -d
        echo ""
        echo -e "${GREEN}✅ サービスが起動しました！${NC}"
        echo ""
        echo "ログを確認: docker-compose logs -f"
        echo "サービスを停止: docker-compose down"
        ;;
    
    2)
        echo -e "${GREEN}🚀 Docker Compose + Redisで起動中...${NC}"
        docker-compose --profile with-redis up -d
        echo ""
        echo -e "${GREEN}✅ サービスが起動しました（Redis含む）！${NC}"
        echo ""
        echo "ログを確認: docker-compose logs -f"
        echo "サービスを停止: docker-compose --profile with-redis down"
        ;;
    
    3)
        echo -e "${GREEN}🚀 Docker Compose + Ollamaで起動中...${NC}"
        docker-compose --profile with-ollama up -d
        echo ""
        echo -e "${GREEN}✅ サービスが起動しました（Ollama含む）！${NC}"
        echo ""
        echo "ログを確認: docker-compose logs -f"
        echo "サービスを停止: docker-compose --profile with-ollama down"
        echo ""
        echo -e "${YELLOW}💡 ヒント：初回使用時はモデルをダウンロードしてください${NC}"
        echo "   docker-compose exec ollama ollama pull llama2-chinese"
        ;;
    
    4)
        echo -e "${GREEN}🐍 ローカル Python で実行中...${NC}"
        
        # 仮想環境を確認
        if [ ! -d "venv" ]; then
            echo -e "${BLUE}📦 仮想環境を作成中...${NC}"
            python3 -m venv venv
        fi
        
        # 仮想環境を有効化
        source venv/bin/activate
        
        # 依存関係をインストール
        echo -e "${BLUE}📦 依存関係をインストール中...${NC}"
        pip install -q -r requirements.txt
        
        # 実行
        echo -e "${GREEN}🚀 ロボットを起動中...${NC}"
        python -m src.bot
        ;;
    
    5)
        echo ""
        echo "🛠️  ツールメニュー"
        echo ""
        echo "1) 🎭 キャラクター編集器"
        echo "2) 📚 知識インポート"
        echo "3) 📊 統計を表示"
        echo "4) 🧹 データをクリーン"
        echo "5) 🔙 メインメニューに戻る"
        echo ""
        read -p "選択 [1-5]: " tool_choice
        
        case $tool_choice in
            1)
                python tools/persona_editor.py
                ;;
            2)
                echo ""
                echo "知識インポートツール"
                echo "使い方: python tools/knowledge_importer.py [file|dir|text|stats] <パラメータ>"
                echo ""
                read -p "コマンドを入力（例: file docs/about.txt）: " import_cmd
                python tools/knowledge_importer.py $import_cmd
                ;;
            3)
                python tools/knowledge_importer.py stats
                ;;
            4)
                echo -e "${RED}⚠️  全てのデータが削除されます！${NC}"
                read -p "クリーンアップを確認? [y/N]: " confirm
                if [[ $confirm == [yY] ]]; then
                    rm -rf data/* logs/*
                    echo -e "${GREEN}✅ データがクリーンされました${NC}"
                fi
                ;;
            5)
                exec $0
                ;;
        esac
        ;;
    
    6)
        echo -e "${GREEN}👋 さようなら！${NC}"
        exit 0
        ;;
    
    *)
        echo -e "${RED}❌ 無効な選択${NC}"
        exit 1
        ;;
esac
