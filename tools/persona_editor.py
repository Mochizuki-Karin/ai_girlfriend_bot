#!/usr/bin/env python3
"""
人格エディター - 対話的にバーチャルガールフレンドの人格を作成・編集
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any


class PersonaEditor:
    """人格エディター"""
    
    def __init__(self):
        self.persona = self._create_template()
    
    def _create_template(self) -> Dict[str, Any]:
        """人格テンプレートを作成"""
        return {
            'basic_info': {
                'name': '',
                'age': 20,
                'birthday': '',
                'zodiac': '',
                'location': '',
                'occupation': '',
                'major': ''
            },
            'personality': {
                'traits': {
                    'openness': 70,
                    'conscientiousness': 60,
                    'extraversion': 65,
                    'agreeableness': 80,
                    'neuroticism': 40
                },
                'description': ''
            },
            'speech_style': {
                'tone': '',
                'particles': [],
                'emojis': [],
                'habits': [],
                'sentence_patterns': []
            },
            'background': {
                'story': '',
                'hobbies': [],
                'favorite_foods': [],
                'dislikes': []
            },
            'relationship': {
                'relationship_type': '',
                'first_impression': '',
                'intimacy': [],
                'boundaries': []
            },
            'emotional_triggers': {
                'happy': [],
                'sad': [],
                'jealous': [],
                'angry': []
            },
            'response_preferences': {
                'message_length': 3,
                'typing_delay': {'min': 1, 'max': 4},
                'initiative_rate': 0.3,
                'initiative_topics': []
            }
        }
    
    def interactive_create(self):
        """対話的に人格を作成"""
        print("=" * 50)
        print("🎭 バーチャルガールフレンド人格エディター")
        print("=" * 50)
        print()
        
        # 基本情報
        print("【基本情報】")
        self.persona['basic_info']['name'] = input("名前: ") or "美月"
        self.persona['basic_info']['age'] = int(input("年齢: ") or "22")
        self.persona['basic_info']['location'] = input("所在地: ") or "東京"
        self.persona['basic_info']['occupation'] = input("職業: ") or "大学生"
        print()
        
        # 性格
        print("【性格特徴】")
        print("彼女の性格を説明してください（複数行入力、空行で終了）：")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        self.persona['personality']['description'] = '\n'.join(lines) or "優しく思いやりがあり、人の気持ちを理解できる"
        print()
        
        # 話し方のスタイル
        print("【話し方のスタイル】")
        self.persona['speech_style']['tone'] = input("口調の特徴: ") or "優しい、親しみやすい、少し甘え気味"
        
        particles = input("よく使う語気詞（カンマ区切り）: ") or "ね,よ,わ,かしら,の"
        self.persona['speech_style']['particles'] = [p.strip() for p in particles.split(',')]
        
        emojis = input("よく使う絵文字（カンマ区切り）: ") or "😊,🥰,😉,🤗,✨,💕"
        self.persona['speech_style']['emojis'] = [e.strip() for e in emojis.split(',')]
        print()
        
        # 背景ストーリー
        print("【背景ストーリー】")
        print("彼女の背景ストーリーを説明してください（複数行入力、空行で終了）：")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        self.persona['background']['story'] = '\n'.join(lines) or f"あなたは{self.persona['basic_info']['occupation']}で、性格は優しく思いやりがある。"
        print()
        
        # 趣味・興味
        hobbies = input("趣味・興味（カンマ区切り）: ") or "読書,音楽を聴く,映画鑑賞,手作り"
        self.persona['background']['hobbies'] = [h.strip() for h in hobbies.split(',')]
        print()
        
        # 関係設定
        print("【関係設定】")
        self.persona['relationship']['relationship_type'] = input("関係タイプ: ") or "曖昧な関係の友達"
        print()
        
        print("✅ 人格作成が完了しました！")
    
    def save(self, filepath: str):
        """人格を保存"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self.persona, f, allow_unicode=True, default_flow_style=False)
        
        print(f"💾 人格が保存されました: {filepath}")
    
    def load(self, filepath: str):
        """人格を読み込み"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.persona = yaml.safe_load(f)
        print(f"📂 人格を読み込みました: {filepath}")
    
    def preview(self):
        """人格をプレビュー"""
        print("\n" + "=" * 50)
        print("📋 人格プレビュー")
        print("=" * 50)
        
        basic = self.persona['basic_info']
        print(f"\n名前: {basic['name']}")
        print(f"年齢: {basic['age']}")
        print(f"職業: {basic['occupation']}")
        print(f"所在地: {basic['location']}")
        
        print(f"\n性格:\n{self.persona['personality']['description'][:200]}...")
        
        speech = self.persona['speech_style']
        print(f"\n口調: {speech['tone']}")
        print(f"語気詞: {', '.join(speech['particles'][:5])}")
        print(f"絵文字: {', '.join(speech['emojis'][:5])}")
        
        print("\n" + "=" * 50)


def main():
    """メイン関数"""
    editor = PersonaEditor()
    
    print("操作を選択してください:")
    print("1. 新しい人格を作成")
    print("2. 既存の人格を編集")
    
    choice = input("\n選択 (1/2): ").strip()
    
    if choice == "1":
        editor.interactive_create()
        
        filename = input("\n保存ファイル名（例: my_girlfriend.yaml）: ") or "custom_persona.yaml"
        filepath = f"config/{filename}"
        editor.save(filepath)
        editor.preview()
        
    elif choice == "2":
        # 既存の人格をリストアップ
        config_dir = Path("config")
        personas = list(config_dir.glob("*.yaml"))
        
        if not personas:
            print("既存の人格ファイルが見つかりません")
            return
        
        print("\n既存の人格:")
        for i, p in enumerate(personas, 1):
            print(f"{i}. {p.name}")
        
        idx = int(input("\n編集する人格を選択: ")) - 1
        if 0 <= idx < len(personas):
            editor.load(str(personas[idx]))
            editor.preview()
            
            print("\n編集オプション:")
            print("1. 基本情報を変更")
            print("2. 性格を変更")
            print("3. 話し方を変更")
            print("4. すべて再編集")
            
            edit_choice = input("\n選択: ").strip()
            
            if edit_choice == "4":
                editor.interactive_create()
                editor.save(str(personas[idx]))
            else:
                print("機能開発中...")
        
    else:
        print("無効な選択")


if __name__ == "__main__":
    main()
