"""
知識学習システム - ボットがインポートした知識を学習し、人格に統合する
"""
import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from loguru import logger

import chromadb
from chromadb.config import Settings as ChromaSettings
import numpy as np


@dataclass
class KnowledgeItem:
    """知識項目"""
    id: str
    content: str
    source: str  # ソースファイル/URL
    source_type: str  # file, url, conversation, learned
    category: str  # 知識カテゴリ
    importance: float = 1.0  # 重要度 0-1
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content,
            'source': self.source,
            'source_type': self.source_type,
            'category': self.category,
            'importance': self.importance,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'access_count': self.access_count,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeItem':
        return cls(
            id=data['id'],
            content=data['content'],
            source=data['source'],
            source_type=data['source_type'],
            category=data['category'],
            importance=data.get('importance', 1.0),
            created_at=datetime.fromisoformat(data['created_at']),
            last_accessed=datetime.fromisoformat(data.get('last_accessed', data['created_at'])),
            access_count=data.get('access_count', 0),
            metadata=data.get('metadata', {})
        )


@dataclass
class LearnedInsight:
    """学習された洞察/理解"""
    id: str
    original_knowledge_ids: List[str]  # どの知識に基づくか
    insight_type: str  # pattern, preference, fact, emotion_rule, behavior_rule
    content: str  # 洞察内容
    confidence: float  # 信頼度
    created_at: datetime = field(default_factory=datetime.now)
    verified: bool = False
    application_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'original_knowledge_ids': self.original_knowledge_ids,
            'insight_type': self.insight_type,
            'content': self.content,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat(),
            'verified': self.verified,
            'application_count': self.application_count
        }


class KnowledgeImporter:
    """知識インポーター - 複数のフォーマットをサポート"""
    
    SUPPORTED_FORMATS = {'.txt', '.md', '.json', '.yaml', '.yml'}
    
    def __init__(self, knowledge_base_path: str = "./data/knowledge"):
        self.knowledge_base_path = Path(knowledge_base_path)
        self.knowledge_base_path.mkdir(parents=True, exist_ok=True)
    
    async def import_file(self, file_path: str, category: str = "general") -> List[KnowledgeItem]:
        """ファイルから知識をインポート"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if path.suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {path.suffix}")
        
        logger.info(f"Importing knowledge from {file_path}")
        
        content = await self._read_file(path)
        items = await self._parse_content(content, path.name, category)
        
        # 知識ベースに保存
        await self._save_to_knowledge_base(items)
        
        return items
    
    async def import_directory(self, dir_path: str, category: str = "general") -> List[KnowledgeItem]:
        """ディレクトリを一括インポート"""
        all_items = []
        path = Path(dir_path)
        
        for file_path in path.rglob("*"):
            if file_path.suffix in self.SUPPORTED_FORMATS:
                try:
                    items = await self.import_file(str(file_path), category)
                    all_items.extend(items)
                except Exception as e:
                    logger.error(f"Failed to import {file_path}: {e}")
        
        return all_items
    
    async def import_text(self, text: str, source: str, category: str = "learned") -> KnowledgeItem:
        """プレーンテキストから知識をインポート"""
        item_id = hashlib.md5(f"{source}:{text[:100]}".encode()).hexdigest()
        
        item = KnowledgeItem(
            id=item_id,
            content=text,
            source=source,
            source_type="learned",
            category=category
        )
        
        await self._save_to_knowledge_base([item])
        return item
    
    async def _read_file(self, path: Path) -> str:
        """ファイル内容を読み込む"""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def _parse_content(self, content: str, source: str, category: str) -> List[KnowledgeItem]:
        """内容を解析し、知識項目を抽出"""
        items = []
        
        # インテリジェントなセグメント化
        segments = self._segment_content(content)
        
        for i, segment in enumerate(segments):
            if len(segment.strip()) < 10:  # 短すぎるセグメントをフィルタリング
                continue
            
            item_id = hashlib.md5(f"{source}:{i}:{segment[:50]}".encode()).hexdigest()
            
            item = KnowledgeItem(
                id=item_id,
                content=segment.strip(),
                source=source,
                source_type="file",
                category=category
            )
            items.append(item)
        
        return items
    
    def _segment_content(self, content: str) -> List[str]:
        """内容をインテリジェントにセグメント化"""
        # 段落で分割
        paragraphs = content.split('\n\n')
        
        segments = []
        current_segment = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 現在の段落が完全な文/段落の場合、個別にセグメント化
            if para.endswith(('。', '！', '？', '.', '!', '?', '」', '"', '"')):
                if current_segment:
                    segments.append(current_segment + " " + para)
                    current_segment = ""
                else:
                    segments.append(para)
            else:
                # 短い段落を蓄積
                if len(current_segment) + len(para) < 500:
                    current_segment += " " + para if current_segment else para
                else:
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = para
        
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    async def _save_to_knowledge_base(self, items: List[KnowledgeItem]):
        """知識ベースディレクトリに保存"""
        for item in items:
            file_path = self.knowledge_base_path / f"{item.id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(item.to_dict(), f, ensure_ascii=False, indent=2)


class KnowledgeLearner:
    """知識学習者 - 知識を分析し理解する"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.insights: List[LearnedInsight] = []
    
    async def learn_from_knowledge(self, items: List[KnowledgeItem]) -> List[LearnedInsight]:
        """知識から洞察を学習"""
        insights = []
        
        # 1. ユーザーの好みを抽出
        preference_insights = await self._extract_preferences(items)
        insights.extend(preference_insights)
        
        # 2. 行動パターンを発見
        pattern_insights = await self._discover_patterns(items)
        insights.extend(pattern_insights)
        
        # 3. 重要な事実を抽出
        fact_insights = await self._extract_facts(items)
        insights.extend(fact_insights)
        
        # 4. 感情ルールを理解
        emotion_insights = await self._understand_emotions(items)
        insights.extend(emotion_insights)
        
        self.insights.extend(insights)
        return insights
    
    async def _extract_preferences(self, items: List[KnowledgeItem]) -> List[LearnedInsight]:
        """ユーザーの好みを抽出"""
        insights = []
        
        # 「好き」「嫌い」「好み」などのキーワードを含む内容を分析
        preference_keywords = ['好き', '愛', '好み', '大好き', '嫌い', '苦手', '嫌悪', '反感']
        
        for item in items:
            content = item.content
            for keyword in preference_keywords:
                if keyword in content:
                    # 好みの文を抽出
                    sentences = content.split('。')
                    for sent in sentences:
                        if keyword in sent and len(sent) > 10:
                            insight_id = hashlib.md5(f"pref:{sent}".encode()).hexdigest()[:16]
                            insight = LearnedInsight(
                                id=insight_id,
                                original_knowledge_ids=[item.id],
                                insight_type="preference",
                                content=sent.strip(),
                                confidence=0.7
                            )
                            insights.append(insight)
        
        return insights
    
    async def _discover_patterns(self, items: List[KnowledgeItem]) -> List[LearnedInsight]:
        """行動パターンを発見"""
        insights = []
        
        # 時間パターン
        time_patterns = ['朝', '夜', '毎日', 'よく', 'いつも', '習慣']
        
        for item in items:
            content = item.content
            for pattern in time_patterns:
                if pattern in content:
                    sentences = content.split('。')
                    for sent in sentences:
                        if pattern in sent and len(sent) > 10:
                            insight_id = hashlib.md5(f"pattern:{sent}".encode()).hexdigest()[:16]
                            insight = LearnedInsight(
                                id=insight_id,
                                original_knowledge_ids=[item.id],
                                insight_type="pattern",
                                content=sent.strip(),
                                confidence=0.6
                            )
                            insights.append(insight)
        
        return insights
    
    async def _extract_facts(self, items: List[KnowledgeItem]) -> List[LearnedInsight]:
        """重要な事実を抽出"""
        insights = []
        
        # 事実キーワード
        fact_indicators = ['は', 'に', 'いる', 'から来た', '仕事', '住んでいる', '誕生日']
        
        for item in items:
            content = item.content
            # 個人情報を含む事実を探す
            if any(indicator in content for indicator in ['私は', '私の名前は', '私はから来た', '私はに住んでいる', '私は仕事']):
                sentences = content.split('。')
                for sent in sentences:
                    if any(sent.startswith(prefix) for prefix in ['私は', '私の', '私の名前は']):
                        insight_id = hashlib.md5(f"fact:{sent}".encode()).hexdigest()[:16]
                        insight = LearnedInsight(
                            id=insight_id,
                            original_knowledge_ids=[item.id],
                            insight_type="fact",
                            content=sent.strip(),
                            confidence=0.8
                        )
                        insights.append(insight)
        
        return insights
    
    async def _understand_emotions(self, items: List[KnowledgeItem]) -> List[LearnedInsight]:
        """感情トリガールールを理解"""
        insights = []
        
        emotion_keywords = ['嬉しい', '悲しい', '怒り', '失望', '興奮', '不安', '怖い']
        
        for item in items:
            content = item.content
            for emotion in emotion_keywords:
                if emotion in content:
                    sentences = content.split('。')
                    for sent in sentences:
                        if emotion in sent and ('とき' in sent or 'もし' in sent or 'させて' in sent):
                            insight_id = hashlib.md5(f"emotion:{sent}".encode()).hexdigest()[:16]
                            insight = LearnedInsight(
                                id=insight_id,
                                original_knowledge_ids=[item.id],
                                insight_type="emotion_rule",
                                content=sent.strip(),
                                confidence=0.65
                            )
                            insights.append(insight)
        
        return insights
    
    async def deep_learn_with_llm(self, items: List[KnowledgeItem]) -> List[LearnedInsight]:
        """LLMを使用した深層学習"""
        if not self.llm_client:
            return []
        
        insights = []
        
        # 関連する内容を結合
        combined_content = "\n".join([item.content for item in items[:10]])  # 数量制限
        
        prompt = f"""以下のユーザー情報に基づいて、重要な洞察を分析・抽出してください：

{combined_content}

以下の点を分析してください：
1. ユーザーの性格特徴
2. ユーザーの趣味・興味と好み
3. ユーザーの行動パターン
4. ユーザーの感情トリガーポイント
5. ユーザーとの付き合い方のアドバイス

JSON形式で出力：
{{
    "personality_traits": ["特徴1", "特徴2"],
    "preferences": ["好み1", "好み2"],
    "patterns": ["パターン1", "パターン2"],
    "emotional_triggers": ["トリガーポイント1"],
    "interaction_tips": ["アドバイス1", "アドバイス2"]
}}"""
        
        try:
            response = await self.llm_client.generate(prompt)
            # JSONレスポンスを解析
            import json
            analysis = json.loads(response)
            
            # insightsに変換
            for category, items_list in analysis.items():
                for content in items_list:
                    insight_id = hashlib.md5(f"llm:{category}:{content}".encode()).hexdigest()[:16]
                    insight = LearnedInsight(
                        id=insight_id,
                        original_knowledge_ids=[item.id for item in items],
                        insight_type=category,
                        content=content,
                        confidence=0.85
                    )
                    insights.append(insight)
        
        except Exception as e:
            logger.error(f"Deep learning failed: {e}")
        
        return insights


class KnowledgeIntegrator:
    """知識インテグレーター - 学習した知識を personality に統合する"""
    
    def __init__(self, persona_config_path: str):
        self.persona_config_path = Path(persona_config_path)
        self.learned_knowledge_file = self.persona_config_path.parent / "learned_knowledge.yaml"
    
    async def integrate_insights(self, insights: List[LearnedInsight]):
        """洞察を personality に統合"""
        
        # タイプ別にグループ化
        grouped = self._group_by_type(insights)
        
        # learned_knowledge.yaml を更新
        learned_data = self._load_learned_knowledge()
        
        # 好みを統合
        if 'preference' in grouped:
            learned_data['user_preferences'] = learned_data.get('user_preferences', [])
            for insight in grouped['preference']:
                if insight.content not in learned_data['user_preferences']:
                    learned_data['user_preferences'].append(insight.content)
        
        # 事実を統合
        if 'fact' in grouped:
            learned_data['user_facts'] = learned_data.get('user_facts', [])
            for insight in grouped['fact']:
                if insight.content not in learned_data['user_facts']:
                    learned_data['user_facts'].append(insight.content)
        
        # 行動パターンを統合
        if 'pattern' in grouped:
            learned_data['user_patterns'] = learned_data.get('user_patterns', [])
            for insight in grouped['pattern']:
                if insight.content not in learned_data['user_patterns']:
                    learned_data['user_patterns'].append(insight.content)
        
        # 感情ルールを統合
        if 'emotion_rule' in grouped:
            learned_data['emotional_rules'] = learned_data.get('emotional_rules', [])
            for insight in grouped['emotion_rule']:
                if insight.content not in learned_data['emotional_rules']:
                    learned_data['emotional_rules'].append(insight.content)
        
        # 保存
        await self._save_learned_knowledge(learned_data)
        
        logger.info(f"Integrated {len(insights)} insights into personality")
    
    def _group_by_type(self, insights: List[LearnedInsight]) -> Dict[str, List[LearnedInsight]]:
        """タイプ別にグループ化"""
        grouped = {}
        for insight in insights:
            if insight.insight_type not in grouped:
                grouped[insight.insight_type] = []
            grouped[insight.insight_type].append(insight)
        return grouped
    
    def _load_learned_knowledge(self) -> Dict[str, Any]:
        """学習済み知識を読み込む"""
        import yaml
        
        if self.learned_knowledge_file.exists():
            with open(self.learned_knowledge_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    async def _save_learned_knowledge(self, data: Dict[str, Any]):
        """学習した知識を保存"""
        import yaml
        
        with open(self.learned_knowledge_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    def get_enhanced_system_prompt(self, base_prompt: str) -> str:
        """強化されたシステムプロンプトを取得（学習した知識を含む）"""
        learned = self._load_learned_knowledge()
        
        enhancement = "\n\n【あなたについての理解】\n"
        
        if learned.get('user_facts'):
            enhancement += "重要な情報：\n"
            for fact in learned['user_facts'][:10]:  # 数量制限
                enhancement += f"- {fact}\n"
        
        if learned.get('user_preferences'):
            enhancement += "\n好みと嗜好：\n"
            for pref in learned['user_preferences'][:10]:
                enhancement += f"- {pref}\n"
        
        if learned.get('user_patterns'):
            enhancement += "\n行動パターン：\n"
            for pattern in learned['user_patterns'][:5]:
                enhancement += f"- {pattern}\n"
        
        if learned.get('emotional_rules'):
            enhancement += "\n感情の特徴：\n"
            for rule in learned['emotional_rules'][:5]:
                enhancement += f"- {rule}\n"
        
        enhancement += "\n【適用ルール】\n"
        enhancement += "- 会話の中でこれらの理解を自然に活用する\n"
        enhancement += "- ユーザーの好みを覚えて、積極的に言及する\n"
        enhancement += "- ユーザーのパターンに基づいてインタラクション方法を調整する\n"
        enhancement += "- ユーザーのネガティブな感情を引き起こさないようにする\n"
        
        return base_prompt + enhancement


class KnowledgeRetriever:
    """知識リトリーバー - 会話中で関連する知識を検索"""
    
    def __init__(self, chroma_client, embedding_model=None):
        self.chroma_client = chroma_client
        self.embedding_model = embedding_model
        
        # コレクションを取得または作成
        try:
            self.collection = self.chroma_client.get_collection("knowledge")
        except:
            self.collection = self.chroma_client.create_collection("knowledge")
    
    async def add_knowledge(self, items: List[KnowledgeItem]):
        """知識をベクトルデータベースに追加"""
        if not items:
            return
        
        ids = [item.id for item in items]
        documents = [item.content for item in items]
        metadatas = [{
            'source': item.source,
            'category': item.category,
            'importance': item.importance
        } for item in items]
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        logger.info(f"Added {len(items)} items to vector DB")
    
    async def retrieve_relevant(
        self, 
        query: str, 
        n_results: int = 5,
        min_similarity: float = 0.5
    ) -> List[KnowledgeItem]:
        """関連する知識を検索"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        items = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                distance = results['distances'][0][i] if results['distances'] else 1.0
                similarity = 1 - distance
                
                if similarity >= min_similarity:
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    item = KnowledgeItem(
                        id=doc_id,
                        content=results['documents'][0][i],
                        source=metadata.get('source', 'unknown'),
                        source_type='retrieved',
                        category=metadata.get('category', 'general'),
                        importance=metadata.get('importance', 1.0)
                    )
                    items.append(item)
        
        return items
    
    async def get_context_for_conversation(
        self, 
        user_message: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """会話のための関連コンテキストを取得"""
        # 関連する知識を検索
        relevant = await self.retrieve_relevant(user_message, n_results=3)
        
        if not relevant:
            return ""
        
        context = "【関連する記憶】\n"
        for item in relevant:
            context += f"- {item.content}\n"
        
        context += "\n【適用ヒント】\n"
        context += "返信の中で上記の関連情報を自然に活用するが、直接引用しないでください。\n"
        
        return context


class KnowledgeSystem:
    """知識システムメインクラス - すべての知識機能を統合"""
    
    def __init__(
        self, 
        chroma_client,
        llm_client=None,
        knowledge_base_path: str = "./data/knowledge",
        persona_config_path: str = "./config/persona_default.yaml"
    ):
        self.importer = KnowledgeImporter(knowledge_base_path)
        self.learner = KnowledgeLearner(llm_client)
        self.integrator = KnowledgeIntegrator(persona_config_path)
        self.retriever = KnowledgeRetriever(chroma_client)
        
        self.knowledge_base_path = Path(knowledge_base_path)
        self._knowledge_cache: Dict[str, KnowledgeItem] = {}
    
    async def import_and_learn(
        self, 
        source: str, 
        source_type: str = "file",
        category: str = "general"
    ) -> Dict[str, Any]:
        """知識をインポートして学習"""
        
        # 1. 知識をインポート
        if source_type == "file":
            items = await self.importer.import_file(source, category)
        elif source_type == "directory":
            items = await self.importer.import_directory(source, category)
        elif source_type == "text":
            item = await self.importer.import_text(source, "manual_input", category)
            items = [item]
        else:
            raise ValueError(f"Unknown source type: {source_type}")
        
        logger.info(f"Imported {len(items)} knowledge items")
        
        # 2. ベクトルデータベースに追加
        await self.retriever.add_knowledge(items)
        
        # 3. 洞察を学習
        insights = await self.learner.learn_from_knowledge(items)
        
        # 4. LLMを使用した深層学習（利用可能な場合）
        if self.learner.llm_client and len(items) >= 3:
            deep_insights = await self.learner.deep_learn_with_llm(items)
            insights.extend(deep_insights)
        
        # 5. personalityに統合
        await self.integrator.integrate_insights(insights)
        
        # キャッシュ
        for item in items:
            self._knowledge_cache[item.id] = item
        
        return {
            'imported_count': len(items),
            'insights_count': len(insights),
            'insights_by_type': self._count_by_type(insights)
        }
    
    def _count_by_type(self, insights: List[LearnedInsight]) -> Dict[str, int]:
        """タイプ別に洞察を統計"""
        counts = {}
        for insight in insights:
            counts[insight.insight_type] = counts.get(insight.insight_type, 0) + 1
        return counts
    
    async def get_enhanced_context(self, user_message: str) -> str:
        """強化された会話コンテキストを取得"""
        return await self.retriever.get_context_for_conversation(user_message)
    
    async def learn_from_conversation(
        self, 
        user_message: str, 
        bot_response: str,
        user_id: str
    ):
        """会話から学習"""
        # 価値ある情報を抽出
        combined = f"ユーザーが言った：{user_message}\n私が返信：{bot_response}"
        
        # 知識項目を作成
        item_id = hashlib.md5(f"conv:{user_id}:{combined[:100]}".encode()).hexdigest()
        
        item = KnowledgeItem(
            id=item_id,
            content=combined,
            source=f"conversation:{user_id}",
            source_type="conversation",
            category="interaction"
        )
        
        # 学習
        insights = await self.learner.learn_from_knowledge([item])
        
        if insights:
            await self.integrator.integrate_insights(insights)
        
        return len(insights)
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """学習サマリーを取得"""
        learned = self.integrator._load_learned_knowledge()
        
        return {
            'total_facts': len(learned.get('user_facts', [])),
            'total_preferences': len(learned.get('user_preferences', [])),
            'total_patterns': len(learned.get('user_patterns', [])),
            'total_emotional_rules': len(learned.get('emotional_rules', [])),
            'cached_knowledge': len(self._knowledge_cache)
        }
