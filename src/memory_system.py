"""
メモリシステム - 長期記憶と短期記憶を管理
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import asyncio
from loguru import logger

import chromadb
from chromadb.config import Settings as ChromaSettings


@dataclass
class Memory:
    """メモリエントリ"""
    id: str
    content: str
    memory_type: str  # fact, preference, event, conversation, emotion
    importance: float = 1.0  # 0-1
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    user_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'memory_type': self.memory_type,
            'importance': self.importance,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'access_count': self.access_count,
            'user_id': self.user_id,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        return cls(
            id=data['id'],
            content=data['content'],
            memory_type=data['memory_type'],
            importance=data.get('importance', 1.0),
            created_at=datetime.fromisoformat(data['created_at']),
            last_accessed=datetime.fromisoformat(data.get('last_accessed', data['created_at'])),
            access_count=data.get('access_count', 0),
            user_id=data.get('user_id', ''),
            metadata=data.get('metadata', {})
        )


@dataclass
class ConversationTurn:
    """会話ターン"""
    id: str
    user_message: str
    bot_response: str
    timestamp: datetime
    user_id: str
    emotional_context: Dict[str, Any] = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_message': self.user_message,
            'bot_response': self.bot_response,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'emotional_context': self.emotional_context,
            'topics': self.topics
        }


class ShortTermMemory:
    """短期記憶 - 最近の会話コンテキスト"""
    
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self._conversations: Dict[str, List[ConversationTurn]] = {}
    
    def add_turn(self, user_id: str, user_message: str, bot_response: str, 
                 emotional_context: Dict = None, topics: List[str] = None):
        """会話ターンを追加"""
        if user_id not in self._conversations:
            self._conversations[user_id] = []
        
        turn = ConversationTurn(
            id=hashlib.md5(f"{user_id}:{datetime.now().isoformat()}".encode()).hexdigest()[:16],
            user_message=user_message,
            bot_response=bot_response,
            timestamp=datetime.now(),
            user_id=user_id,
            emotional_context=emotional_context or {},
            topics=topics or []
        )
        
        self._conversations[user_id].append(turn)
        
        # 保持最大数量
        if len(self._conversations[user_id]) > self.max_turns:
            self._conversations[user_id] = self._conversations[user_id][-self.max_turns:]
    
    def get_recent_context(self, user_id: str, n_turns: int = 5) -> List[ConversationTurn]:
        """最近の会話コンテキストを取得"""
        turns = self._conversations.get(user_id, [])
        return turns[-n_turns:] if turns else []
    
    def get_context_string(self, user_id: str, n_turns: int = 5) -> str:
        """フォーマットされたコンテキスト文字列を取得"""
        turns = self.get_recent_context(user_id, n_turns)
        if not turns:
            return ""
        
        context = "【最近の会話】\n"
        for turn in turns:
            context += f"ユーザー：{turn.user_message}\n"
            context += f"あなた：{turn.bot_response}\n"
        
        return context
    
    def clear(self, user_id: str = None):
        """短期記憶をクリア"""
        if user_id:
            self._conversations.pop(user_id, None)
        else:
            self._conversations.clear()
    
    def get_topics(self, user_id: str, n_turns: int = 10) -> List[str]:
        """最近議論されたトピックを取得"""
        turns = self.get_recent_context(user_id, n_turns)
        topics = set()
        for turn in turns:
            topics.update(turn.topics)
        return list(topics)


class LongTermMemory:
    """長期記憶 - ベクトルデータベースに保存"""
    
    def __init__(self, chroma_client, collection_name: str = "memories"):
        self.chroma_client = chroma_client
        
        # コレクションを取得または作成
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
        except:
            self.collection = self.chroma_client.create_collection(collection_name)
    
    async def add_memory(self, memory: Memory):
        """メモリを追加"""
        self.collection.add(
            ids=[memory.id],
            documents=[memory.content],
            metadatas=[{
                'memory_type': memory.memory_type,
                'importance': memory.importance,
                'user_id': memory.user_id,
                'created_at': memory.created_at.isoformat(),
                'metadata': json.dumps(memory.metadata)
            }]
        )
    
    async def add_memories(self, memories: List[Memory]):
        """メモリを一括追加"""
        if not memories:
            return
        
        self.collection.add(
            ids=[m.id for m in memories],
            documents=[m.content for m in memories],
            metadatas=[{
                'memory_type': m.memory_type,
                'importance': m.importance,
                'user_id': m.user_id,
                'created_at': m.created_at.isoformat(),
                'metadata': json.dumps(m.metadata)
            } for m in memories]
        )
    
    async def retrieve_relevant(
        self, 
        query: str, 
        user_id: str = None,
        n_results: int = 5,
        memory_types: List[str] = None,
        min_importance: float = 0.0
    ) -> List[Memory]:
        """関連するメモリを検索"""
        
        # フィルタ条件を構築
        where_filter = {}
        if user_id:
            where_filter['user_id'] = user_id
        if memory_types:
            where_filter['memory_type'] = {'$in': memory_types}
        
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        memories = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                
                # 重要度フィルタリング
                importance = metadata.get('importance', 1.0)
                if importance < min_importance:
                    continue
                
                memory = Memory(
                    id=doc_id,
                    content=results['documents'][0][i],
                    memory_type=metadata.get('memory_type', 'fact'),
                    importance=importance,
                    user_id=metadata.get('user_id', ''),
                    created_at=datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat())),
                    metadata=json.loads(metadata.get('metadata', '{}'))
                )
                memories.append(memory)
        
        return memories
    
    async def get_user_memories(
        self, 
        user_id: str, 
        memory_types: List[str] = None
    ) -> List[Memory]:
        """ユーザーのすべてのメモリを取得"""
        where_filter = {'user_id': user_id}
        if memory_types:
            where_filter['memory_type'] = {'$in': memory_types}
        
        results = self.collection.get(where=where_filter)
        
        memories = []
        if results['ids']:
            for i, doc_id in enumerate(results['ids']):
                metadata = results['metadatas'][i] if results['metadatas'] else {}
                memory = Memory(
                    id=doc_id,
                    content=results['documents'][i],
                    memory_type=metadata.get('memory_type', 'fact'),
                    importance=metadata.get('importance', 1.0),
                    user_id=metadata.get('user_id', ''),
                    created_at=datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat())),
                    metadata=json.loads(metadata.get('metadata', '{}'))
                )
                memories.append(memory)
        
        return memories
    
    async def update_memory_access(self, memory_id: str):
        """メモリアクセス統計を更新"""
        # ChromaDBは直接更新をサポートしていないので、再追加が必要
        pass
    
    async def delete_memory(self, memory_id: str):
        """メモリを削除"""
        self.collection.delete(ids=[memory_id])
    
    async def consolidate_memories(self, user_id: str, llm_client):
        """メモリを統合 - LLMを使用して要約と精製"""
        memories = await self.get_user_memories(user_id)
        
        if len(memories) < 10:
            return
        
        # タイプ別にグループ化
        facts = [m for m in memories if m.memory_type == 'fact']
        preferences = [m for m in memories if m.memory_type == 'preference']
        
        # LLMを使用して要約
        if llm_client and len(facts) > 5:
            fact_contents = [m.content for m in facts[-20:]]
            prompt = f"""ユーザーに関する以下の事実情報を要約し、重複を除去し、重要なポイントを抽出してください：

{chr(10).join(fact_contents)}

簡潔な要点リストを出力してください："""
            
            try:
                summary = await llm_client.generate(prompt)
                
                # 要約を新しいメモリとして追加
                summary_memory = Memory(
                    id=hashlib.md5(f"summary:facts:{user_id}".encode()).hexdigest()[:16],
                    content=f"ユーザー事実の要約：{summary}",
                    memory_type='consolidated_fact',
                    importance=0.9,
                    user_id=user_id
                )
                await self.add_memory(summary_memory)
                
            except Exception as e:
                logger.error(f"Memory consolidation failed: {e}")


class MemoryExtractor:
    """メモリ抽出器 - 会話から記憶に値する情報を抽出"""
    
    # 記憶に値するキーワード
    MEMORY_KEYWORDS = [
        '好き', '愛', '嫌い', '怖い', '欲しい', '夢', '目標',
        '仕事', '勉強', '家族', '友達', '誕生日', '記念日',
        '名前', '年齢', '住んでいる', 'から来た', '専門', '趣味',
        'like', 'love', 'hate', 'want', 'dream', 'goal',
        'work', 'study', 'family', 'friend', 'birthday'
    ]
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def extract_from_message(
        self, 
        user_message: str, 
        bot_response: str,
        user_id: str
    ) -> List[Memory]:
        """単一メッセージからメモリを抽出"""
        memories = []
        combined = f"{user_message} {bot_response}"
        
        # 単純なキーワード抽出
        for keyword in self.MEMORY_KEYWORDS:
            if keyword in combined:
                # キーワードを含む文を抽出
                sentences = combined.replace('!', '。').replace('?', '。').split('。')
                for sent in sentences:
                    if keyword in sent and len(sent.strip()) > 5:
                        memory_id = hashlib.md5(
                            f"{user_id}:{sent.strip()}".encode()
                        ).hexdigest()[:16]
                        
                        memory = Memory(
                            id=memory_id,
                            content=sent.strip(),
                            memory_type=self._classify_memory_type(sent),
                            importance=self._calculate_importance(sent),
                            user_id=user_id
                        )
                        memories.append(memory)
        
        # 重複除去
        seen = set()
        unique_memories = []
        for m in memories:
            if m.content not in seen:
                seen.add(m.content)
                unique_memories.append(m)
        
        return unique_memories[:3]  # 数量制限
    
    async def extract_with_llm(
        self, 
        conversation_history: List[Dict[str, str]],
        user_id: str
    ) -> List[Memory]:
        """LLMを使用してメモリを抽出"""
        if not self.llm_client or len(conversation_history) < 3:
            return []
        
        # 会話履歴をフォーマット
        conversation_text = "\n".join([
            f"ユーザー：{turn['user']}\nアシスタント：{turn['bot']}"
            for turn in conversation_history[-5:]
        ])
        
        prompt = f"""以下の会話から長期的に記憶する価値のある情報を抽出してください：

{conversation_text}

以下の情報を抽出してください：
1. ユーザーの個人情報（名前、年齢、職業など）
2. ユーザーの好みと嗜好
3. ユーザーが言及した重要な出来事
4. ユーザーの感情状態

JSON形式で出力：
{{
    "memories": [
        {{"content": "記憶内容", "type": "fact/preference/event/emotion", "importance": 0.8}}
    ]
}}

記憶に値する情報がない場合は、空の配列を返してください。"""
        
        try:
            response = await self.llm_client.generate(prompt)
            import json
            data = json.loads(response)
            
            memories = []
            for mem_data in data.get('memories', []):
                memory_id = hashlib.md5(
                    f"{user_id}:{mem_data['content']}".encode()
                ).hexdigest()[:16]
                
                memory = Memory(
                    id=memory_id,
                    content=mem_data['content'],
                    memory_type=mem_data.get('type', 'fact'),
                    importance=mem_data.get('importance', 0.5),
                    user_id=user_id
                )
                memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"LLM memory extraction failed: {e}")
            return []
    
    def _classify_memory_type(self, content: str) -> str:
        """メモリタイプを分類"""
        content = content.lower()
        
        if any(word in content for word in ['好き', '愛', 'love', 'like', 'favorite']):
            return 'preference'
        elif any(word in content for word in ['誕生日', 'anniversary', 'event', 'party']):
            return 'event'
        elif any(word in content for word in ['嬉しい', '悲しい', '怒り', 'sad', 'happy', 'angry']):
            return 'emotion'
        else:
            return 'fact'
    
    def _calculate_importance(self, content: str) -> float:
        """メモリの重要度を計算"""
        importance = 0.5
        
        # 個人情報はより重要
        personal_indicators = ['私は', '私の名前は', '私はから来た', '私はに住んでいる', '私は仕事', '私の']
        if any(indicator in content for indicator in personal_indicators):
            importance += 0.3
        
        # 感情表現
        emotion_words = ['愛', '憎しみ', '怖い', '夢', 'love', 'hate', 'dream']
        if any(word in content for word in emotion_words):
            importance += 0.2
        
        # 長さの要素
        if len(content) > 50:
            importance += 0.1
        
        return min(1.0, importance)


class MemorySystem:
    """メモリシステムメインクラス"""
    
    def __init__(
        self, 
        chroma_client,
        llm_client=None,
        short_term_limit: int = 10
    ):
        self.short_term = ShortTermMemory(max_turns=short_term_limit)
        self.long_term = LongTermMemory(chroma_client)
        self.extractor = MemoryExtractor(llm_client)
        self.llm_client = llm_client
    
    async def process_conversation_turn(
        self, 
        user_id: str, 
        user_message: str, 
        bot_response: str,
        emotional_context: Dict = None,
        topics: List[str] = None
    ):
        """会話ターンを処理し、メモリを更新"""
        
        # 1. 短期記憶を更新
        self.short_term.add_turn(
            user_id, user_message, bot_response, 
            emotional_context, topics
        )
        
        # 2. 長期記憶を抽出
        memories = self.extractor.extract_from_message(
            user_message, bot_response, user_id
        )
        
        # 3. LLMを使用して抽出（利用可能な場合）
        if self.llm_client:
            recent = self.short_term.get_recent_context(user_id, 5)
            history = [
                {'user': t.user_message, 'bot': t.bot_response}
                for t in recent
            ]
            llm_memories = await self.extractor.extract_with_llm(history, user_id)
            memories.extend(llm_memories)
        
        # 4. 長期記憶に保存
        if memories:
            await self.long_term.add_memories(memories)
            logger.info(f"Extracted {len(memories)} memories for user {user_id}")
    
    async def get_context_for_response(
        self, 
        user_id: str, 
        current_message: str,
        include_short_term: bool = True,
        include_long_term: bool = True,
        n_long_term: int = 5
    ) -> str:
        """応答生成のためのコンテキストを取得"""
        context_parts = []
        
        # 短期記憶
        if include_short_term:
            short_context = self.short_term.get_context_string(user_id)
            if short_context:
                context_parts.append(short_context)
        
        # 長期記憶
        if include_long_term:
            relevant_memories = await self.long_term.retrieve_relevant(
                query=current_message,
                user_id=user_id,
                n_results=n_long_term
            )
            
            if relevant_memories:
                memory_context = "【関連する記憶】\n"
                for mem in relevant_memories:
                    memory_context += f"- {mem.content}\n"
                context_parts.append(memory_context)
        
        return "\n\n".join(context_parts)
    
    async def add_explicit_memory(
        self, 
        user_id: str, 
        content: str, 
        memory_type: str = 'fact',
        importance: float = 0.8
    ):
        """明示的なメモリを追加"""
        memory_id = hashlib.md5(
            f"{user_id}:{content}".encode()
        ).hexdigest()[:16]
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            user_id=user_id
        )
        
        await self.long_term.add_memory(memory)
    
    async def get_user_profile(self, user_id: str) -> Dict[str, List[str]]:
        """ユーザープロファイルを取得"""
        memories = await self.long_term.get_user_memories(user_id)
        
        profile = {
            'facts': [],
            'preferences': [],
            'events': [],
            'emotions': []
        }
        
        for mem in memories:
            if mem.memory_type in profile:
                profile[mem.memory_type].append(mem.content)
        
        return profile
    
    async def consolidate(self, user_id: str):
        """ユーザーメモリを統合"""
        await self.long_term.consolidate_memories(user_id, self.llm_client)
    
    def clear_short_term(self, user_id: str = None):
        """短期記憶をクリア"""
        self.short_term.clear(user_id)
