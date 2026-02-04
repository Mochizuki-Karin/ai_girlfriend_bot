# AIガールフレンドボット - APIドキュメント

このドキュメントはAIガールフレンドボットの内部APIと拡張インターフェースを紹介します。

## 目次

1. [設定 API](#設定-api)
2. [好感度システム API](#好感度システム-api)
3. [メモリシステム API](#メモリシステム-api)
4. [知識システム API](#知識システム-api)
5. [LLMクライアント API](#llmクライアント-api)
6. [メッセージ生成 API](#メッセージ生成-api)

---

## 設定 API

### PersonaConfig

人格設定マネージャー。

```python
from src.config import PersonaConfig

# 人格を読み込み
persona = PersonaConfig("config/persona_default.yaml")

# 基本情報を取得
name = persona.basic_info['name']  # "さくら"
age = persona.basic_info['age']    # 22

# 性格の説明を取得
description = persona.personality['description']

# 話し方のスタイルを取得
speech_style = persona.speech_style

# システムプロンプトを生成
system_prompt = persona.get_system_prompt()

# 設定を再読み込み
persona.reload()
```

### Settings

グローバル設定。

```python
from src.config import settings

# Telegram設定
token = settings.telegram_bot_token

# LLM設定
llm_provider = settings.llm.default_provider
openai_model = settings.llm.openai_model

# 行動設定
affection_enabled = settings.behavior.affection_enabled
memory_enabled = settings.behavior.memory_enabled
```

---

## 好感度システム API

### AffectionSystem

```python
from src.affection_system import AffectionSystem

# 初期化
affection = AffectionSystem("./data")

# ユーザー状態を取得
state = affection.get_state("user_123")
print(state.score)        # 好感度スコア
print(state.current_mood) # 現在の感情

# 関係レベルを取得
level = affection.get_level("user_123")
# AffectionLevel.FRIEND, AffectionLevel.LOVER, etc.

# 好感度を更新
new_score, feedback = affection.update(
    "user_123",
    action="compliment",  # 褒める
    context={}
)

# メッセージを処理
new_score, feedback, actions = affection.process_message(
    "user_123",
    message="あなたは今日とても綺麗だ",
    response_time_seconds=30
)

# 関係状態を取得
status = affection.get_relationship_status("user_123")
# {
#     'score': 75.5,
#     'level': '片思い',
#     'next_level': '恋人',
#     'progress_to_next': 37.0,
#     'mood': 'happy',
#     'interaction_count': 150
# }

# 感情を設定
affection.set_mood("user_123", "happy", intensity=0.8, reason="プレゼントをもらった")

# 特別イベントを追加
affection.add_special_event("user_123", "first_date", "初めてのデート")

# プロンプト強化のヒントを取得
hint = affection.get_affection_hint_for_prompt("user_123")
```

### AffectionLevel

```python
from src.affection_system import AffectionLevel

# 等級列挙
AffectionLevel.STRANGER      # 0-10
AffectionLevel.ACQUAINTANCE  # 10-30
AffectionLevel.FRIEND        # 30-50
AffectionLevel.CLOSE_FRIEND  # 50-70
AffectionLevel.CRUSH         # 70-85
AffectionLevel.LOVER         # 85-95
AffectionLevel.SOULMATE      # 95-100

# 等級を取得
level = AffectionLevel.get_level(75.5)  # AffectionLevel.CRUSH

# 等級属性
print(level.level_name)  # "見知らぬ人"
print(level.greeting)    # "こんにちは"
```

---

## メモリシステム API

### MemorySystem

```python
from src.memory_system import MemorySystem
import chromadb

# 初期化
chroma_client = chromadb.Client()
memory = MemorySystem(chroma_client, llm_client=None)

# 会話ラウンドを処理
await memory.process_conversation_turn(
    user_id="user_123",
    user_message="私は火鍋が好き",
    bot_response="火鍋は本当に美味しいですね！",
    emotional_context={"mood": "happy"},
    topics=["food", "hotpot"]
)

# コンテキストを取得
context = await memory.get_context_for_response(
    user_id="user_123",
    current_message="今晩何を食べるか",
    include_short_term=True,
    include_long_term=True,
    n_long_term=5
)

# 明示的なメモリを追加
await memory.add_explicit_memory(
    user_id="user_123",
    content="ユーザーの誕生日は3月15日",
    memory_type="fact",
    importance=0.9
)

# ユーザープロファイルを取得
profile = await memory.get_user_profile("user_123")
# {
#     'facts': ['ユーザーが火鍋が好き', 'ユーザーの誕生日は3月15日'],
#     'preferences': ['辛い食べ物が好き'],
#     'events': ['初デート'],
#     'emotions': ['プレゼントを貰ったときに嬉しい']
# }

# メモリを統合
await memory.consolidate("user_123")

# 短期記憶をクリア
memory.clear_short_term("user_123")
```

### ShortTermMemory

```python
from src.memory_system import ShortTermMemory

# 初期化
short_term = ShortTermMemory(max_turns=10)

# 会話ラウンドを追加
short_term.add_turn(
    user_id="user_123",
    user_message="こんにちは",
    bot_response="こんにちは～",
    emotional_context={},
    topics=["greeting"]
)

# 最近のコンテキストを取得
turns = short_term.get_recent_context("user_123", n_turns=5)

# フォーマットされたコンテキスト文字列を取得
context = short_term.get_context_string("user_123", n_turns=5)

# 議論されたトピックを取得
topics = short_term.get_topics("user_123", n_turns=10)
```

### LongTermMemory

```python
from src.memory_system import LongTermMemory, Memory

# 初期化
long_term = LongTermMemory(chroma_client)

# メモリを追加
memory = Memory(
    id="mem_123",
    content="ユーザーが猫が好き",
    memory_type="preference",
    importance=0.8,
    user_id="user_123"
)
await long_term.add_memory(memory)

# バッチ追加
await long_term.add_memories([memory1, memory2, memory3])

# 関連するメモリを検索
memories = await long_term.retrieve_relevant(
    query="ペット",
    user_id="user_123",
    n_results=5,
    memory_types=["preference", "fact"],
    min_importance=0.5
)

# ユーザーのすべてのメモリを取得
all_memories = await long_term.get_user_memories(
    user_id="user_123",
    memory_types=["fact"]
)

# メモリを削除
await long_term.delete_memory("mem_123")
```

---

## 知識システム API

### KnowledgeSystem

```python
from src.knowledge_system import KnowledgeSystem

# 初期化
knowledge = KnowledgeSystem(
    chroma_client=chroma_client,
    llm_client=llm_client,
    knowledge_base_path="./data/knowledge",
    persona_config_path="./config/persona_default.yaml"
)

# 知識をインポートして学習
result = await knowledge.import_and_learn(
    source="./docs/about_user.txt",
    source_type="file",  # file, directory, text
    category="personal"
)
# {
#     'imported_count': 10,
#     'insights_count': 5,
#     'insights_by_type': {'preference': 3, 'fact': 2}
# }

# 強化されたコンテキストを取得
context = await knowledge.get_enhanced_context("ユーザーのメッセージ")

# 対話から学習
insights_count = await knowledge.learn_from_conversation(
    user_message="私は青が好き",
    bot_response="青は綺麗ですね",
    user_id="user_123"
)

# 学習サマリーを取得
summary = knowledge.get_learning_summary()
# {
#     'total_facts': 15,
#     'total_preferences': 8,
#     'total_patterns': 3,
#     'total_emotional_rules': 2
# }
```

### KnowledgeImporter

```python
from src.knowledge_system import KnowledgeImporter

importer = KnowledgeImporter("./data/knowledge")

# ファイルをインポート
items = await importer.import_file(
    file_path="./docs/info.txt",
    category="general"
)

# ディレクトリをインポート
items = await importer.import_directory(
    dir_path="./knowledge_files",
    category="personal"
)

# テキストをインポート
item = await importer.import_text(
    text="ユーザーの誕生日は3月15日",
    source="manual_input",
    category="personal"
)
```

### KnowledgeLearner

```python
from src.knowledge_system import KnowledgeLearner

learner = KnowledgeLearner(llm_client)

# 知識から学習
insights = await learner.learn_from_knowledge(items)

# LLMを使用して深層学習
deep_insights = await learner.deep_learn_with_llm(items)
```

### KnowledgeIntegrator

```python
from src.knowledge_system import KnowledgeIntegrator

integrator = KnowledgeIntegrator("./config/persona_default.yaml")

# 洞察を personality に統合
await integrator.integrate_insights(insights)

# 強化されたシステムプロンプトを取得
enhanced_prompt = integrator.get_enhanced_system_prompt(base_prompt)
```

### KnowledgeRetriever

```python
from src.knowledge_system import KnowledgeRetriever

retriever = KnowledgeRetriever(chroma_client)

# 知識をベクトルデータベースに追加
await retriever.add_knowledge(items)

# 関連する知識を検索
items = await retriever.retrieve_relevant(
    query="ユーザーの好み",
    n_results=5,
    min_similarity=0.5
)

# 対話コンテキストを取得
context = await retriever.get_context_for_conversation(
    user_message="何が好きですか",
    conversation_history=[]
)
```

---

## LLM クライアント API

### LLMClientManager

```python
from src.llm_client import create_llm_manager, LLMConfig

# 設定から作成
llm_manager = create_llm_manager(settings)

# 新しいクライアントを登録
llm_manager.register_client(
    name="custom",
    client=CustomLLMClient(config),
    is_default=False
)

# クライアントを取得
client = llm_manager.get_client("openai")

# テキストを生成
response = await llm_manager.generate(
    prompt="こんにちは",
    provider="openai",
    system_prompt="あなたはアシスタントです",
    temperature=0.7,
    max_tokens=500
)
print(response.content)
print(response.usage)

# 対話生成
response = await llm_manager.chat(
    messages=[
        {"role": "system", "content": "あなたはアシスタントです"},
        {"role": "user", "content": "こんにちは"}
    ],
    provider="openai"
)

# すべてのクライアントを閉じる
await llm_manager.close_all()
```

### ストリーミング生成

```python
# ストリーミング生成
async for chunk in client.generate_stream(
    prompt="物語を語って",
    system_prompt="あなたは物語を語る人です"
):
    print(chunk, end="")

# ストリーミング対話
async for chunk in client.chat_stream(messages):
    print(chunk, end="")
```

### カスタム LLM クライアント

```python
from src.llm_client import BaseLLMClient, LLMResponse, LLMConfig

class CustomLLMClient(BaseLLMClient):
    async def generate(self, prompt, system_prompt=None, **kwargs):
        # 生成ロジックを実装
        content = await self._call_api(prompt, system_prompt)
        
        return LLMResponse(
            content=content,
            model=self.config.model,
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            finish_reason="stop"
        )
    
    async def generate_stream(self, prompt, system_prompt=None, **kwargs):
        # ストリーミング生成を実装
        async for chunk in self._call_streaming_api(prompt):
            yield chunk
    
    async def chat(self, messages, **kwargs):
        # 対話生成を実装
        pass

# 登録
config = LLMConfig(provider="custom", api_key="xxx", model="custom-model")
llm_manager.register_client("custom", CustomLLMClient(config))
```

---

## メッセージ生成 API

### MessageGenerator

```python
from src.message_generator import MessageGenerator

generator = MessageGenerator(
    llm_manager=llm_manager,
    affection_system=affection_system,
    memory_system=memory_system,
    knowledge_system=knowledge_system
)

# レスポンスを生成
response, new_affection = await generator.generate_response(
    user_id="user_123",
    user_message="今日はどうだった",
    provider="openai"
)

# 主動メッセージを生成
initiative_msg = await generator.generate_initiative_message(
    user_id="user_123",
    provider="openai"
)

# 主動メッセージを送るべきか判断
should_initiate = generator.should_initiate("user_123")

# タイピングパラメータを取得
typing_params = generator.get_typing_params(
    user_id="user_123",
    message="これはメッセージです"
)
# {
#     'speed': 'normal',
#     'thinking_time': 'medium',
#     'duration': 3.5
# }

# 音声メッセージテキストを生成
voice_text = await generator.generate_voice_message_text(
    user_id="user_123",
    emotion="happy"
)
```

### ResponseStyler

```python
from src.message_generator import ResponseStyler
from src.affection_system import AffectionLevel

# 語気詞を追加
styled = ResponseStyler.add_particles("あなたは今日どうだった", frequency=0.5)
# "あなたは今日どうだったね"

# 絵文字を追加
styled = ResponseStyler.add_emojis("今日の天気は良い", frequency=0.5)
# "今日の天気は良い😊"

# 完全なスタイルを適用
styled = ResponseStyler.apply_style(
    text="会いたい",
    affection_level=AffectionLevel.LOVER
)
# "会いたい🥰～"
```

---

## イベントフック

### カスタムイベント処理

```python
from src.bot import bot

# メッセージ前処理フックを登録
async def before_message_hook(user_id, message):
    print(f"メッセージ受信: {message}")
    return message

bot.register_hook("before_message", before_message_hook)

# メッセージ後処理フックを登録
async def after_message_hook(user_id, response):
    print(f"返信送信: {response}")
    
bot.register_hook("after_message", after_message_hook)
```

---

## 拡張開発

### カスタムコマンドを作成

```python
from telegram import Update
from telegram.ext import ContextTypes

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """カスタムコマンド"""
    user_id = update.effective_user.id
    
    # ユーザーデータを取得
    state = bot.affection_system.get_state(str(user_id))
    
    # レスポンスを送信
    await update.message.reply_text(f"あなたの好感度: {state.score}")

# コマンドを登録
bot.application.add_handler(CommandHandler("custom", custom_command))
```

### カスタム人格プラグインを作成

```python
class CustomPersonalityPlugin:
    """カスタム人格プラグイン"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def modify_system_prompt(self, base_prompt: str) -> str:
        """システムプロンプトを修正"""
        return base_prompt + "\n\n追加指示：..."
    
    def on_message(self, user_id: str, message: str):
        """メッセージ処理フック"""
        pass
    
    def on_response(self, user_id: str, response: str) -> str:
        """レスポンス処理フック"""
        return response

# プラグインを登録
plugin = CustomPersonalityPlugin(bot)
bot.register_plugin(plugin)
```

---

## より多くの例

`examples/` ディレクトリでより多くの使用例を確認してください。

---

**Happy Coding!** 🤖💕
