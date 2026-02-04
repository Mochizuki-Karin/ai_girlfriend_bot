#!/usr/bin/env python3
"""
プラグイン開発の例
カスタムプラグインでボット機能を拡張する方法を示す
"""
import sys
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class PluginContext:
    """プラグインコンテキスト"""
    user_id: str
    message: str
    timestamp: datetime
    metadata: Dict[str, Any]


class BasePlugin:
    """プラグイン基底クラス"""
    
    name: str = "base_plugin"
    version: str = "1.0.0"
    description: str = "Base plugin class"
    
    def __init__(self, bot=None):
        self.bot = bot
        self.enabled = True
    
    async def on_load(self):
        """プラグイン読み込み時に呼び出し"""
        print(f"Plugin {self.name} loaded")
    
    async def on_unload(self):
        """プラグインアンロード時に呼び出し"""
        print(f"Plugin {self.name} unloaded")
    
    async def before_message(self, context: PluginContext) -> str:
        """メッセージ処理前に呼び出し"""
        return context.message
    
    async def after_message(self, context: PluginContext, response: str) -> str:
        """メッセージ処理後に呼び出し"""
        return response
    
    async def on_command(self, command: str, args: List[str], user_id: str) -> str:
        """コマンド処理"""
        return None


class MorningGreetingPlugin(BasePlugin):
    """朝の挨拶プラグイン"""
    
    name = "morning_greeting"
    description = "時間に基づいて異なる朝の挨拶を送信"
    
    GREETINGS = {
        "early": ["随分早いですね！偉いです☀️", "おはよう～今日も頑張りましょう"],
        "normal": ["おはよう～よく眠れましたか？", "おはよう！今日は何か予定がありますか？"],
        "late": ["やっと起きたんですね～お sleepy pig 🐷", "おはよう！昼まで寝るかと思ってました"]
    }
    
    async def before_message(self, context: PluginContext) -> str:
        """朝の挨拶メッセージをチェック"""
        message = context.message.lower()
        
        if any(word in message for word in ["おはよう", "おはよ", "早"]):
            hour = context.timestamp.hour
            
            if hour < 7:
                greeting_type = "early"
            elif hour < 10:
                greeting_type = "normal"
            else:
                greeting_type = "late"
            
            import random
            greeting = random.choice(self.GREETINGS[greeting_type])
            
            # メッセージを変更またはタグを追加可能
            context.metadata['morning_greeting'] = greeting
        
        return context.message


class AffectionBoostPlugin(BasePlugin):
    """好感度ブーストプラグイン"""
    
    name = "affection_boost"
    description = "特定キーワードで好感度ブーストをトリガー"
    
    BOOST_WORDS = {
        "褒め言葉": ["可愛い", "美人", "賢い", "優しい", "親切"],
        "気遣い": ["体に気をつけて", "無理しないで", "ちゃんと食べて", "早めに寝て"],
        "親密": ["会いたい", "好き", "愛してる", "ハグして"]
    }
    
    async def after_message(self, context: PluginContext, response: str) -> str:
        """メッセージ内のキーワードをチェック"""
        message = context.message
        
        for category, words in self.BOOST_WORDS.items():
            if any(word in message for word in words):
                # 好感度を増加
                if self.bot and hasattr(self.bot, 'affection_system'):
                    self.bot.affection_system.update(
                        context.user_id,
                        action=f"{category}_bonus",
                        context={"boost": 1.5}
                    )
                
                # 返信にフィードバックを追加
                if category == "褒め言葉":
                    response += "\n（そう言ってくれて嬉しそう～）"
                elif category == "気遣い":
                    response += "\n（優しくてありがとう～）"
                
                break
        
        return response


class CustomCommandPlugin(BasePlugin):
    """カスタムコマンドプラグイン"""
    
    name = "custom_commands"
    description = "カスタムコマンドを追加"
    
    COMMANDS = {
        "joke": "ジョークを言う",
        "weather": "天気を調べる",
        "mood": "気持ちを確認",
        "hug": "ハグする"
    }
    
    async def on_command(self, command: str, args: List[str], user_id: str) -> str:
        """カスタムコマンドを処理"""
        
        if command == "joke":
            jokes = [
                "なぜプログラマーはクリスマスとハロウィンを混同するのか？ 31 OCT = 25 DEC だから",
                "プログラマーが最も嫌う4つのこと：1. コメントを書く 2. ドキュメントを書く 3. 他人がコメントを書かない 4. 他人がドキュメントを書かない",
                "あるプログラマーがバーに入り、手を挙げて言った：「ビールを1杯ください。」 バーテンが尋ねた：「1杯ですか？2杯ですか？」 プログラマーは「1杯です」と答え、2本の指を立てた。"
            ]
            import random
            return random.choice(jokes)
        
        elif command == "hug":
            hugs = [
                "大きなハグをプレゼント！🤗",
                "ハグ～全部大丈夫になるよ💕",
                "（ぎゅっと抱きしめる）ちゃんといるよ～"
            ]
            import random
            return random.choice(hugs)
        
        elif command == "mood":
            if self.bot and hasattr(self.bot, 'affection_system'):
                state = self.bot.affection_system.get_state(user_id)
                moods = {
                    "happy": "😊 今日は気持ちいいね！",
                    "sad": "😢 少し悲しい...",
                    "neutral": "😐 まあまあかな",
                    "excited": "🤩 超 excited ！"
                }
                return moods.get(state.current_mood, "😊 気持ちいいね～")
            return "😊 気持ちいいね～"
        
        return None


class MemoryReminderPlugin(BasePlugin):
    """メモリーリマインダープラグイン"""
    
    name = "memory_reminder"
    description = "重要なメモリーをリマインド"
    
    async def before_message(self, context: PluginContext) -> str:
        """メモリーがトリガーされたかチェック"""
        message = context.message
        
        # 関連トピックが言及されているかチェック
        trigger_words = {
            "誕生日": "user_birthday",
            "猫": "user_pet",
            "仕事": "user_job",
            "家": "user_home"
        }
        
        for word, memory_key in trigger_words.items():
            if word in message:
                # ここでメモリーをコンテキストに追加可能
                context.metadata['triggered_memory'] = memory_key
        
        return message


class PluginManager:
    """プラグインマネージャー"""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.plugins: List[BasePlugin] = []
    
    def register(self, plugin: BasePlugin):
        """プラグインを登録"""
        plugin.bot = self.bot
        self.plugins.append(plugin)
        print(f"✅ プラグイン登録: {plugin.name}")
    
    def unregister(self, plugin_name: str):
        """プラグインを登録解除"""
        self.plugins = [p for p in self.plugins if p.name != plugin_name]
        print(f"❌ プラグイン登録解除: {plugin_name}")
    
    async def process_before_message(self, context: PluginContext) -> str:
        """メッセージ処理前フック"""
        message = context.message
        
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    message = await plugin.before_message(context)
                    context.message = message
                except Exception as e:
                    print(f"Plugin {plugin.name} error: {e}")
        
        return message
    
    async def process_after_message(self, context: PluginContext, response: str) -> str:
        """メッセージ処理後フック"""
        
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    response = await plugin.after_message(context, response)
                except Exception as e:
                    print(f"Plugin {plugin.name} error: {e}")
        
        return response
    
    async def process_command(self, command: str, args: List[str], user_id: str) -> str:
        """コマンド処理"""
        
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    result = await plugin.on_command(command, args, user_id)
                    if result:
                        return result
                except Exception as e:
                    print(f"Plugin {plugin.name} error: {e}")
        
        return None
    
    def list_plugins(self) -> List[Dict[str, str]]:
        """すべてのプラグインをリスト"""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "enabled": p.enabled
            }
            for p in self.plugins
        ]


def example_usage():
    """使用例"""
    
    # プラグインマネージャーを作成
    manager = PluginManager(bot=None)
    
    # プラグインを登録
    manager.register(MorningGreetingPlugin())
    manager.register(AffectionBoostPlugin())
    manager.register(CustomCommandPlugin())
    manager.register(MemoryReminderPlugin())
    
    print("\n📋 登録済みプラグイン:")
    for plugin_info in manager.list_plugins():
        status = "✅" if plugin_info["enabled"] else "❌"
        print(f"  {status} {plugin_info['name']} - {plugin_info['description']}")
    
    return manager


if __name__ == "__main__":
    print("=" * 60)
    print("🔌 プラグイン開発の例")
    print("=" * 60)
    
    # 例を実行
    manager = example_usage()
    
    print("\n" + "=" * 60)
    print("✅ 例の完了！")
    print("=" * 60)
    print("\n💡 ヒント:")
    print("  - BasePlugin を継承して新しいプラグインを作成")
    print("  - 必要なメソッドをオーバーライド")
    print("  - PluginManager を使用してプラグインを管理")
    print("  - プラグインはメッセージと返信を変更可能")
