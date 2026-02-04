#!/usr/bin/env python3
"""
知識インポートツール - 知識ファイルを一括インポート
"""
import os
import sys
import asyncio
import argparse
from pathlib import Path

# プロジェクトルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.knowledge_system import KnowledgeImporter, KnowledgeLearner, KnowledgeIntegrator
from src.llm_client import create_llm_manager
from src.config import settings
import chromadb
from chromadb.config import Settings as ChromaSettings


class KnowledgeImportTool:
    """知識インポートツール"""
    
    SUPPORTED_FORMATS = {'.txt', '.md', '.json', '.yaml', '.yml'}
    
    def __init__(self):
        self.importer = None
        self.learner = None
        self.integrator = None
        self.chroma_client = None
        self.llm_client = None
    
    async def initialize(self):
        """初期化"""
        print("🔧 知識システムを初期化中...")
        
        # ChromaDBを初期化
        os.makedirs("./data/chroma", exist_ok=True)
        self.chroma_client = chromadb.Client(
            ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory="./data/chroma"
            )
        )
        
        # LLMを初期化（オプション）
        try:
            llm_manager = create_llm_manager(settings)
            self.llm_client = llm_manager
            print("✅ LLMクライアントが初期化されました")
        except Exception as e:
            print(f"⚠️ LLM初期化失敗（基本学習を使用します）: {e}")
            self.llm_client = None
        
        # コンポーネントを初期化
        self.importer = KnowledgeImporter("./data/knowledge")
        self.learner = KnowledgeLearner(self.llm_client)
        self.integrator = KnowledgeIntegrator("./config/persona_default.yaml")
        
        print("✅ 初期化が完了しました\n")
    
    async def import_file(self, filepath: str, category: str = "general"):
        """単一ファイルをインポート"""
        path = Path(filepath)
        
        if not path.exists():
            print(f"❌ ファイルが存在しません: {filepath}")
            return
        
        if path.suffix not in self.SUPPORTED_FORMATS:
            print(f"❌ サポートされていない形式: {path.suffix}")
            return
        
        print(f"📄 インポート中: {filepath}")
        
        try:
            # 知識をインポート
            items = await self.importer.import_file(filepath, category)
            print(f"  ✓ {len(items)} 件の知識をインポート")
            
            # 洞察を学習
            insights = await self.learner.learn_from_knowledge(items)
            print(f"  ✓ {len(insights)} 個の洞察を抽出")
            
            # 深層学習（LLMが利用可能な場合）
            if self.llm_client and len(items) >= 3:
                print("  🤖 深層学習を実行中...")
                deep_insights = await self.learner.deep_learn_with_llm(items)
                insights.extend(deep_insights)
                print(f"  ✓ 深層学習が完了、追加で {len(deep_insights)} 個の洞察を抽出")
            
            # personalityに統合
            await self.integrator.integrate_insights(insights)
            print(f"  ✓ personalityに統合されました")
            
            print(f"\n✅ インポート完了: {filepath}\n")
            
        except Exception as e:
            print(f"❌ インポート失敗: {e}\n")
    
    async def import_directory(self, dirpath: str, category: str = "general"):
        """ディレクトリ全体をインポート"""
        path = Path(dirpath)
        
        if not path.exists():
            print(f"❌ ディレクトリが存在しません: {dirpath}")
            return
        
        if not path.is_dir():
            print(f"❌ ディレクトリではありません: {dirpath}")
            return
        
        # サポートされているすべてのファイルを検索
        files = []
        for ext in self.SUPPORTED_FORMATS:
            files.extend(path.rglob(f"*{ext}"))
        
        if not files:
            print(f"⚠️ ディレクトリにサポートされているファイルがありません: {dirpath}")
            return
        
        print(f"📁 {len(files)} 個のファイルが見つかりました\n")
        
        # 一つずつインポート
        for i, file_path in enumerate(files, 1):
            print(f"[{i}/{len(files)}] ", end="")
            await self.import_file(str(file_path), category)
    
    async def import_text(self, text: str, category: str = "manual"):
        """テキストをインポート"""
        print("📝 テキストをインポート中...")
        
        try:
            item = await self.importer.import_text(text, "manual_input", category)
            print(f"  ✓ 1 件の知識をインポート")
            
            insights = await self.learner.learn_from_knowledge([item])
            print(f"  ✓ {len(insights)} 個の洞察を抽出")
            
            await self.integrator.integrate_insights(insights)
            print(f"  ✓ personalityに統合されました")
            
            print("\n✅ テキストインポートが完了しました\n")
            
        except Exception as e:
            print(f"❌ インポート失敗: {e}\n")
    
    def show_stats(self):
        """統計情報を表示"""
        learned = self.integrator._load_learned_knowledge()
        
        print("\n" + "=" * 50)
        print("📊 知識学習統計")
        print("=" * 50)
        print(f"ユーザーの事実: {len(learned.get('user_facts', []))}")
        print(f"ユーザーの好み: {len(learned.get('user_preferences', []))}")
        print(f"行動パターン: {len(learned.get('user_patterns', []))}")
        print(f"感情ルール: {len(learned.get('emotional_rules', []))}")
        print("=" * 50 + "\n")


def print_usage():
    """使用方法を表示"""
    print("""
📚 AIガールフレンドボット - 知識インポートツール

使用方法:
    python knowledge_importer.py <コマンド> [引数]

コマンド:
    file <ファイルパス> [カテゴリ]     単一ファイルをインポート
    dir <ディレクトリパス> [カテゴリ]  ディレクトリ全体をインポート
    text <テキスト内容> [カテゴリ]     テキストをインポート
    stats                     学習統計を表示

サポートされている形式:
    .txt, .md, .json, .yaml, .yml

例:
    python knowledge_importer.py file docs/about_user.txt personal
    python knowledge_importer.py dir knowledge/ general
    python knowledge_importer.py text "ユーザーの誕生日は3月15日" personal
    python knowledge_importer.py stats
""")


async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='知識インポートツール')
    parser.add_argument('command', choices=['file', 'dir', 'text', 'stats'],
                       help='インポートコマンド')
    parser.add_argument('path', nargs='?', help='ファイル/ディレクトリパスまたはテキスト内容')
    parser.add_argument('--category', '-c', default='general',
                       help='知識カテゴリ (default: general)')
    
    args = parser.parse_args()
    
    tool = KnowledgeImportTool()
    await tool.initialize()
    
    if args.command == 'file':
        if not args.path:
            print("❌ ファイルパスを提供してください")
            return
        await tool.import_file(args.path, args.category)
    
    elif args.command == 'dir':
        if not args.path:
            print("❌ ディレクトリパスを提供してください")
            return
        await tool.import_directory(args.path, args.category)
    
    elif args.command == 'text':
        if not args.path:
            print("❌ テキスト内容を提供してください")
            return
        await tool.import_text(args.path, args.category)
    
    elif args.command == 'stats':
        tool.show_stats()


if __name__ == "__main__":
    asyncio.run(main())
