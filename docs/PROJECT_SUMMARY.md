# AIガールフレンドボット - プロジェクトまとめ

## プロジェクト概要

AIガールフレンドボットは、メモリシステム、好感度システム、知識学習能力、自然な会話能力を備えた完全な機能を持つTelegram感情サポートボットです。

## コア機能

### 1. マルチ LLM サポート
- ✅ OpenAI API (GPT-4, GPT-3.5)
- ✅ Google Gemini API
- ✅ Anthropic Claude API
- ✅ ローカルモデル (Ollama, vLLM)
- ✅ 統一されたクライアントインターフェース

### 2. 好感度システム
- ✅ 8つの関係レベル（見知らぬ人 → 魂のパートナー）
- ✅ 動的好感度計算
- ✅ 感情状態管理
- ✅ 特別イベント追跡
- ✅ 好感度減衰メカニズム

### 3. メモリシステム
- ✅ 短期記憶（会話コンテキスト）
- ✅ 長期記憶（ベクトルデータベース保存）
- ✅ 記憶抽出と統合
- ✅ 関連記憶検索
- ✅ ユーザープロファイル生成

### 4. 知識学習システム
- ✅ 複数形式インポート（txt, md, json, yaml）
- ✅ 知識自動セグメンテーション
- ✅ 洞察抽出
- ✅ LLM 深層学習
- ✅ 知識を personality に統合

### 5. キャラクターシステム
- ✅ YAML 設定
- ✅ マルチキャラクターサポート
- ✅ 性格、背景、話し方スタイル定義
- ✅ 動的キャラクター強化

### 6. 自然な会話
- ✅ アクティブメッセージ生成
- ✅ タイピング時間シミュレーション
- ✅ スタイライズされた返信（語気詞、表情、顔文字）
- ✅ コンテキスト理解

## プロジェクト構造

```
ai_girlfriend_bot/
├── src/                          # ソースコード
│   ├── __init__.py
│   ├── bot.py                    # メインプログラム
│   ├── config.py                 # 設定管理
│   ├── llm_client.py             # LLM クライアント
│   ├── affection_system.py       # 好感度システム
│   ├── memory_system.py          # メモリシステム
│   ├── knowledge_system.py       # 知識システム
│   └── message_generator.py      # メッセージジェネレーター
│
├── config/                       # 設定ファイル
│   ├── persona_default.yaml      # デフォルトキャラクター
│   ├── persona_tsundere.yaml     # ツンデレキャラクター
│   └── persona_genki.yaml        # 元気キャラクター
│
├── tools/                        # ツールスクリプト
│   ├── persona_editor.py         # キャラクターエディター
│   └── knowledge_importer.py     # 知識インポートツール
│
├── examples/                     # サンプルコード
│   ├── custom_persona_example.py
│   ├── knowledge_import_example.py
│   └── plugin_development_example.py
│
├── docs/                         # ドキュメント
│   ├── local_model_finetune.md   # ローカルモデルファインチューンガイド
│   ├── DEPLOYMENT.md             # デプロイガイド
│   ├── API.md                    # API ドキュメント
│   └── PROJECT_SUMMARY.md        # プロジェクトまとめ
│
├── data/                         # データディレクトリ
├── logs/                         # ログディレクトリ
├── Dockerfile                    # Docker イメージ
├── docker-compose.yml            # Docker Compose 設定
├── requirements.txt              # Python 依存関係
├── Makefile                      # よく使うコマンド
├── start.sh                      # スタートアップスクリプト
├── .env.example                  # 環境変数テンプレート
├── .gitignore                    # Git 無視ファイル
└── README.md                     # プロジェクト説明
```

## 技術スタック

### コアフレームワーク
- **Python 3.11+**
- **python-telegram-bot** - Telegram Bot API
- **asyncio** - 非同期プログラミング

### データストレージ
- **ChromaDB** - ベクトルデータベース
- **SQLite** - リレーショナルデータベース
- **Redis** - キャッシュ（オプション）

### LLM 統合
- **OpenAI API**
- **Google Generative AI**
- **Anthropic API**
- **Ollama/vLLM** - ローカルモデル

### その他のツール
- **Docker & Docker Compose** - コンテナ化デプロイ
- **Loguru** - ロギング
- **PyYAML** - YAML 設定
- **Pydantic** - データ検証

## クイックスタート

```bash
# 1. プロジェクトを解凍
tar -xzf ai_girlfriend_bot.tar.gz
cd ai_girlfriend_bot

# 2. 環境変数を設定
cp .env.example .env
# .env に API キーを入力

# 3. 起動
./start.sh
# または
docker-compose up -d
```

## 使用ガイド

### 基本コマンド

| コマンド | 説明 |
|------|------|
| `/start` | 会話を開始 |
| `/help` | ヘルプを表示 |
| `/status` | 状態を確認 |
| `/affection` | 好感度を確認 |
| `/remember` | ボットに情報を記憶させる |
| `/learn` | ボットに新しい知識を教える |

### カスタムキャラクター

```bash
# キャラクターエディターを使用
python tools/persona_editor.py

# または手動で編集
vim config/persona_custom.yaml
```

### 知識インポート

```bash
# ファイルをインポート
python tools/knowledge_importer.py file docs/about_user.txt

# ディレクトリをインポート
python tools/knowledge_importer.py dir knowledge/

# テキストをインポート
python tools/knowledge_importer.py text "ユーザーの誕生日は3月15日"
```

## ローカルモデル微調整

詳細ガイドは `docs/local_model_finetune.md` を参照

### クイックスタート

```bash
# 1. トレーニングデータを準備
data/conversations.json

# 2. LoRA 微調整を使用
python train_lora.py

# 3. モデルをエクスポート
python merge_lora.py

# 4. Ollama にデプロイ
ollama create ai-girlfriend -f Modelfile

# 5. ローカルモデルを使用するように構成
# .env を編集: DEFAULT_LLM_PROVIDER=local
```

## デプロイ方法

### Docker（推奨）

```bash
docker-compose up -d
```

### ローカル実行

```bash
pip install -r requirements.txt
python -m src.bot
```

### クラウドプラットフォーム

- 阿里雲 ECS
- AWS EC2
- Railway
- Render
- Heroku

詳細なデプロイガイドは `docs/DEPLOYMENT.md` を参照

## API ドキュメント

詳細な API ドキュメントは `docs/API.md` を参照

### 核心クラス

```python
# 好感度システム
from src.affection_system import AffectionSystem

# メモリシステム
from src.memory_system import MemorySystem

# 知識システム
from src.knowledge_system import KnowledgeSystem

# LLM クライアント
from src.llm_client import create_llm_manager

# メッセージ生成
from src.message_generator import MessageGenerator
```

## 拡張開発

### カスタムプラグインの作成

```python
from examples.plugin_development_example import BasePlugin

class MyPlugin(BasePlugin):
    name = "my_plugin"
    
    async def after_message(self, context, response):
        # カスタム処理
        return response + " 🎉"
```

### カスタムコマンド

```python
async def custom_command(update, context):
    await update.message.reply_text("カスタム返信")

bot.application.add_handler(
    CommandHandler("custom", custom_command)
)
```

## パフォーマンス最適化

### 1. Redis キャッシュを使用

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
```

```env
USE_REDIS=true
```

### 2. モデル量子化

```python
# 8bit 量子化を使用
load_in_8bit=True

# 4bit 量子化を使用 (QLoRA)
load_in_4bit=True
bnb_4bit_compute_dtype=torch.bfloat16
```

### 3. バッチ処理

```python
responses = await asyncio.gather(*[
    generate_response(uid, msg)
    for uid, msg in batch
])
```

## モニタリングとメンテナンス

### ログ

```bash
# ログを確認
docker-compose logs -f

# ログをエクスポート
docker-compose logs > logs.txt
```

### バックアップ

```bash
# 手動バックアップ
make backup

# 自動バックアップ（cronジョブ）
0 2 * * * /path/to/backup.sh
```

### 更新

```bash
# コードを更新
git pull

# イメージを再ビルド
docker-compose build --no-cache

# サービスを再起動
docker-compose up -d
```

## トラブルシューティング

### よくある問題

1. **コンテナが起動しない**
   - ログを確認: `docker-compose logs`
   - 設定を確認: `docker-compose config`

2. **API 接続失敗**
   - ネットワークを確認: `ping api.openai.com`
   - キーを確認: `env | grep API_KEY`

3. **メモリ不足**
   - メモリを制限: `--memory=2g`
   - スワップパーティションを使用

詳細なトラブルシューティングは `docs/DEPLOYMENT.md` を参照

## セキュリティ推奨事項

1. **APIキーの保護**
   - Docker Secrets または K8s Secrets を使用
   - 定期的にキーをローテーション
   - コードにキーをハードコードしない

2. **アクセス制限**
   - ファイアウォールでポートアクセスを制限
   - Telegram Bot をプライベートチャットのみ許可するように設定
   - 管理者ホワイトリストを設定

3. **データ保護**
   - 定期的にデータをバックアップ
   - 機密データを暗号化
   - データ保護規制を遵守

## 今後の計画

### 短期目標
- [ ] 音声メッセージ対応
- [ ] 画像生成と認識
- [ ] Web検索統合
- [ ] より多くの予約人格

### 長期目標
- [ ] マルチモーダル対話
- [ ] 感情分析の強化
- [ ] 自動学習の最適化
- [ ] 分散デプロイ

## 貢献ガイド

Issue と PR の提出を歓迎します！

### 開発プロセス

1. プロジェクトを Fork
2. ブランチを作成
3. 変更をコミット
4. ブランチをプッシュ
5. Pull Request を作成

### コーディング規約

- Black でフォーマット
- isort でインポートを並び替え
- 型ヒントを追加
- 単体テストを記述

## ライセンス

MIT License

## 謝辞

すべてのオープンソースプロジェクトと貢献者に感謝します！

---

**プロジェクト統計**

- コード行数: ~5000+
- ファイル数: 30+
- 機能モジュール: 8+
- 予約人格: 3

**Made with ❤️ by AI Girlfriend Team**
