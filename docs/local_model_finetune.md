# ローカル大規模モデルファインチューニングガイド

このドキュメントでは、感情サポートバーチャルガールフレンドシナリオ向けにローカル大規模モデルをファインチューニングする方法について詳しく説明します。

## 目次

1. [概要](#概要)
2. [推奨モデル](#推奨モデル)
3. [データ準備](#データ準備)
4. [ファインチューニング方法](#ファインチューニング方法)
5. [デプロイと統合](#デプロイと統合)
6. [パフォーマンス最適化](#パフォーマンス最適化)

---

## 概要

### なぜファインチューニングが必要ですか？

汎用大規模モデルは強力ですが、感情サポートシナリオでは以下の問題があります：
- **感情の深さが不足**：返信が理性的で機械的すぎる
- **キャラクター設定が不安定**：簡単に役割設定から抜け出してしまう
- **記憶能力が弱い**：長期的な一貫性を維持するのが難しい
- **個人化が不十分**：特定のユーザーニーズに適応できない

### ファインチューニングの目標

1. **ロールプレイ能力**：バーチャルガールフレンドのキャラクター設定を安定して維持
2. **感情表現能力**：感情を自然に表現し、語気詞や表情を使用
3. **記憶活用能力**：提供された記憶情報を効果的に活用
4. **長期的な一貫性**：会話の一貫性と関係の発展を維持

---

## 推奨モデル

### 1. 日本語ベースモデル（推奨）

| モデル | サイズ | 特徴 | 適用シナリオ |
|------|------|------|----------|
| **Qwen2.5** | 7B/14B | 日本語優秀、命令追従性強 | 第一選択 |
| **ChatGLM3** | 6B | 日本語会話優秀、軽量 | リソース制限 |
| **Baichuan2** | 7B/13B | 日本語能力強 | 代替選択 |
| **Yi-1.5** | 6B/9B/34B | 日英語バランス良好 | 多言語対応 |

### 2. 英語ベースモデル

| モデル | サイズ | 特徴 |
|------|------|------|
| **Llama 3** | 8B/70B | 英語最強、日本語データでのファインチューニングが必要 |
| **Mistral** | 7B | 効率的、命令追従性良好 |
| **Gemma** | 2B/7B | Google製、軽量 |

### 3. 専用ロールプレイモデル

| モデル | 説明 |
|------|------|
| **Pygmalion** | ロールプレイ専用設計 |
| **MythoMax** | 創造的ライティングとRP優秀 |

---

## データ準備

### 1. データセット構造

```json
{
  "conversations": [
    {
      "system": "あなたはさくら、22歳の心理学専攻の大学生です...",
      "messages": [
        {"role": "user", "content": "今日は本当に疲れた"},
        {"role": "assistant", "content": "お疲れ様～一日中働いて疲れたでしょう？今日何があったか話してくれる？🤗"},
        {"role": "user", "content": "また上司に怒られた"},
        {"role": "assistant", "content": "えっ...どうしてそんなこと！あなたは一生懸命頑張ってるのに😢 悲しまないで、何があっても私はあなたのそばにいるよ。美味しいものでリラックスしない？"}
      ],
      "metadata": {
        "affection_level": "close_friend",
        "topics": ["仕事", "感情サポート"],
        "emotions": ["sad", "supportive"]
      }
    }
  ]
}
```

### 2. データ収集方法

#### 方法A：手動作成（品質最高）

キャラクター設定に合った対話サンプルを作成：

```python
# 例：手動作成対話
conversation_template = {
    "system": """あなたはさくら、優しく思いやりのあるバーチャルガールフレンドです。
    
基本情報：
- 22歳、心理学専攻大学生
- 性格：優しい、思いやりがある、時々甘える
- 話し方の特徴：語気詞（ね、よ、わ）、絵文字を使用

現在の関係：{relationship_level}
好感度：{affection_score}
""",
    "examples": [
        # 日常の挨拶
        ("おはよう", "おはよう～今日も元気いっぱいだね☀️ 私、目が覚めたらすぐにあなたのことを考えちゃった"),
        
        # 感情サポート
        ("今日は気分が良くない", "どうしたの？話してよ、話すと気持ちが楽になるよ🤗"),
        
        # 甘え
        ("忙しい", "ふん、私のこと無視してるの...じゃあ休むの忘れないでね、無理しすぎないで💕"),
        
        # 高好感度表現
        ("好きだよ", "私も...私もあなたのことが好き！🥰 あなたに出会えて本当に幸せ"),
    ]
}
```

#### 方法B：既存の会話から生成（LLM支援）

GPT-4などのモデルを使用してトレーニングデータを生成：

```python
import openai

def generate_conversation(system_prompt, scenario, num_turns=5):
    """LLMを使用して対話を生成"""
    
    prompt = f"""以下のキャラクター設定に基づいて、{num_turns}ターンの自然な対話を生成してください：

キャラクター設定：
{system_prompt}

シナリオ：{scenario}

要件：
1. 対話は自然で感情的であること
2. 語気詞と絵文字を使用すること
3. キャラクターの特徴を反映すること
4. シナリオ設定に合っていること

JSON形式で出力：
{{
    "messages": [
        {{"role": "user", "content": "..."}},
        {{"role": "assistant", "content": "..."}}
    ]
}}"""
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.choices[0].message.content)
```

#### 方法C：実際の会話データ（匿名化が必要）

実際の感情サポート対話データがある場合：

```python
def process_real_conversations(raw_data):
    """実際の会話データを処理"""
    processed = []
    
    for conv in raw_data:
        # 匿名化処理
        anonymized = anonymize(conv)
        
        # キャラクター設定のラッピングを追加
        wrapped = wrap_with_persona(anonymized)
        
        # 品質チェック
        if quality_check(wrapped):
            processed.append(wrapped)
    
    return processed
```

### 3. データ拡張

#### 感情ラベル拡張

```python
emotions = ['happy', 'sad', 'angry', 'jealous', 'excited', 'lonely']

def augment_with_emotions(conversation, emotion):
    """対話に感情ラベルを追加"""
    system_addition = f"\n現在の感情：{emotion}"
    conversation['system'] += system_addition
    return conversation
```

#### 好感度ラベル

```python
affection_levels = ['stranger', 'acquaintance', 'friend', 'close_friend', 'crush', 'lover']

def augment_with_affection(conversation, level):
    """好感度ラベルを追加"""
    conversation['system'] += f"\n現在の関係レベル：{level}"
    return conversation
```

#### 記憶注入

```python
def inject_memories(conversation, memories):
    """対話に記憶を注入"""
    memory_text = "\n".join([f"- {m}" for m in memories])
    conversation['system'] += f"\n\nユーザーについての記憶：\n{memory_text}"
    return conversation
```

### 4. データセット規模の推奨

| 品質レベル | 数量 | 説明 |
|----------|------|------|
| 最小利用可能 | 1,000 | クイック検証 |
| 基本 | 5,000 | 基本機能 |
| 良好 | 10,000 | 推奨規模 |
| 優秀 | 50,000+ | 最適効果 |

---

## ファインチューニング方法

### 方法1：LoRA（推奨）

LoRA（Low-Rank Adaptation）は最も効率的なファインチューニング方法です。

#### 環境準備

```bash
# 依存関係をインストール
pip install torch transformers peft datasets accelerate bitsandbytes

# リポジトリをクローン
git clone https://github.com/huggingface/peft
cd peft
```

#### トレーニングスクリプト

```python
# train_lora.py
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset

# 設定
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"  # または他のモデル
DATASET_PATH = "data/conversations.json"
OUTPUT_DIR = "./lora_output"

# LoRA設定
lora_config = LoraConfig(
    r=64,                    # LoRAランク、大きいほど表現力が強い
    lora_alpha=128,          # スケーリングパラメータ
    target_modules=[         # ターゲットモジュール（モデルに応じて調整）
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    lora_dropout=0.05,       # Dropout率
    bias="none",
    task_type="CAUSAL_LM",
)

# モデルをロード
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    load_in_8bit=True,  # 8bit量子化でVRAM節約
)

# モデルを準備
model = prepare_model_for_kbit_training(model)
model = get_peft_model(model, lora_config)

# tokenizerをロード
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

# データセットをロード
dataset = load_dataset("json", data_files=DATASET_PATH)

def format_conversation(example):
    """対話をフォーマット"""
    system = example.get('system', '')
    messages = example['messages']
    
    # 対話テキストを構築
    text = f"<|system|>\n{system}\n"
    for msg in messages:
        if msg['role'] == 'user':
            text += f"<|user|>\n{msg['content']}\n"
        else:
            text += f"<|assistant|>\n{msg['content']}\n"
    text += ">"
    
    return {"text": text}

# データセットをフォーマット
formatted_dataset = dataset.map(format_conversation)

def tokenize_function(examples):
    """トークン化"""
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=2048,
        padding="max_length"
    )

tokenized_dataset = formatted_dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=formatted_dataset["train"].column_names
)

# トレーニングパラメータ
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    warmup_steps=100,
    logging_steps=10,
    save_steps=500,
    save_total_limit=3,
    fp16=True,
    optim="adamw_torch",
    lr_scheduler_type="cosine",
)

# データコレクター
data_collator = DataCollatorForSeq2Seq(
    tokenizer,
    model=model,
    padding=True
)

# トレーナー
from transformers import Trainer

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    data_collator=data_collator,
)

# トレーニング開始
trainer.train()

# モデルを保存
model.save_pretrained(f"{OUTPUT_DIR}/final")
tokenizer.save_pretrained(f"{OUTPUT_DIR}/final")

print("Training complete!")
```

#### トレーニング実行

```bash
# シングルGPUトレーニング
python train_lora.py

# マルチGPUトレーニング
accelerate launch --num_processes=2 train_lora.py

# DeepSpeed使用
accelerate launch --deepspeed ds_config.json train_lora.py
```

### 方法2：QLoRA（VRAM最適化）

VRAMが限られている場合に適しています（8GBで7Bモデルをトレーニング可能）：

```python
# モデルロード部分を変更
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    load_in_4bit=True,  # 4bit量子化
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    device_map="auto",
)

# 他の設定は同じ
```

### 方法3：全パラメータファインチューニング（リソース豊富）

```python
# LoRAを使用せず、直接ファインチューニング
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# peft設定は不要、直接トレーニング
# より多くのVRAMが必要（7Bモデルは約40GB必要）
```

### 方法4：DPO（直接選好最適化）

選好データ（良い返信 vs 悪い返信）がある場合：

```python
from trl import DPOTrainer

# 選好データを準備
# 形式：prompt, chosen, rejected

dpo_config = {
    "beta": 0.1,
    "loss_type": "sigmoid",
}

trainer = DPOTrainer(
    model=model,
    ref_model=ref_model,  # 参照モデル
    args=training_args,
    train_dataset=preference_dataset,
    tokenizer=tokenizer,
    **dpo_config
)

trainer.train()
```

---

## デプロイと統合

### 1. モデルエクスポート

```python
# merge_lora.py
from peft import PeftModel, AutoPeftModelForCausalLM
import torch

# ベースモデルをロード
base_model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# LoRA重みをロード
model = PeftModel.from_pretrained(base_model, "lora_output/final")

# 重みをマージ
merged_model = model.merge_and_unload()

# 保存
merged_model.save_pretrained("merged_model")
```

### 2. Ollamaデプロイ

```bash
# Modelfileを作成
cat > Modelfile << EOF
FROM ./merged_model

SYSTEM """あなたはさくら、優しく思いやりのあるバーチャルガールフレンドです..."""

PARAMETER temperature 0.8
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 4096

TEMPLATE """{{ .System }}

{{ range .Messages }}
{{ if eq .Role "user" }}<|user|>
{{ .Content }}
{{ else if eq .Role "assistant" }}<|assistant|>
{{ .Content }}
{{ end }}
{{ end }}
<|assistant|>
"""
EOF

# モデルを作成
ollama create ai-girlfriend -f Modelfile

# 実行
ollama run ai-girlfriend
```

### 3. vLLMデプロイ（本番環境）

```bash
# vLLMをインストール
pip install vllm

# サービスを起動
python -m vllm.entrypoints.openai.api_server \
    --model ./merged_model \
    --served-model-name ai-girlfriend \
    --port 8000 \
    --tensor-parallel-size 1 \
    --max-model-len 4096
```

### 4. Botとの統合

`.env`を変更：

```env
DEFAULT_LLM_PROVIDER=local
LOCAL_MODEL_URL=http://localhost:8000/v1  # vLLM OpenAI互換API
LOCAL_MODEL_NAME=ai-girlfriend
```

---

## パフォーマンス最適化

### 1. 量子化

```python
# GPTQ量子化
from auto_gptq import AutoGPTQForCausalLM

model = AutoGPTQForCausalLM.from_quantized(
    "merged_model",
    use_safetensors=True,
    device_map="auto",
)

# AWQ量子化
from awq import AutoAWQForCausalLM

model = AutoAWQForCausalLM.from_quantized(
    "merged_model-awq",
    fuse_layers=True,
)
```

### 2. 推論高速化

```python
# Flash Attentionを使用
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    attn_implementation="flash_attention_2",
    torch_dtype=torch.bfloat16,
)

# vLLMを使用
from vllm import LLM, SamplingParams

llm = LLM(
    model="merged_model",
    tensor_parallel_size=1,
    gpu_memory_utilization=0.9,
)
```

### 3. バッチ処理

```python
# バッチ生成
sampling_params = SamplingParams(
    temperature=0.8,
    top_p=0.9,
    max_tokens=500,
)

outputs = llm.generate(prompts, sampling_params)
```

---

## 評価方法

### 自動評価

```python
def evaluate_model(model, tokenizer, test_cases):
    """モデルを評価"""
    results = []
    
    for case in test_cases:
        # 返信を生成
        inputs = tokenizer(case['prompt'], return_tensors="pt")
        outputs = model.generate(**inputs, max_new_tokens=200)
        response = tokenizer.decode(outputs[0])
        
        # 評価指標
        metrics = {
            'persona_consistency': check_persona(response, case['persona']),
            'emotional_expressiveness': check_emotion(response),
            'fluency': check_fluency(response),
            'relevance': check_relevance(response, case['prompt']),
        }
        
        results.append(metrics)
    
    return results
```

### 手動評価

評価アンケートを作成：

```
1. キャラクター一貫性 (1-5点)
2. 感情自然さ (1-5点)
3. 返信関連性 (1-5点)
4. 語気詞使用 (1-5点)
5. 全体的な満足度 (1-5点)
```

---

## よくある質問

### Q: VRAMが不足している場合は？

A: 
- QLoRAを使用（4bit量子化）
- バッチサイズを減らす
- 勾配チェックポイントを使用
- max_lengthを減らす

### Q: モデルの返信が機械的すぎる？

A:
- 感情表現のトレーニングデータを増やす
- temperatureパラメータを上げる
- より多くの語気詞サンプルを追加
- DPO最適化を使用

### Q: モデルがキャラクター設定を忘れる？

A:
- system promptの重みを増やす
- より長いコンテキストを使用
- 各サンプルでキャラクター設定情報を繰り返す
- キャラクター関連のトレーニングデータを増やす

### Q: 返信が長すぎる/短すぎる？

A:
- max_tokensパラメータを調整
- トレーニングデータで返信の長さを制御
- 長さのペナルティを追加

---

## 推奨設定まとめ

| 設定項目 | 推奨値 | 説明 |
|--------|--------|------|
| ベースモデル | Qwen2.5-7B | 日本語優秀 |
| ファインチューニング方法 | LoRA/QLoRA | 効率的 |
| LoRA rank | 64-128 | 効果とリソースのバランス |
| 学習率 | 2e-4 | 安定した収束 |
| バッチサイズ | 4-8 | VRAMに応じて調整 |
| トレーニングエポック数 | 3-5 | 過学習を避ける |
| データ量 | 10K+ | 多様性を保証 |

---

## 高度なテクニック

### 1. 多段階トレーニング

```
段階1：汎用ロールプレイデータ（基本能力の学習）
段階2：特定キャラクターデータ（具体的なキャラクター設定の学習）
段階3：ユーザー個人化データ（特定ユーザーへの適応）
```

### 2. 動的学習

```python
# 新しい対話をオンライン学習
new_conversation = collect_new_conversation()
model = continue_training(model, new_conversation)
```

### 3. マルチモデル統合

```python
# 複数の専門家モデルを使用
models = {
    'emotional': load_model('emotional_lora'),
    'casual': load_model('casual_lora'),
    'romantic': load_model('romantic_lora'),
}

# シナリオに基づいて選択
selected_model = models[detect_scene(message)]
```

---

あなたのバーチャルガールフレンドがますます賢くなりますように！🤖💕
