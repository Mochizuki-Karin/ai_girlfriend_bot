"""
好感度システム - AIガールフレンドのユーザーへの好感度を管理
"""
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import asyncio
from loguru import logger


class AffectionLevel(Enum):
    """好感度レベル"""
    STRANGER = (0, 10, "見知らぬ人", "こんにちは、あなたは誰ですか？")
    ACQUAINTANCE = (10, 30, "知り合い", "やあ、最近どう？")
    FRIEND = (30, 50, "友達", "今日は何を話そうか？")
    CLOSE_FRIEND = (50, 70, "親友", "ちょうどあなたのことを考えていたところだよ～")
    CRUSH = (70, 85, "片思い", "あなたと話すのは本当に楽しいです")
    LOVER = (85, 95, "恋人", "会いたくなっちゃった、何してるの？")
    SOULMATE = (95, 100, "ソウルメイト", "何があっても、私はあなたのそばにいるよ")
    
    def __init__(self, min_val: int, max_val: int, name: str, greeting: str):
        self.min_val = min_val
        self.max_val = max_val
        self.level_name = name
        self.greeting = greeting
    
    @classmethod
    def get_level(cls, score: float) -> 'AffectionLevel':
        """スコアに基づいてレベルを取得"""
        for level in cls:
            if level.min_val <= score < level.max_val:
                return level
        return cls.SOULMATE if score >= 100 else cls.STRANGER


@dataclass
class AffectionState:
    """好感度状態"""
    user_id: str
    score: float = 20.0  # 初期好感度
    last_interaction: datetime = field(default_factory=datetime.now)
    interaction_count: int = 0
    consecutive_positive: int = 0
    consecutive_negative: int = 0
    
    # 感情状態
    current_mood: str = "neutral"  # happy, sad, angry, jealous, neutral
    mood_intensity: float = 0.5  # 0-1
    mood_reason: str = ""
    
    # 特別マーク
    is_ignoring: bool = False  # すねているかどうか
    ignore_until: Optional[datetime] = None
    special_events: List[Dict] = field(default_factory=list)
    
    # 統計データ
    total_messages: int = 0
    positive_interactions: int = 0
    negative_interactions: int = 0
    gifts_received: int = 0
    dates_had: int = 0


class AffectionCalculator:
    """好感度計算機"""
    
    # 基礎スコア
    BASE_MESSAGE = 0.1
    
    # ポジティブなインタラクション
    POSITIVE_FACTORS = {
        'compliment': 2.0,      # 褒める
        'gift': 5.0,            # プレゼントを贈る
        'remember_detail': 3.0,  # 詳細を覚える
        'share_feeling': 1.5,   # 感情を共有する
        'ask_about_day': 1.0,   # 日常を気遣う
        'good_morning_night': 1.5,  # 朝晩の挨拶
        'initiate_conversation': 1.0,  # 会話を自発的に開始する
        'quick_response': 0.5,    # 迅速な返信
        'long_conversation': 2.0, # 長い会話
        'use_nickname': 1.0,     # ニックネームを使用する
        'apologize': 2.0,        # 謝る
        'keep_promise': 3.0,     # 約束を守る
    }
    
    # ネガティブなインタラクション
    NEGATIVE_FACTORS = {
        'ignore': -3.0,          # 無視する
        'forget_important': -4.0, # 重要なことを忘れる
        'mention_other_girl': -5.0,  # 他の女の子について言及する
        'rude': -5.0,            # 失礼な態度
        'lie': -8.0,             # 嘘をつく
        'break_promise': -6.0,   # 約束を破る
        'late_response_hours': -0.5,  # 返信が遅い（1時間ごと）
        'one_word_reply': -0.5,  # 一言返信
        'insult': -10.0,         # 侮辱する
        'pressure': -3.0,        # 圧力をかける
    }
    
    # 減衰設定
    DECAY_RATE = 0.3  # 毎日減衰
    DECAY_THRESHOLD_DAYS = 2  # 2日以上インタラクションがないと減衰開始
    
    @classmethod
    def calculate_change(
        cls, 
        action: str, 
        current_score: float,
        context: Dict = None
    ) -> float:
        """好感度の変化を計算"""
        context = context or {}
        change = 0.0
        
        # ポジティブ要因
        if action in cls.POSITIVE_FACTORS:
            change = cls.POSITIVE_FACTORS[action]
            
            # 好感度が高い場合、ポジティブ行動の利益は逓減する
            if current_score > 80:
                change *= 0.7
            elif current_score > 60:
                change *= 0.85
            
            # 連続ポジティブインタラクションのボーナス
            consecutive = context.get('consecutive_positive', 0)
            if consecutive > 3:
                change *= 1.2
        
        # ネガティブ要因
        elif action in cls.NEGATIVE_FACTORS:
            change = cls.NEGATIVE_FACTORS[action]
            
            # 好感度が低い場合、ネガティブ行動のペナルティが強化される
            if current_score < 30:
                change *= 1.3
            
            # 連続ネガティブインタラクションのペナルティ強化
            consecutive = context.get('consecutive_negative', 0)
            if consecutive > 2:
                change *= 1.3
        
        # 減衰計算
        elif action == 'decay':
            days_inactive = context.get('days_inactive', 0)
            if days_inactive >= cls.DECAY_THRESHOLD_DAYS:
                change = -cls.DECAY_RATE * (days_inactive - cls.DECAY_THRESHOLD_DAYS + 1)
        
        # 0-100の範囲内であることを確認
        new_score = max(0, min(100, current_score + change))
        actual_change = new_score - current_score
        
        return actual_change
    
    @classmethod
    def analyze_message_sentiment(
        cls, 
        message: str, 
        conversation_context: List[str] = None
    ) -> Tuple[str, float]:
        """メッセージの感情傾向を分析"""
        message = message.lower()
        
        # ポジティブキーワード
        positive_words = [
            '綺麗', '可愛い', '賢い', '優しい', '親切', '好き', '愛', '想', '良い',
            '素晴らしい', '優秀', 'すごい', 'ありがとう', '感謝', '嬉しい', '幸せ', '素敵',
            'miss', 'love', 'like', 'beautiful', 'cute', 'smart', 'thanks',
            'happy', 'glad', 'wonderful', 'amazing', 'great', 'good'
        ]
        
        # ネガティブキーワード
        negative_words = [
            '醜い', 'バカ', '馬鹿', '嫌い', '憎い', '出て行け', 'うるさい', '悪い', 'ダメ',
            '愚か', 'つまらない', '気持ち悪い', '失望', '怒り', '憤り', '悲しい',
            'hate', 'stupid', 'ugly', 'boring', 'annoying', 'bad',
            'terrible', 'awful', 'disappointed', 'angry'
        ]
        
        # 特別トリガーワード
        other_girl_words = ['他の女の子', '別の女の子', '彼女', '元カノ', 'ex', 'other girl']
        
        positive_count = sum(1 for word in positive_words if word in message)
        negative_count = sum(1 for word in negative_words if word in message)
        other_girl_count = sum(1 for word in other_girl_words if word in message)
        
        # 特定の行動を検出
        if other_girl_count > 0:
            return 'mention_other_girl', -5.0
        
        if positive_count > negative_count:
            return 'compliment', min(2.0, positive_count * 0.5)
        elif negative_count > positive_count:
            return 'rude', max(-5.0, -negative_count * 1.0)
        
        return 'neutral', 0.0


class AffectionSystem:
    """好感度システムメインクラス"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.states_file = self.data_dir / "affection_states.json"
        
        self._states: Dict[str, AffectionState] = {}
        self._load_states()
    
    def _load_states(self):
        """状態を読み込む"""
        if self.states_file.exists():
            try:
                with open(self.states_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id, state_data in data.items():
                        # 日付文字列を変換
                        state_data['last_interaction'] = datetime.fromisoformat(
                            state_data['last_interaction']
                        )
                        if state_data.get('ignore_until'):
                            state_data['ignore_until'] = datetime.fromisoformat(
                                state_data['ignore_until']
                            )
                        self._states[user_id] = AffectionState(**state_data)
            except Exception as e:
                logger.error(f"Failed to load affection states: {e}")
    
    def _save_states(self):
        """状態を保存"""
        try:
            data = {}
            for user_id, state in self._states.items():
                state_dict = asdict(state)
                # 日付を文字列に変換
                state_dict['last_interaction'] = state.last_interaction.isoformat()
                if state.ignore_until:
                    state_dict['ignore_until'] = state.ignore_until.isoformat()
                data[user_id] = state_dict
            
            with open(self.states_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save affection states: {e}")
    
    def get_state(self, user_id: str) -> AffectionState:
        """ユーザーの好感度状態を取得"""
        if user_id not in self._states:
            self._states[user_id] = AffectionState(user_id=user_id)
        return self._states[user_id]
    
    def get_level(self, user_id: str) -> AffectionLevel:
        """現在のレベルを取得"""
        state = self.get_state(user_id)
        return AffectionLevel.get_level(state.score)
    
    def update(
        self, 
        user_id: str, 
        action: str, 
        context: Dict = None
    ) -> Tuple[float, str]:
        """好感度を更新"""
        state = self.get_state(user_id)
        context = context or {}
        
        # すねているかどうかをチェック
        if state.is_ignoring and state.ignore_until:
            if datetime.now() < state.ignore_until:
                return state.score, f"まだ怒ってる...（残り{(state.ignore_until - datetime.now()).seconds // 60}分）"
            else:
                state.is_ignoring = False
                state.ignore_until = None
        
        # 変化を計算
        context['consecutive_positive'] = state.consecutive_positive
        context['consecutive_negative'] = state.consecutive_negative
        
        change = AffectionCalculator.calculate_change(
            action, state.score, context
        )
        
        old_score = state.score
        state.score = max(0, min(100, state.score + change))
        state.last_interaction = datetime.now()
        state.interaction_count += 1
        state.total_messages += 1
        
        # 連続カウントを更新
        if change > 0:
            state.consecutive_positive += 1
            state.consecutive_negative = 0
            state.positive_interactions += 1
        elif change < 0:
            state.consecutive_negative += 1
            state.consecutive_positive = 0
            state.negative_interactions += 1
            
            # 深刻なネガティブ行動がすねる状態をトリガー
            if change <= -5 and state.score < 50:
                state.is_ignoring = True
                state.ignore_until = datetime.now() + timedelta(minutes=30)
        
        # 保存
        self._save_states()
        
        # フィードバックを生成
        feedback = self._generate_feedback(old_score, state.score, action)
        
        return state.score, feedback
    
    def process_message(
        self, 
        user_id: str, 
        message: str,
        response_time_seconds: float = None
    ) -> Tuple[float, str, List[str]]:
        """ユーザーメッセージを処理し、感情を分析して好感度を更新"""
        state = self.get_state(user_id)
        triggered_actions = []
        
        # メッセージの感情を分析
        sentiment_action, sentiment_score = AffectionCalculator.analyze_message_sentiment(message)
        
        if sentiment_action != 'neutral':
            triggered_actions.append(sentiment_action)
        
        # 朝晩の挨拶を検出
        hour = datetime.now().hour
        if 'おはよう' in message or 'お早う' in message:
            if 5 <= hour <= 10:
                triggered_actions.append('good_morning_night')
        elif 'おやすみ' in message or 'お休み' in message:
            if 20 <= hour <= 24:
                triggered_actions.append('good_morning_night')
        
        # 返信速度を検出
        if response_time_seconds and response_time_seconds < 60:
            triggered_actions.append('quick_response')
        
        # トリガーされたすべてのアクションを適用
        total_change = 0
        for action in triggered_actions:
            new_score, _ = self.update(user_id, action)
            total_change = new_score - state.score
        
        # 基本メッセージ好感度
        if not triggered_actions:
            self.update(user_id, 'base_message')
        
        # 減衰をチェック
        self._apply_decay(user_id)
        
        # フィードバックプロンプトを生成
        feedback = self._generate_interaction_feedback(state, triggered_actions)
        
        return state.score, feedback, triggered_actions
    
    def _apply_decay(self, user_id: str):
        """好感度減衰を適用"""
        state = self.get_state(user_id)
        days_inactive = (datetime.now() - state.last_interaction).days
        
        if days_inactive >= AffectionCalculator.DECAY_THRESHOLD_DAYS:
            self.update(user_id, 'decay', {'days_inactive': days_inactive})
    
    def _generate_feedback(
        self, 
        old_score: float, 
        new_score: float, 
        action: str
    ) -> str:
        """好感度変化のフィードバックを生成"""
        change = new_score - old_score
        
        if change > 3:
            return "好感度が大幅に上昇！"
        elif change > 1:
            return "好感度が上がった～"
        elif change > 0:
            return "好感度が少し上昇"
        elif change < -3:
            return "好感度が大幅に下降..."
        elif change < -1:
            return "好感度が下がった"
        elif change < 0:
            return "好感度が少し下降"
        
        return ""
    
    def _generate_interaction_feedback(
        self, 
        state: AffectionState, 
        actions: List[str]
    ) -> str:
        """インタラクションフィードバックを生成"""
        if not actions:
            return ""
        
        feedbacks = []
        
        if 'compliment' in actions:
            feedbacks.append("そう言ってもらえて、すごく嬉しいな～")
        if 'mention_other_girl' in actions:
            feedbacks.append("（少し不機嫌そう）")
        if 'rude' in actions:
            feedbacks.append("（少し悲しそう）")
        if 'good_morning_night' in actions:
            feedbacks.append("気が利くね～")
        if 'quick_response' in actions:
            feedbacks.append("返信が早いね！")
        
        return " ".join(feedbacks)
    
    def get_relationship_status(self, user_id: str) -> Dict:
        """関係状態の詳細を取得"""
        state = self.get_state(user_id)
        level = self.get_level(user_id)
        
        # 進捗を計算
        progress = (state.score - level.min_val) / (level.max_val - level.min_val) * 100
        
        return {
            'score': round(state.score, 1),
            'level': level.level_name,
            'next_level': self._get_next_level(level),
            'progress_to_next': round(progress, 1),
            'mood': state.current_mood,
            'mood_intensity': state.mood_intensity,
            'is_ignoring': state.is_ignoring,
            'interaction_count': state.interaction_count,
            'greeting': level.greeting
        }
    
    def _get_next_level(self, current_level: AffectionLevel) -> Optional[str]:
        """次のレベルを取得"""
        levels = list(AffectionLevel)
        current_index = levels.index(current_level)
        if current_index < len(levels) - 1:
            return levels[current_index + 1].level_name
        return None
    
    def set_mood(
        self, 
        user_id: str, 
        mood: str, 
        intensity: float = 0.5,
        reason: str = ""
    ):
        """感情状態を設定"""
        state = self.get_state(user_id)
        state.current_mood = mood
        state.mood_intensity = max(0, min(1, intensity))
        state.mood_reason = reason
        self._save_states()
    
    def add_special_event(self, user_id: str, event_type: str, description: str):
        """特別イベントを追加"""
        state = self.get_state(user_id)
        event = {
            'type': event_type,
            'description': description,
            'date': datetime.now().isoformat()
        }
        state.special_events.append(event)
        
        # 特別イベント好感度ボーナス
        if event_type == 'first_date':
            self.update(user_id, 'date', {'bonus': 10})
        elif event_type == 'anniversary':
            self.update(user_id, 'anniversary', {'bonus': 15})
        elif event_type == 'gift':
            state.gifts_received += 1
            self.update(user_id, 'gift')
        
        self._save_states()
    
    def get_affection_hint_for_prompt(self, user_id: str) -> str:
        """プロンプト用の好感度ヒントを取得"""
        state = self.get_state(user_id)
        level = self.get_level(user_id)
        
        hints = []
        
        # レベルに基づく
        if level == AffectionLevel.STRANGER:
            hints.append("まだ知り合ったばかりなので、礼儀正しく友好的に接する")
        elif level == AffectionLevel.ACQUAINTANCE:
            hints.append("少しずつ親しくなってきたので、少しリラックスできる")
        elif level == AffectionLevel.FRIEND:
            hints.append("親友なので、もっと個人的な考えを共有できる")
        elif level == AffectionLevel.CLOSE_FRIEND:
            hints.append("関係が良いので、甘えたり冗談を言ったりできる")
        elif level == AffectionLevel.CRUSH:
            hints.append("あなたに好意を持っているので、時々恥ずかしがったり暗示したりする")
        elif level == AffectionLevel.LOVER:
            hints.append("恋愛関係なので、愛情や思いを表現できる")
        elif level == AffectionLevel.SOULMATE:
            hints.append("ソウルメイトなので、深く愛し合い、無条件で支え合う")
        
        # 感情に基づく
        if state.current_mood == 'happy':
            hints.append("今は気分が良い")
        elif state.current_mood == 'sad':
            hints.append("今は少し悲しい、慰めが必要")
        elif state.current_mood == 'angry':
            hints.append("今は少し怒っている")
        elif state.current_mood == 'jealous':
            hints.append("今は少し嫉妬している")
        
        # すねる状態に基づく
        if state.is_ignoring:
            hints.append("今はすねているので、相手に慰めてもらう必要がある")
        
        return "\n".join(hints) if hints else ""
