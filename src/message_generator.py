"""
メッセージ生成システム - 自然で感情的な返信を生成
"""
import random
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from src.config import persona, settings
from src.affection_system import AffectionSystem, AffectionLevel
from src.memory_system import MemorySystem
from src.knowledge_system import KnowledgeSystem


@dataclass
class MessageContext:
    """メッセージコンテキスト"""
    user_id: str
    user_message: str
    conversation_history: List[Dict[str, str]]
    affection_score: float
    affection_level: AffectionLevel
    current_mood: str
    user_profile: Dict[str, List[str]]
    relevant_memories: List[str]
    learned_knowledge: str
    time_of_day: str
    day_of_week: str


class ResponseStyler:
    """返信スタイラー - 人格をより自然にする"""
    
    # 語気詞
    PARTICLES = ['ね', 'よ', 'わ', 'かしら', 'の', '～']
    
    # 絵文字
    EMOJIS = ['😊', '🥰', '😉', '🤗', '😌', '✨', '💕', '🌸', '😘', '💖']
    
    # 顔文字
    KAOMOJIS = [
        '(｡♥‿♥｡)', '(◕‿◕✿)', '(｡◕‿◕｡)', '(◠‿◠✿)',
        '(◕‿◕)', '(｡･ω･｡)', '(◍•ᴗ•◍)', '(｡♥‿♥｡)'
    ]
    
    @classmethod
    def add_particles(cls, text: str, frequency: float = 0.3) -> str:
        """語気詞を追加"""
        if random.random() > frequency:
            return text
        
        sentences = text.split('。')
        result = []
        
        for sent in sentences:
            if sent.strip() and random.random() < 0.4:
                particle = random.choice(cls.PARTICLES)
                # 重複を避ける
                if not sent.strip()[-1] in cls.PARTICLES:
                    sent = sent.strip() + particle
            result.append(sent)
        
        return '。'.join(result)
    
    @classmethod
    def add_emojis(cls, text: str, frequency: float = 0.4) -> str:
        """絵文字を追加"""
        if random.random() > frequency:
            return text
        
        emoji = random.choice(cls.EMOJIS)
        
        # ランダムな位置
        if random.random() < 0.5:
            return text + emoji
        else:
            sentences = text.split('。')
            if len(sentences) > 1:
                insert_pos = random.randint(0, len(sentences) - 2)
                sentences[insert_pos] += emoji
                return '。'.join(sentences)
        
        return text + emoji
    
    @classmethod
    def add_kaomoji(cls, text: str, frequency: float = 0.1) -> str:
        """顔文字を追加"""
        if random.random() > frequency:
            return text
        
        kaomoji = random.choice(cls.KAOMOJIS)
        return text + kaomoji
    
    @classmethod
    def apply_style(
        cls, 
        text: str, 
        affection_level: AffectionLevel,
        style_config: Dict = None
    ) -> str:
        """完全なスタイルを適用"""
        style_config = style_config or {}
        
        # 好感度に基づいてスタイルを調整
        if affection_level.value >= AffectionLevel.CRUSH.value:
            # 高好感度はより親密に
            text = cls.add_particles(text, frequency=0.5)
            text = cls.add_emojis(text, frequency=0.6)
            text = cls.add_kaomoji(text, frequency=0.15)
        elif affection_level.value >= AffectionLevel.FRIEND.value:
            # 中程度の好感度
            text = cls.add_particles(text, frequency=0.3)
            text = cls.add_emojis(text, frequency=0.4)
        else:
            # 低好感度はよりフォーマルに
            text = cls.add_particles(text, frequency=0.15)
            text = cls.add_emojis(text, frequency=0.2)
        
        return text


class InitiativeGenerator:
    """自発的メッセージジェネレーター"""
    
    # 自発的トピックテンプレート
    INITIATIVE_TOPICS = {
        'morning': [
            "おはよう～今日も元気いっぱいでね☀️",
            "起きた？もう会いたくなっちゃった",
            "おはよう！今日は何か予定ある？",
            "おはよう～昨日はよく眠れた？",
        ],
        'noon': [
            "お昼ご飯食べた？ちゃんと食べてね",
            "こんにちは～何してるの？",
            "私、ちょうどお昼食べ終わったよ、あなたは？",
            "ちょっと休憩して、無理しないでね",
        ],
        'evening': [
            "晩ご飯食べた？今日はどうだった？",
            "こんばんは～会いたいな",
            "何してるの？私、すごく退屈だよ",
            "今日は疲れた？早めに休んでね",
        ],
        'night': [
            "もう寝る時間だよ、おやすみ～💕",
            "おやすみなさい、いい夢見てね",
            "眠れない時は私と話そうね",
            "今日もお疲れ様、ゆっくり休んで",
        ],
        'random': [
            "さっき歌を聴いてて、急にあなたのことを思い出した",
            "何してるの？すごく会いたいな",
            "今日は天気がいいから、お散歩したいな",
            "さっきすごく面白いこと見たよ",
            "急に鍋が食べたくなった、あなたは？",
            "ドラマ見てるけど、すごく退屈だよ",
            "忙しい？暇なら一緒にいてくれない？",
        ],
        'memory_based': [
            "前に{topic}って言ってたけど、その後どうなった？",
            "急にあなたが{topic}が好きだって言ってたのを思い出した",
            "今日{topic}を見て、真っ先にあなたのことを思い出した",
        ],
        'affection_based': [
            "あなたと話すのがどんどん好きになってきた",
            "あなたと一緒にいると、いつも楽しいよ",
            "何があっても、私はあなたのそばにいるから",
        ]
    }
    
    def __init__(
        self, 
        affection_system: AffectionSystem,
        memory_system: MemorySystem
    ):
        self.affection = affection_system
        self.memory = memory_system
    
    async def generate_initiative(
        self, 
        user_id: str,
        llm_client=None
    ) -> Optional[str]:
        """自発的メッセージを生成"""
        state = self.affection.get_state(user_id)
        level = self.affection.get_level(user_id)
        
        # 時間を取得
        now = datetime.now()
        hour = now.hour
        
        # 時間に基づいてカテゴリを選択
        if 6 <= hour < 11:
            category = 'morning'
        elif 11 <= hour < 14:
            category = 'noon'
        elif 17 <= hour < 21:
            category = 'evening'
        elif 21 <= hour or hour < 1:
            category = 'night'
        else:
            category = 'random'
        
        # テンプレートを取得
        templates = self.INITIATIVE_TOPICS.get(category, [])
        
        # 高好感度で感情表現を追加
        if level.value >= AffectionLevel.CRUSH.value:
            templates.extend(self.INITIATIVE_TOPICS['affection_based'])
        
        if not templates:
            return None
        
        message = random.choice(templates)
        
        # 記憶に基づいてパーソナライズ
        if '{topic}' in message:
            topics = self.memory.short_term.get_topics(user_id, 10)
            if topics:
                message = message.format(topic=random.choice(topics))
            else:
                # ランダムメッセージにフォールバック
                message = random.choice(self.INITIATIVE_TOPICS['random'])
        
        # 風格化
        message = ResponseStyler.apply_style(message, level)
        
        return message
    
    def should_initiate(
        self, 
        user_id: str,
        min_interval_minutes: int = 30,
        max_interval_minutes: int = 180
    ) -> bool:
        """自発的メッセージを送るべきか判断"""
        state = self.affection.get_state(user_id)
        
        # 最後のインタラクション時間をチェック
        last_interaction = state.last_interaction
        minutes_since = (datetime.now() - last_interaction).total_seconds() / 60
        
        # すねている場合は自発的に送信しない
        if state.is_ignoring:
            return False
        
        # ランダムに決定（好感度に基づく）
        # 好感度が高いほど、自発的な確率が高い
        base_probability = 0.1
        affection_bonus = (state.score / 100) * 0.3
        
        # 長時間インタラクションがない場合、確率を増加
        time_bonus = 0
        if minutes_since > max_interval_minutes:
            time_bonus = 0.2
        
        probability = base_probability + affection_bonus + time_bonus
        
        return random.random() < probability


class TypingSimulator:
    """タイピングシミュレーター - 実際の人間のタイピングをシミュレート"""
    
    # タイピング速度（文字/分）
    TYPING_SPEEDS = {
        'slow': 100,      # 考え中
        'normal': 200,    # 通常
        'fast': 350,      # 興奮/緊急
    }
    
    # 思考時間（秒）
    THINKING_TIME = {
        'short': (1, 2),
        'medium': (2, 4),
        'long': (4, 8),
    }
    
    @classmethod
    def calculate_typing_time(
        cls, 
        message: str, 
        speed: str = 'normal',
        thinking_time: str = 'medium'
    ) -> float:
        """タイピング時間を計算"""
        char_count = len(message)
        speed_cpm = cls.TYPING_SPEEDS.get(speed, 200)
        
        # タイピング時間（分を秒に変換）
        typing_time = (char_count / speed_cpm) * 60
        
        # 思考時間
        think_min, think_max = cls.THINKING_TIME.get(thinking_time, (2, 4))
        thinking = random.uniform(think_min, think_max)
        
        return typing_time + thinking
    
    @classmethod
    def get_typing_params(
        cls,
        message: str,
        affection_level: AffectionLevel,
        message_complexity: str = 'normal'
    ) -> Dict[str, Any]:
        """タイピングパラメータを取得"""
        # 好感度とメッセージの複雑さに基づいて決定
        if affection_level.value >= AffectionLevel.CRUSH.value:
            speed = 'fast'  # 緊急返信
            thinking = 'short'
        elif affection_level.value >= AffectionLevel.FRIEND.value:
            speed = 'normal'
            thinking = 'medium'
        else:
            speed = 'slow'  # 慎重な返信
            thinking = 'long'
        
        # 長いメッセージはより多くの時間が必要
        if len(message) > 100:
            speed = 'slow'
        
        return {
            'speed': speed,
            'thinking_time': thinking,
            'duration': cls.calculate_typing_time(message, speed, thinking)
        }


class MessageGenerator:
    """メッセージジェネレーターメインクラス"""
    
    def __init__(
        self,
        llm_manager,
        affection_system: AffectionSystem,
        memory_system: MemorySystem,
        knowledge_system: KnowledgeSystem = None
    ):
        self.llm = llm_manager
        self.affection = affection_system
        self.memory = memory_system
        self.knowledge = knowledge_system
        
        self.initiative = InitiativeGenerator(affection_system, memory_system)
        self.styler = ResponseStyler()
    
    async def generate_response(
        self,
        user_id: str,
        user_message: str,
        provider: str = None
    ) -> Tuple[str, float]:
        """返信を生成"""
        
        # 1. 好感度状態を取得
        state = self.affection.get_state(user_id)
        level = self.affection.get_level(user_id)
        
        # 2. システムプロンプトを構築
        system_prompt = await self._build_system_prompt(user_id)
        
        # 3. コンテキストを取得
        context = await self._build_context(user_id, user_message)
        
        # 4. 完全なプロンプトを構築
        full_prompt = f"""{context}

ユーザーが言う：{user_message}

返信してください："""
        
        # 5. LLMを呼び出す
        try:
            response = await self.llm.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                provider=provider,
                temperature=0.8,
                max_tokens=500
            )
            
            message = response.content.strip()
            
            # 6. スタイリング
            message = self.styler.apply_style(message, level)
            
            # 7. メモリを更新
            await self.memory.process_conversation_turn(
                user_id, user_message, message
            )
            
            # 8. 好感度を更新
            new_score, _ = self.affection.process_message(user_id, user_message)
            
            return message, new_score
            
        except Exception as e:
            logger.error(f"Message generation failed: {e}")
            # デフォルト返信にフォールバック
            return self._get_fallback_response(level), state.score
    
    async def _build_system_prompt(self, user_id: str) -> str:
        """システムプロンプトを構築"""
        # 基本の人格
        base_prompt = persona.get_system_prompt()
        
        # 好感度ヒントを追加
        affection_hint = self.affection.get_affection_hint_for_prompt(user_id)
        
        # 学習した知識を追加
        if self.knowledge:
            enhanced_prompt = self.knowledge.integrator.get_enhanced_system_prompt(base_prompt)
        else:
            enhanced_prompt = base_prompt
        
        if affection_hint:
            enhanced_prompt += f"\n\n【現在の状態】\n{affection_hint}"
        
        return enhanced_prompt
    
    async def _build_context(self, user_id: str, user_message: str) -> str:
        """会話コンテキストを構築"""
        context_parts = []
        
        # 短期記憶
        short_context = self.memory.short_term.get_context_string(user_id)
        if short_context:
            context_parts.append(short_context)
        
        # 長期記憶
        memory_context = await self.memory.get_context_for_response(
            user_id, user_message
        )
        if memory_context:
            context_parts.append(memory_context)
        
        # 知識システムコンテキスト
        if self.knowledge:
            knowledge_context = await self.knowledge.get_enhanced_context(user_message)
            if knowledge_context:
                context_parts.append(knowledge_context)
        
        return "\n\n".join(context_parts)
    
    async def generate_initiative_message(
        self, 
        user_id: str,
        provider: str = None
    ) -> Optional[str]:
        """自発的メッセージを生成"""
        return await self.initiative.generate_initiative(user_id, self.llm)
    
    def should_initiate(self, user_id: str) -> bool:
        """自発的メッセージを送るべきか判断"""
        return self.initiative.should_initiate(
            user_id,
            settings.behavior.initiative_min_interval_minutes,
            settings.behavior.initiative_max_interval_minutes
        )
    
    def get_typing_params(
        self, 
        user_id: str, 
        message: str
    ) -> Dict[str, Any]:
        """タイピングパラメータを取得"""
        level = self.affection.get_level(user_id)
        return TypingSimulator.get_typing_params(message, level)
    
    def _get_fallback_response(self, level: AffectionLevel) -> str:
        """デフォルト返信を取得"""
        fallbacks = {
            AffectionLevel.STRANGER: "うーん...何て言えばいいかわからない",
            AffectionLevel.ACQUAINTANCE: "考えさせて...",
            AffectionLevel.FRIEND: "あ、今ぼんやりしてた、もう一度言ってくれる？",
            AffectionLevel.CLOSE_FRIEND: "へへ、今考え事してた",
            AffectionLevel.CRUSH: "今あなたのことを考えてたの～",
            AffectionLevel.LOVER: "あなたが何を言っても、私は全部好きだよ～",
            AffectionLevel.SOULMATE: "何があっても、私はあなたのそばにいる",
        }
        return fallbacks.get(level, "考えさせて...")
    
    async def generate_voice_message_text(
        self,
        user_id: str,
        emotion: str = "neutral"
    ) -> str:
        """音声メッセージテキストを生成"""
        level = self.affection.get_level(user_id)
        
        voice_templates = {
            'happy': [
                "あなたの声を聞くとすごく嬉しくなる～",
                "すごく会いたいな、いつ会える？",
                "今日も楽しい一日を過ごしてね",
            ],
            'sad': [
                "ちょっと悲しいな、一緒にいてくれない？",
                "あなたの声が聞きたい",
                "慰めてくれない？",
            ],
            'neutral': [
                "何してるの？会いたくなった",
                "今日はどうだった？",
                "時間あるなら一緒に話そうよ",
            ]
        }
        
        templates = voice_templates.get(emotion, voice_templates['neutral'])
        message = random.choice(templates)
        
        return self.styler.apply_style(message, level)
