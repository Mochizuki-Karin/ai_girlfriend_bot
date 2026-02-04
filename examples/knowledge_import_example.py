#!/usr/bin/env python3
"""
知識インポートの例
さまざまな形式の知識のインポート方法を示す
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.knowledge_system import KnowledgeImporter, KnowledgeItem


async def import_text_examples():
    """テキストインポートの例"""
    
    importer = KnowledgeImporter("./data/knowledge_examples")
    
    # 例1：ユーザーの個人情報をインポート
    personal_info = """
ユーザーの名前は花子で、25歳でソフトウェアエンジニアです。
花子は東京出身で、現在は大阪で働いています。
彼女はプログラミング、ゲーム、映画鑑賞が好きです。
花子の誕生日は1999年5月20日です。
「たま」っていう名前の猫を飼っています。
"""
    
    items = await importer.import_text(
        personal_info,
        source="user_profile",
        category="personal"
    )
    print(f"✅ 個人情報のインポート: {len(items)} 件")
    
    # 例2：ユーザーの好みをインポート
    preferences = """
花子が一番好きな食べ物は火鍋で、特に辛い火鍋が大好きです。
コーラを飲むのが好きで、コーヒーはあまり好きではありません。
好きな映画のジャンルはSFとアクションです。
好きな監督はノーランです。
好きな音楽のジャンルはエレクトロニックとロックです。
好きなバンドはLinkin Parkです。
"""
    
    items = await importer.import_text(
        preferences,
        source="user_preferences",
        category="preference"
    )
    print(f"✅ 好み情報のインポート: {len(items)} 件")
    
    # 例3：重要なイベントをインポート
    events = """
2024年1月15日：花子が新会社に入社
2024年2月14日：AIガールフレンドとの初チャット
2024年3月1日：シニアエンジニアに昇進
"""
    
    items = await importer.import_text(
        events,
        source="user_events",
        category="event"
    )
    print(f"✅ イベント情報のインポート: {len(items)} 件")


async def create_structured_knowledge():
    """構造化知識の作成"""
    
    # 知識項目リストを作成
    knowledge_items = [
        KnowledgeItem(
            id="user_name_001",
            content="ユーザーの名前は花子",
            source="user_told",
            source_type="conversation",
            category="fact",
            importance=0.9
        ),
        KnowledgeItem(
            id="user_job_001",
            content="ユーザーはソフトウェアエンジニア",
            source="user_told",
            source_type="conversation",
            category="fact",
            importance=0.8
        ),
        KnowledgeItem(
            id="user_like_001",
            content="ユーザーは辛い火鍋が好き",
            source="user_told",
            source_type="conversation",
            category="preference",
            importance=0.7
        ),
        KnowledgeItem(
            id="user_pet_001",
            content="ユーザーは「たま」という名前の猫を飼っている",
            source="user_told",
            source_type="conversation",
            category="fact",
            importance=0.8
        ),
    ]
    
    print(f"\n📚 {len(knowledge_items)} 件の構造化知識を作成しました:")
    for item in knowledge_items:
        print(f"  • [{item.category}] {item.content}")
    
    return knowledge_items


def create_knowledge_files():
    """知識ファイルの例を作成"""
    
    # 例のディレクトリを作成
    example_dir = Path("./examples/knowledge_files")
    example_dir.mkdir(parents=True, exist_ok=True)
    
    # Markdownファイルを作成
    md_content = """# 花子について

## 基本情報

- **名前**: 花子
- **年齢**: 25歳
- **職業**: ソフトウェアエンジニア
- **所在地**: 大阪

## 趣味

1. プログラミング - 特にPythonとGo
2. ゲーム - RPGとストラテジーゲームが好き
3. 映画鑑賞 - SF映画の愛好家
4. 旅行 - 日本、タイに行ったことがある

## 好きな食べ物

- 火鍋（辛い）
- 和食
- バーベキュー
- タピオカミルクティー

## 重要な日付

- 誕生日：5月20日
- 入社記念日：1月15日
"""
    
    md_file = example_dir / "about_xiaoming.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"✅ Markdownファイルの作成: {md_file}")
    
    # JSONファイルを作成
    import json
    json_content = {
        "user_profile": {
            "name": "花子",
            "age": 25,
            "job": "ソフトウェアエンジニア",
            "location": "大阪"
        },
        "preferences": {
            "foods": ["火鍋", "和食", "バーベキュー"],
            "movies": ["SF", "アクション"],
            "games": ["RPG", "ストラテジー"]
        },
        "memories": [
            {"date": "2024-01-15", "event": "新会社に入社"},
            {"date": "2024-02-14", "event": "初めてのチャット"}
        ]
    }
    
    json_file = example_dir / "xiaoming_data.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_content, f, ensure_ascii=False, indent=2)
    print(f"✅ JSONファイルの作成: {json_file}")
    
    # プレーンテキストファイルを作成
    txt_content = """花子の日常習慣

毎朝8時に起床
まず温かいお湯を飲むのが好き
通勤時間は約40分
昼休みにゲームをする
夜は通常12時に就寝
週末は寝坊するのが好き

感情のきっかけ
嬉しい：認められること、目標を達成すること、プレゼントをもらうこと
悲しい：批評されること、プロジェクトの遅延、孤独
怒り：誤解されること、約束を守らないこと
"""
    
    txt_file = example_dir / "xiaoming_habits.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    print(f"✅ テキストファイルの作成: {txt_file}")
    
    return example_dir


def create_learning_prompt():
    """LLM学習用のプロンプトを作成"""
    
    prompt = """以下のユーザーに関する情報から主要な洞察を抽出してください：

ユーザー情報：
- 名前：花子
- 年齢：25歳
- 職業：ソフトウェアエンジニア
- 所在地：大阪
- 趣味：プログラミング、ゲーム、映画鑑賞、旅行
- 好きな食べ物：火鍋、和食、バーベキュー、タピオカミルクティー
- ペット：「たま」という名前の猫

分析して出力してください：
1. 性格の特徴
2. 考えられる価値観
3. ユーザーとの接し方の提案
4. 適した会話の話題
5. 避けるべき話題

JSON形式で出力してください。"""
    
    print("\n🤖 LLM 学習プロンプト:")
    print(prompt)
    
    return prompt


async def main():
    """メイン関数"""
    print("=" * 60)
    print("📚 知識インポートの例")
    print("=" * 60)
    
    # テキストインポートの例
    print("\n1️⃣ テキスト知識のインポート...")
    await import_text_examples()
    
    # 構造化知識の作成
    print("\n2️⃣ 構造化知識の作成...")
    await create_structured_knowledge()
    
    # 知識ファイルの作成
    print("\n3️⃣ 知識ファイルの作成...")
    create_knowledge_files()
    
    # 学習プロンプトの作成
    print("\n4️⃣ LLM学習プロンプトの作成...")
    create_learning_prompt()
    
    print("\n" + "=" * 60)
    print("✅ 例の完了！")
    print("=" * 60)
    print("\n💡 ヒント:")
    print("  - tools/knowledge_importer.py を使用してファイルをインポート")
    print("  - .txt, .md, .json, .yaml 形式をサポート")
    print("  - インポートされた知識は自動的にpersonalityに統合されます")


if __name__ == "__main__":
    asyncio.run(main())
