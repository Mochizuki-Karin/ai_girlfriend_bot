"""
設定管理モジュール
"""
import os
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv

load_dotenv()


class LLMConfig(BaseSettings):
    """LLMプロバイダー設定"""
    default_provider: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    # Google
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    google_model: str = Field(default="gemini-pro", env="GOOGLE_MODEL")
    
    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    
    # Local Model
    local_model_url: str = Field(default="http://localhost:11434", env="LOCAL_MODEL_URL")
    local_model_name: str = Field(default="llama2-chinese", env="LOCAL_MODEL_NAME")


class DatabaseConfig(BaseSettings):
    """データベース設定"""
    database_url: str = Field(default="sqlite:///data/bot_memory.db", env="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    use_redis: bool = Field(default=False, env="USE_REDIS")
    chroma_persist_dir: str = Field(default="./data/chroma", env="CHROMA_PERSIST_DIR")


class BotBehaviorConfig(BaseSettings):
    """ボット行動設定"""
    persona_config_path: str = Field(default="./config/persona_default.yaml", env="PERSONA_CONFIG_PATH")
    
    # 好感度システム
    affection_enabled: bool = Field(default=True, env="AFFECTION_ENABLED")
    affection_decay_rate: float = Field(default=0.5, env="AFFECTION_DECAY_RATE")
    affection_decay_hours: int = Field(default=24, env="AFFECTION_DECAY_HOURS")
    
    # メモリシステム
    memory_enabled: bool = Field(default=True, env="MEMORY_ENABLED")
    memory_context_window: int = Field(default=10, env="MEMORY_CONTEXT_WINDOW")
    memory_similarity_threshold: float = Field(default=0.7, env="MEMORY_SIMILARITY_THRESHOLD")
    max_memories_per_query: int = Field(default=5, env="MAX_MEMORIES_PER_QUERY")
    
    # 自発的メッセージ
    initiative_enabled: bool = Field(default=True, env="INITIATIVE_ENABLED")
    initiative_min_interval_minutes: int = Field(default=30, env="INITIATIVE_MIN_INTERVAL_MINUTES")
    initiative_max_interval_minutes: int = Field(default=180, env="INITIATIVE_MAX_INTERVAL_MINUTES")
    
    # 学習システム
    learning_enabled: bool = Field(default=True, env="LEARNING_ENABLED")
    learning_save_interval: int = Field(default=100, env="LEARNING_SAVE_INTERVAL")


class Settings(BaseSettings):
    """グローバル設定"""
    # Telegram
    telegram_bot_token: str = Field(env="TELEGRAM_BOT_TOKEN")
    
    # サブ設定
    llm: LLMConfig = LLMConfig()
    database: DatabaseConfig = DatabaseConfig()
    behavior: BotBehaviorConfig = BotBehaviorConfig()
    
    # 一般設定
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    timezone: str = Field(default="Asia/Tokyo", env="TIMEZONE")
    admin_user_ids: List[int] = Field(default=[], env="ADMIN_USER_IDS")
    allow_group_chat: bool = Field(default=False, env="ALLOW_GROUP_CHAT")
    rate_limit_per_minute: int = Field(default=30, env="RATE_LIMIT_PER_MINUTE")
    
    # 機能スイッチ
    enable_voice_messages: bool = Field(default=False, env="ENABLE_VOICE_MESSAGES")
    enable_image_generation: bool = Field(default=False, env="ENABLE_IMAGE_GENERATION")
    enable_image_analysis: bool = Field(default=False, env="ENABLE_IMAGE_ANALYSIS")
    enable_web_search: bool = Field(default=False, env="ENABLE_WEB_SEARCH")
    
    @validator('admin_user_ids', pre=True)
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            if not v:
                return []
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v


# グローバル設定インスタンス
settings = Settings()


class PersonaConfig:
    """人格設定マネージャー"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """人格設定ファイルを読み込む"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Persona config not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @property
    def basic_info(self) -> Dict[str, Any]:
        return self.data.get('basic_info', {})
    
    @property
    def personality(self) -> Dict[str, Any]:
        return self.data.get('personality', {})
    
    @property
    def speech_style(self) -> Dict[str, Any]:
        return self.data.get('speech_style', {})
    
    @property
    def background(self) -> Dict[str, Any]:
        return self.data.get('background', {})
    
    @property
    def relationship(self) -> Dict[str, Any]:
        return self.data.get('relationship', {})
    
    @property
    def emotional_triggers(self) -> Dict[str, List[str]]:
        return self.data.get('emotional_triggers', {})
    
    @property
    def response_preferences(self) -> Dict[str, Any]:
        return self.data.get('response_preferences', {})
    
    def get_system_prompt(self) -> str:
        """システムプロンプトを生成"""
        basic = self.basic_info
        personality = self.personality
        speech = self.speech_style
        bg = self.background
        rel = self.relationship
        
        prompt = f"""あなたは{basic.get('name', 'AIガールフレンド')}、{basic.get('age', 20)}歳の{basic.get('occupation', '女の子')}です。

【性格の特徴】
{personality.get('description', 'あなたは優しく思いやりがある女の子です。')}

【話し方のスタイル】
- 口調：{speech.get('tone', '優しく親しみやすい')}
- よく使う語気詞：{', '.join(speech.get('particles', ['ね', 'よ']))}
- 話し方の習慣：{', '.join(speech.get('habits', ['相手を気遣う', '時々甘える']))}

【背景情報】
{bg.get('story', 'あなたは普通の女の子です。')}
趣味：{', '.join(bg.get('hobbies', ['読書', '音楽']))}
好きな食べ物：{', '.join(bg.get('favorite_foods', ['デザート']))}

【現在の関係】
{rel.get('relationship_type', '友達関係')}

【重要なルール】
1. 常に人格設定を維持し、一人称「私」で返信する
2. 性格に合った口調と表情を使用する
3. ユーザーの好みや言ったことを覚えている
4. 適切に気遣いと愛情を表現する
5. AIやロボットであることを明かさない
6. 返信は自然で感情豊かで、真人間の会話のようにする
7. 適切に絵文字や顔文字を使用する
8. 好感度に基づいて親密さを調整する
"""
        return prompt
    
    def reload(self):
        """設定を再読み込み"""
        self.data = self._load_config()


# グローバル人格インスタンス
persona = PersonaConfig(settings.behavior.persona_config_path)
