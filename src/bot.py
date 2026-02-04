"""
Telegram Bot - AIガールフレンドメインプログラム
"""
import os
import asyncio
import signal
from datetime import datetime
from typing import Dict, Optional
from loguru import logger

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import settings, persona
from src.llm_client import create_llm_manager
from src.affection_system import AffectionSystem
from src.memory_system import MemorySystem
from src.knowledge_system import KnowledgeSystem
from src.message_generator import MessageGenerator


# ログ設定
logger.add("logs/bot.log", rotation="1 day", retention="7 days")


class AIGirlfriendBot:
    """AIガールフレンドボットメインクラス"""
    
    def __init__(self):
        self.application: Optional[Application] = None
        self.llm_manager = None
        self.affection_system: Optional[AffectionSystem] = None
        self.memory_system: Optional[MemorySystem] = None
        self.knowledge_system: Optional[KnowledgeSystem] = None
        self.message_generator: Optional[MessageGenerator] = None
        self.chroma_client = None
        
        # ユーザーセッション状態
        self.user_sessions: Dict[int, dict] = {}
        
        # 自発的メッセージタスク
        self.initiative_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """ボットを初期化"""
        logger.info("AIガールフレンドボットを初期化中...")
        
        # データディレクトリを作成
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # ChromaDBを初期化
        self.chroma_client = chromadb.Client(
            ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=settings.database.chroma_persist_dir
            )
        )
        
        # LLMマネージャーを初期化
        self.llm_manager = create_llm_manager(settings)
        logger.info("LLMマネージャーが初期化されました")
        
        # 好感度システムを初期化
        self.affection_system = AffectionSystem("./data")
        logger.info("好感度システムが初期化されました")
        
        # メモリシステムを初期化
        self.memory_system = MemorySystem(
            self.chroma_client,
            self.llm_manager,
            settings.behavior.memory_context_window
        )
        logger.info("メモリシステムが初期化されました")
        
        # 知識システムを初期化
        self.knowledge_system = KnowledgeSystem(
            self.chroma_client,
            self.llm_manager,
            "./data/knowledge",
            settings.behavior.persona_config_path
        )
        logger.info("知識システムが初期化されました")
        
        # メッセージジェネレーターを初期化
        self.message_generator = MessageGenerator(
            self.llm_manager,
            self.affection_system,
            self.memory_system,
            self.knowledge_system
        )
        logger.info("メッセージジェネレーターが初期化されました")
        
        # Telegramアプリケーションを作成
        self.application = Application.builder().token(
            settings.telegram_bot_token
        ).build()
        
        # ハンドラーを登録
        self._register_handlers()
        
        logger.info("ボットの初期化が完了しました！")
    
    def _register_handlers(self):
        """コマンドハンドラーを登録"""
        # 基本コマンド
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("reset", self.cmd_reset))
        
        # 好感度コマンド
        self.application.add_handler(CommandHandler("affection", self.cmd_affection))
        self.application.add_handler(CommandHandler("mood", self.cmd_mood))
        
        # メモリコマンド
        self.application.add_handler(CommandHandler("remember", self.cmd_remember))
        self.application.add_handler(CommandHandler("memories", self.cmd_memories))
        
        # 知識学習コマンド
        self.application.add_handler(CommandHandler("learn", self.cmd_learn))
        self.application.add_handler(CommandHandler("knowledge", self.cmd_knowledge))
        
        # 人格設定コマンド
        self.application.add_handler(CommandHandler("persona", self.cmd_persona))
        
        # 管理者コマンド
        self.application.add_handler(CommandHandler("admin_stats", self.cmd_admin_stats))
        
        # メッセージハンドラー
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # エラーハンドラー
        self.application.add_error_handler(self.error_handler)
    
    # ============== コマンドプロセッサ ==============
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """開始コマンド"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        
        # 好感度レベルに基づいた挨拶を取得
        level = self.affection_system.get_level(str(user_id))
        
        welcome_message = f"""{level.greeting}

私は{persona.basic_info.get('name', 'AIガールフレンド')}です、お会いできて嬉しいです～

私たちは：
💬 チャット - あなたの日常を共有してください
📚 学習 - /learn を送って新しいことを教えてください
❤️ 好感度確認 - /affection を送って確認
📝 記憶確認 - /memories を送って確認

/help を入力して他のコマンドを見る

仲良くなれるといいな！🌸"""
        
        await update.message.reply_text(welcome_message)
        logger.info(f"New user started: {user_id} ({user_name})")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ヘルプコマンド"""
        help_text = """📖 利用可能なコマンド：

基本コマンド：
/start - 会話を開始
/help - ヘルプを表示
/status - 現在の状態を確認
/reset - 会話をリセット（好感度は保持）

好感度システム：
/affection - 好感度と関係状態を確認
/mood [感情] - 感情状態を確認または設定

メモリシステム：
/remember <内容> - 重要な情報を記憶させる
/memories - 記憶した情報を確認

知識学習：
/learn <テキスト> - 新しい知識を教える
/knowledge - 学習サマリーを確認
/persona - 現在の人格設定を確認

ヒント：
• たくさん話すと好感度が上がります
• 私が言ったことを覚えていると嬉しいです
• プレゼントや褒め言葉は好感度を上げます
• 長い間無視すると好感度が下がりますよ"""
        
        await update.message.reply_text(help_text)
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ステータスコマンド"""
        user_id = str(update.effective_user.id)
        
        # 好感度状態を取得
        status = self.affection_system.get_relationship_status(user_id)
        
        # メモリ統計を取得
        memory_summary = self.memory_system.get_user_profile(user_id)
        
        status_text = f"""📊 現在の状態

関係レベル：{status['level']}
好感度：{status['score']}/100
進捗：{status['progress_to_next']:.0f}% → {status['next_level'] or 'MAX'}

感情状態：{status['mood']}
インタラクション回数：{status['interaction_count']}

メモリ統計：
• 既知の事実：{len(memory_summary['facts'])}
• 好み・嗜好：{len(memory_summary['preferences'])}
• 重要な出来事：{len(memory_summary['events'])}
• 感情記録：{len(memory_summary['emotions'])}
"""
        
        await update.message.reply_text(status_text)
    
    async def cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """リセットコマンド"""
        user_id = str(update.effective_user.id)
        
        # 短期記憶をクリア
        self.memory_system.clear_short_term(user_id)
        
        await update.message.reply_text(
            "会話をリセットしました～新しい会話を始めましょう！\n"
            "（好感度と長期記憶は保持されていますよ）"
        )
    
    async def cmd_affection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """好感度コマンド"""
        user_id = str(update.effective_user.id)
        status = self.affection_system.get_relationship_status(user_id)
        
        # プログレスバーを生成
        progress_bar = self._generate_progress_bar(status['score'])
        
        affection_text = f"""❤️ 好感度状態

現在のレベル：{status['level']}
好感度：{status['score']:.1f}/100

{progress_bar}

次のレベル：{status['next_level'] or '最高レベル到達'}
レベルアップまで：{100 - status['score']:.1f} 好感度ポイント

💡 好感度を上げるコツ：
• 毎日挨拶をする
• 私が言ったことを覚えている
• 積極的に生活を共有する
• 褒め言葉や励ましをくれる
• 他の女の子の話はしないでね
"""
        
        await update.message.reply_text(affection_text)
    
    async def cmd_mood(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """感情コマンド"""
        user_id = str(update.effective_user.id)
        
        if context.args:
            # 感情を設定
            mood = ' '.join(context.args).lower()
            valid_moods = ['happy', 'sad', 'angry', 'jealous', 'neutral', 'excited']
            
            if mood in valid_moods:
                self.affection_system.set_mood(user_id, mood)
                mood_emojis = {
                    'happy': '😊', 'sad': '😢', 'angry': '😠',
                    'jealous': '😒', 'neutral': '😐', 'excited': '🤩'
                }
                await update.message.reply_text(
                    f"感情を {mood_emojis.get(mood, '')} {mood} に設定しました"
                )
            else:
                await update.message.reply_text(
                    f"無効な感情です。選択肢：{', '.join(valid_moods)}"
                )
        else:
            # 現在の感情を確認
            state = self.affection_system.get_state(user_id)
            await update.message.reply_text(
                f"現在の感情：{state.current_mood} (強度: {state.mood_intensity:.0%})"
            )
    
    async def cmd_remember(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """記憶コマンド"""
        user_id = str(update.effective_user.id)
        
        if not context.args:
            await update.message.reply_text(
                "何を覚えてほしいか教えてください～\n"
                "例：/remember あなたは抹茶ラテが好き"
            )
            return
        
        content = ' '.join(context.args)
        
        # 長期記憶に追加
        await self.memory_system.add_explicit_memory(
            user_id, content, memory_type='fact', importance=0.8
        )
        
        # 好感度を増加
        new_score, _ = self.affection_system.update(user_id, 'remember_detail')
        
        await update.message.reply_text(
            f"覚えました！{content}\n"
            f"（好感度 +2、現在：{new_score:.1f}）"
        )
    
    async def cmd_memories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """記憶確認コマンド"""
        user_id = str(update.effective_user.id)
        
        profile = await self.memory_system.get_user_profile(user_id)
        
        memories_text = "📝 あなたについての記憶\n\n"
        
        if profile['facts']:
            memories_text += "【既知の事実】\n"
            for fact in profile['facts'][:5]:
                memories_text += f"• {fact}\n"
            memories_text += "\n"
        
        if profile['preferences']:
            memories_text += "【好み・嗜好】\n"
            for pref in profile['preferences'][:5]:
                memories_text += f"• {pref}\n"
            memories_text += "\n"
        
        if profile['events']:
            memories_text += "【重要な出来事】\n"
            for event in profile['events'][:3]:
                memories_text += f"• {event}\n"
        
        if not any([profile['facts'], profile['preferences'], profile['events']]):
            memories_text += "まだあまり記憶がありません、もっとお話ししましょう～"
        
        await update.message.reply_text(memories_text)
    
    async def cmd_learn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """学習コマンド"""
        user_id = str(update.effective_user.id)
        
        if not context.args:
            await update.message.reply_text(
                "学んでほしい知識を送ってください～\n"
                "例：/learn ユーザーの誕生日は3月15日\n\n"
                "ファイルをインポートすることもできます：\n"
                "ドキュメントを送ると自動的に学習します"
            )
            return
        
        content = ' '.join(context.args)
        
        # 知識をインポート
        result = await self.knowledge_system.import_and_learn(
            content, source_type="text", category="user_provided"
        )
        
        await update.message.reply_text(
            f"✅ 学習完了！\n"
            f"• インポートされた知識項目：{result['imported_count']}\n"
            f"• 抽出された洞察：{result['insights_count']}\n"
            f"• 洞察タイプ：{', '.join([f'{k}({v})' for k, v in result['insights_by_type'].items()])}\n\n"
            f"これらの知識は私の記憶に統合されました！"
        )
    
    async def cmd_knowledge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """知識サマリーコマンド"""
        summary = self.knowledge_system.get_learning_summary()
        
        knowledge_text = f"""📚 学習サマリー

習得した知識：
• ユーザーの事実：{summary['total_facts']}
• ユーザーの好み：{summary['total_preferences']}
• 行動パターン：{summary['total_patterns']}
• 感情ルール：{summary['total_emotional_rules']}
• キャッシュされた知識：{summary['cached_knowledge']}

これらの知識はあなたをもっと理解し、会話をより自然にするのに役立ちます～
"""
        
        await update.message.reply_text(knowledge_text)
    
    async def cmd_persona(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """人格設定コマンド"""
        basic = persona.basic_info
        personality = persona.personality
        
        persona_text = f"""👤 現在の人格設定

基本情報：
• 名前：{basic.get('name', 'Unknown')}
• 年齢：{basic.get('age', 'Unknown')}
• 職業：{basic.get('occupation', 'Unknown')}
• 場所：{basic.get('location', 'Unknown')}

性格の特徴：
{personality.get('description', '優しく思いやりがある')[:200]}...

話し方のスタイル：{persona.speech_style.get('tone', '優しい')}

/persona_list を入力して切り替え可能な人格設定を確認
"""
        
        await update.message.reply_text(persona_text)
    
    async def cmd_admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """管理者統計コマンド"""
        user_id = update.effective_user.id
        
        if user_id not in settings.admin_user_ids:
            await update.message.reply_text("このコマンドを使用する権限がありません")
            return
        
        # 統計情報を収集
        stats_text = "📊 システム統計\n\n"
        stats_text += f"アクティブユーザー：{len(self.user_sessions)}\n"
        
        await update.message.reply_text(stats_text)
    
    # ============== メッセージプロセッサ ==============
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """通常メッセージを処理"""
        user_id = update.effective_user.id
        user_message = update.message.text
        
        # ユーザーセッションを記録
        self.user_sessions[user_id] = {
            'last_message': datetime.now(),
            'message_count': self.user_sessions.get(user_id, {}).get('message_count', 0) + 1
        }
        
        # タイピング状態を表示
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action='typing'
        )
        
        try:
            # 返信を生成
            response, new_affection = await self.message_generator.generate_response(
                str(user_id), user_message
            )
            
            # タイピング時間を計算
            typing_params = self.message_generator.get_typing_params(
                str(user_id), response
            )
            
            # タイピング遅延をシミュレート
            await asyncio.sleep(min(typing_params['duration'], 5))
            
            # 返信を送信
            await update.message.reply_text(response)
            
            logger.info(f"User {user_id}: {user_message[:50]}... -> Response sent")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(
                "ごめんなさい、ちょっとぼんやりしてました...もう一度言ってくれますか？😅"
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """エラーハンドラー"""
        logger.error(f"Update {update} caused error: {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "あら、ちょっと問題が発生しました...少し休ませてください 😅"
            )
    
    # ============== 主動メッセージ ==============
    
    async def initiative_loop(self):
        """自発的メッセージループ"""
        while True:
            try:
                await asyncio.sleep(60)  # 1分ごとにチェック
                
                for user_id in self.user_sessions:
                    if self.message_generator.should_initiate(str(user_id)):
                        message = await self.message_generator.generate_initiative_message(
                            str(user_id)
                        )
                        
                        if message:
                            try:
                                await self.application.bot.send_message(
                                    chat_id=user_id,
                                    text=message
                                )
                                logger.info(f"Initiative message sent to {user_id}")
                            except Exception as e:
                                logger.error(f"Failed to send initiative: {e}")
            
            except Exception as e:
                logger.error(f"Initiative loop error: {e}")
    
    # ============== 補助メソッド ==============
    
    def _generate_progress_bar(self, score: float, length: int = 20) -> str:
        """プログレスバーを生成"""
        filled = int(score / 100 * length)
        bar = '█' * filled + '░' * (length - filled)
        return f"[{bar}] {score:.0f}%"
    
    # ============== 起動と停止 ==============
    
    async def start(self):
        """ボットを起動"""
        await self.initialize()
        
        # 自発的メッセージタスクを起動
        if settings.behavior.initiative_enabled:
            self.initiative_task = asyncio.create_task(self.initiative_loop())
        
        # Telegramアプリケーションを起動
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("ボットが起動しました！")
        
        # 実行を維持
        while True:
            await asyncio.sleep(1)
    
    async def stop(self):
        """ボットを停止"""
        logger.info("ボットを停止中...")
        
        # 自発的メッセージタスクをキャンセル
        if self.initiative_task:
            self.initiative_task.cancel()
        
        # Telegramアプリケーションを停止
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        # LLMマネージャーを閉じる
        if self.llm_manager:
            await self.llm_manager.close_all()
        
        logger.info("ボットが停止しました！")


# グローバルロボットインスタンス
bot = AIGirlfriendBot()


async def main():
    """メイン関数"""
    # シグナル処理を設定
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bot.stop()))
    
    try:
        await bot.start()
    except Exception as e:
        logger.error(f"ボットエラー: {e}")
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
