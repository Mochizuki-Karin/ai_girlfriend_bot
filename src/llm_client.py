"""
LLMクライアント - 複数プロバイダ対応（OpenAI、Google、Anthropic、ローカルモデル）
"""
import os
import json
import asyncio
from typing import AsyncGenerator, Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from loguru import logger

import httpx


@dataclass
class LLMResponse:
    """LLMレスポンス"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    raw_response: Any = None


@dataclass
class LLMConfig:
    """LLM設定"""
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 60


class BaseLLMClient(ABC):
    """LLMクライアント基底クラス"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        system_prompt: str = None,
        **kwargs
    ) -> LLMResponse:
        """テキスト生成"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self, 
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """ストリーム生成"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """チャット生成"""
        pass
    
    async def close(self):
        """クライアントを閉じる"""
        await self.client.aclose()


class OpenAIClient(BaseLLMClient):
    """OpenAIクライアント - OpenAI APIと互換APIをサポート"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: str = None,
        **kwargs
    ) -> LLMResponse:
        """テキスト生成"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return await self.chat(messages, **kwargs)
    
    async def generate_stream(
        self, 
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """ストリーム生成"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async for chunk in self.chat_stream(messages, **kwargs):
            yield chunk
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """チャット生成"""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens)
        }
        
        try:
            response = await self.client.post(
                url, 
                headers=self.headers, 
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                content=data['choices'][0]['message']['content'],
                model=data.get('model', self.config.model),
                usage=data.get('usage', {}),
                finish_reason=data['choices'][0].get('finish_reason', 'stop'),
                raw_response=data
            )
        
        except httpx.HTTPError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """ストリーミングチャット"""
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get('temperature', self.config.temperature),
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "stream": True
        }
        
        try:
            async with self.client.stream(
                "POST", 
                url, 
                headers=self.headers, 
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if chunk['choices'][0].get('delta', {}).get('content'):
                                yield chunk['choices'][0]['delta']['content']
                        except json.JSONDecodeError:
                            continue
        
        except httpx.HTTPError as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise


class GoogleClient(BaseLLMClient):
    """Google Geminiクライアント"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.api_key = config.api_key
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: str = None,
        **kwargs
    ) -> LLMResponse:
        """テキスト生成"""
        url = f"{self.base_url}/models/{self.config.model}:generateContent"
        
        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {system_prompt}"}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "maxOutputTokens": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        try:
            response = await self.client.post(
                url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            content = data['candidates'][0]['content']['parts'][0]['text']
            
            return LLMResponse(
                content=content,
                model=self.config.model,
                usage=data.get('usageMetadata', {}),
                finish_reason=data['candidates'][0].get('finishReason', 'STOP'),
                raw_response=data
            )
        
        except httpx.HTTPError as e:
            logger.error(f"Google API error: {e}")
            raise
    
    async def generate_stream(
        self, 
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """ストリーム生成"""
        # Google APIストリーム実装
        response = await self.generate(prompt, system_prompt, **kwargs)
        yield response.content
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """チャット生成"""
        # メッセージ形式を変換
        contents = []
        for msg in messages:
            role = "user" if msg['role'] == 'user' else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg['content']}]
            })
        
        url = f"{self.base_url}/models/{self.config.model}:generateContent"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "maxOutputTokens": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        try:
            response = await self.client.post(
                url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            content = data['candidates'][0]['content']['parts'][0]['text']
            
            return LLMResponse(
                content=content,
                model=self.config.model,
                usage=data.get('usageMetadata', {}),
                finish_reason=data['candidates'][0].get('finishReason', 'STOP'),
                raw_response=data
            )
        
        except httpx.HTTPError as e:
            logger.error(f"Google API error: {e}")
            raise


class AnthropicClient(BaseLLMClient):
    """Anthropic Claudeクライアント"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: str = None,
        **kwargs
    ) -> LLMResponse:
        """テキスト生成"""
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, system_prompt, **kwargs)
    
    async def generate_stream(
        self, 
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """ストリーム生成"""
        messages = [{"role": "user", "content": prompt}]
        async for chunk in self.chat_stream(messages, system_prompt, **kwargs):
            yield chunk
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        **kwargs
    ) -> LLMResponse:
        """チャット生成"""
        url = f"{self.base_url}/messages"
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "temperature": kwargs.get('temperature', self.config.temperature)
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = await self.client.post(
                url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                content=data['content'][0]['text'],
                model=data.get('model', self.config.model),
                usage=data.get('usage', {}),
                finish_reason=data.get('stop_reason', 'end_turn'),
                raw_response=data
            )
        
        except httpx.HTTPError as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """ストリーミングチャット"""
        url = f"{self.base_url}/messages"
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get('max_tokens', self.config.max_tokens),
            "temperature": kwargs.get('temperature', self.config.temperature),
            "stream": True
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            async with self.client.stream(
                "POST",
                url,
                headers=self.headers,
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            chunk = json.loads(data)
                            if chunk.get('type') == 'content_block_delta':
                                yield chunk['delta'].get('text', '')
                        except json.JSONDecodeError:
                            continue
        
        except httpx.HTTPError as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise


class LocalModelClient(BaseLLMClient):
    """ローカルモデルクライアント - Ollama、vLLMなどをサポート"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: str = None,
        **kwargs
    ) -> LLMResponse:
        """テキスト生成"""
        # Ollama API
        url = f"{self.base_url}/api/generate"
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        payload = {
            "model": self.config.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "num_predict": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                content=data['response'],
                model=self.config.model,
                usage={},
                finish_reason='stop',
                raw_response=data
            )
        
        except httpx.HTTPError as e:
            logger.error(f"Local model API error: {e}")
            raise
    
    async def generate_stream(
        self, 
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """ストリーム生成"""
        url = f"{self.base_url}/api/generate"
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        payload = {
            "model": self.config.model,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "num_predict": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        try:
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if 'response' in data:
                                yield data['response']
                        except json.JSONDecodeError:
                            continue
        
        except httpx.HTTPError as e:
            logger.error(f"Local model streaming error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> LLMResponse:
        """チャット生成 - Ollama chat API"""
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get('temperature', self.config.temperature),
                "num_predict": kwargs.get('max_tokens', self.config.max_tokens)
            }
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                content=data['message']['content'],
                model=self.config.model,
                usage={},
                finish_reason='stop',
                raw_response=data
            )
        
        except httpx.HTTPError as e:
            logger.error(f"Local model chat error: {e}")
            raise


class LLMClientManager:
    """LLMクライアントマネージャー - 複数プロバイダを管理"""
    
    def __init__(self):
        self.clients: Dict[str, BaseLLMClient] = {}
        self.default_provider: Optional[str] = None
    
    def register_client(self, name: str, client: BaseLLMClient, is_default: bool = False):
        """クライアントを登録"""
        self.clients[name] = client
        if is_default or not self.default_provider:
            self.default_provider = name
    
    def get_client(self, provider: str = None) -> BaseLLMClient:
        """クライアントを取得"""
        provider = provider or self.default_provider
        if provider not in self.clients:
            raise ValueError(f"Unknown provider: {provider}")
        return self.clients[provider]
    
    async def generate(
        self, 
        prompt: str, 
        provider: str = None,
        system_prompt: str = None,
        **kwargs
    ) -> LLMResponse:
        """指定プロバイダで生成"""
        client = self.get_client(provider)
        return await client.generate(prompt, system_prompt, **kwargs)
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        provider: str = None,
        **kwargs
    ) -> LLMResponse:
        """指定プロバイダでチャット"""
        client = self.get_client(provider)
        return await client.chat(messages, **kwargs)
    
    async def close_all(self):
        """すべてのクライアントを閉じる"""
        for client in self.clients.values():
            await client.close()


def create_llm_manager(settings) -> LLMClientManager:
    """設定からLLMマネージャーを作成"""
    manager = LLMClientManager()
    
    # OpenAI
    if settings.llm.openai_api_key:
        openai_config = LLMConfig(
            provider="openai",
            api_key=settings.llm.openai_api_key,
            base_url=settings.llm.openai_base_url,
            model=settings.llm.openai_model
        )
        manager.register_client(
            "openai", 
            OpenAIClient(openai_config),
            is_default=settings.llm.default_provider == "openai"
        )
    
    # Google
    if settings.llm.google_api_key:
        google_config = LLMConfig(
            provider="google",
            api_key=settings.llm.google_api_key,
            model=settings.llm.google_model
        )
        manager.register_client(
            "google",
            GoogleClient(google_config),
            is_default=settings.llm.default_provider == "google"
        )
    
    # Anthropic
    if settings.llm.anthropic_api_key:
        anthropic_config = LLMConfig(
            provider="anthropic",
            api_key=settings.llm.anthropic_api_key,
            model=settings.llm.anthropic_model
        )
        manager.register_client(
            "anthropic",
            AnthropicClient(anthropic_config),
            is_default=settings.llm.default_provider == "anthropic"
        )
    
    # Local Model
    local_config = LLMConfig(
        provider="local",
        base_url=settings.llm.local_model_url,
        model=settings.llm.local_model_name
    )
    manager.register_client(
        "local",
        LocalModelClient(local_config),
        is_default=settings.llm.default_provider == "local"
    )
    
    return manager
