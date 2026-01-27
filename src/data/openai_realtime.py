"""
OpenAI Realtime API Client for The Planeswalker Agent.

Provides both WebSocket-based Realtime API access and standard Chat API fallback.
The Realtime API enables low-latency, streaming responses ideal for interactive use.

Environment Variables:
    OPENAI_API_KEY: Your OpenAI API key
    OPENAI_REALTIME_ENDPOINT: WebSocket endpoint (default: wss://api.openai.com/v1/realtime)
    OPENAI_REALTIME_MODEL: Model to use (default: gpt-4o-realtime-preview-2024-12-17)
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, Callable, AsyncGenerator
from dataclasses import dataclass
import logging

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = None

try:
    from openai import OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    AsyncOpenAI = None
    AzureOpenAI = None
    AsyncAzureOpenAI = None

from src.config import config

logger = logging.getLogger(__name__)


@dataclass
class RealtimeResponse:
    """Response from the Realtime API."""
    text: str
    conversation_id: Optional[str] = None
    response_id: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    is_complete: bool = True


class OpenAIRealtimeClient:
    """
    Client for OpenAI's Realtime API using WebSockets.

    The Realtime API provides:
    - Low-latency streaming responses
    - Support for text and audio modalities
    - Session-based conversation management

    Usage:
        client = OpenAIRealtimeClient()

        # Async usage (recommended for Realtime API)
        async with client.connect() as session:
            response = await session.send_message("Hello!")
            print(response.text)

        # Sync usage (uses standard Chat API as fallback)
        response = client.chat("Hello!")
        print(response)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the OpenAI Realtime client.

        Args:
            api_key: OpenAI API key (defaults to config/env)
            endpoint: Realtime WebSocket endpoint (defaults to config/env)
            model: Model to use (defaults to config/env)
        """
        self.api_key = api_key or config.openai.api_key
        self.endpoint = endpoint or config.openai.get_realtime_url()
        self.model = model or config.openai.realtime_model
        self.chat_model = config.openai.chat_model
        self.is_azure = config.openai.is_azure
        self.api_version = config.openai.realtime_api_version

        if not self.api_key:
            logger.warning("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")

    @property
    def is_available(self) -> bool:
        """Check if the client is properly configured and dependencies are available."""
        return bool(self.api_key) and (WEBSOCKETS_AVAILABLE or OPENAI_AVAILABLE)

    @property
    def realtime_available(self) -> bool:
        """Check if Realtime API (WebSocket) is available."""
        return bool(self.api_key) and WEBSOCKETS_AVAILABLE

    @property
    def chat_available(self) -> bool:
        """Check if standard Chat API is available."""
        return bool(self.api_key) and OPENAI_AVAILABLE

    def connect(self) -> "RealtimeSession":
        """
        Create a Realtime API session context manager.

        Returns:
            RealtimeSession context manager for async usage

        Example:
            async with client.connect() as session:
                response = await session.send_message("Hello")
        """
        if not self.realtime_available:
            raise RuntimeError(
                "Realtime API not available. Install websockets: pip install websockets"
            )
        return RealtimeSession(self)

    def _get_sync_client(self):
        """Get the appropriate sync client (Azure or OpenAI)."""
        if self.is_azure:
            # Use Azure OpenAI client
            azure_endpoint = config.openai.azure_endpoint
            if not azure_endpoint and config.openai.realtime_endpoint:
                # Extract base URL from realtime endpoint
                endpoint = config.openai.realtime_endpoint
                if "wss://" in endpoint:
                    azure_endpoint = endpoint.replace("wss://", "https://").split("/openai")[0]
                elif "ws://" in endpoint:
                    azure_endpoint = endpoint.replace("ws://", "http://").split("/openai")[0]

            return AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=azure_endpoint,
                api_version=self.api_version,
            )
        else:
            return OpenAI(
                api_key=self.api_key,
                base_url=config.openai.api_endpoint,
            )

    def _get_async_client(self):
        """Get the appropriate async client (Azure or OpenAI)."""
        if self.is_azure:
            azure_endpoint = config.openai.azure_endpoint
            if not azure_endpoint and config.openai.realtime_endpoint:
                endpoint = config.openai.realtime_endpoint
                if "wss://" in endpoint:
                    azure_endpoint = endpoint.replace("wss://", "https://").split("/openai")[0]
                elif "ws://" in endpoint:
                    azure_endpoint = endpoint.replace("ws://", "http://").split("/openai")[0]

            return AsyncAzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=azure_endpoint,
                api_version=self.api_version,
            )
        else:
            return AsyncOpenAI(
                api_key=self.api_key,
                base_url=config.openai.api_endpoint,
            )

    def _get_model_name(self) -> str:
        """Get the model/deployment name to use for Chat API."""
        if self.is_azure:
            # For Azure, prefer chat-specific deployment, fall back to general deployment
            return (
                config.openai.azure_chat_deployment
                or config.openai.azure_deployment
                or self.chat_model
            )
        return self.chat_model

    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Send a message using the standard Chat API (synchronous fallback).

        Supports both OpenAI and Azure OpenAI endpoints.

        Args:
            message: User message to send
            system_prompt: Optional system prompt
            conversation_history: Optional list of previous messages

        Returns:
            Assistant's response text
        """
        if not self.chat_available:
            raise RuntimeError(
                "OpenAI Chat API not available. Install openai: pip install openai"
            )

        client = self._get_sync_client()
        model = self._get_model_name()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        logger.info(f"Chat API request - Azure: {self.is_azure}, Model: {model}")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=config.openai.temperature,
            max_tokens=config.openai.max_tokens,
        )

        return response.choices[0].message.content

    async def chat_async(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Send a message using the standard Chat API (async version).

        Supports both OpenAI and Azure OpenAI endpoints.

        Args:
            message: User message to send
            system_prompt: Optional system prompt
            conversation_history: Optional list of previous messages

        Returns:
            Assistant's response text
        """
        if not self.chat_available:
            raise RuntimeError(
                "OpenAI Chat API not available. Install openai: pip install openai"
            )

        client = self._get_async_client()
        model = self._get_model_name()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=config.openai.temperature,
            max_tokens=config.openai.max_tokens,
        )

        return response.choices[0].message.content

    async def chat_stream(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response using the standard Chat API.

        Supports both OpenAI and Azure OpenAI endpoints.

        Args:
            message: User message to send
            system_prompt: Optional system prompt
            conversation_history: Optional list of previous messages

        Yields:
            Response text chunks as they arrive
        """
        if not self.chat_available:
            raise RuntimeError(
                "OpenAI Chat API not available. Install openai: pip install openai"
            )

        client = self._get_async_client()
        model = self._get_model_name()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=config.openai.temperature,
            max_tokens=config.openai.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class RealtimeSession:
    """
    Async context manager for OpenAI Realtime API sessions.

    Manages WebSocket connection lifecycle and message exchange.
    """

    def __init__(self, client: OpenAIRealtimeClient):
        self.client = client
        self.ws: Optional[WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.conversation_id: Optional[str] = None
        self._response_buffer: Dict[str, str] = {}

    async def __aenter__(self) -> "RealtimeSession":
        """Connect to the Realtime API."""
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from the Realtime API."""
        await self._disconnect()

    async def _connect(self):
        """Establish WebSocket connection."""
        # Use pre-built URL from config (already includes model/deployment and api-version)
        url = self.client.endpoint

        # Build headers based on provider (Azure vs OpenAI)
        if self.client.is_azure:
            headers = {
                "api-key": self.client.api_key,
            }
        else:
            headers = {
                "Authorization": f"Bearer {self.client.api_key}",
                "OpenAI-Beta": "realtime=v1",
            }

        logger.info(f"Connecting to Realtime API: {url}")
        logger.info(f"Using Azure: {self.client.is_azure}")

        self.ws = await websockets.connect(url, extra_headers=headers)

        # Wait for session.created event
        response = await self.ws.recv()
        event = json.loads(response)

        if event.get("type") == "session.created":
            self.session_id = event.get("session", {}).get("id")
            logger.info(f"Session created: {self.session_id}")
        else:
            logger.warning(f"Unexpected initial event: {event.get('type')}")

        # Configure session for text modality
        await self._configure_session()

    async def _configure_session(self):
        """Configure the Realtime session for text interactions."""
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text"],
                "instructions": (
                    "You are an expert Magic: The Gathering advisor. "
                    "Provide helpful, accurate advice about deck building, "
                    "card choices, metagame analysis, and strategy. "
                    "Be concise but thorough."
                ),
                "temperature": config.openai.temperature,
                "max_response_output_tokens": config.openai.max_tokens,
            }
        }

        await self.ws.send(json.dumps(session_config))

        # Wait for session.updated confirmation
        response = await self.ws.recv()
        event = json.loads(response)
        if event.get("type") == "session.updated":
            logger.info("Session configured successfully")
        else:
            logger.warning(f"Session config response: {event.get('type')}")

    async def _disconnect(self):
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("Disconnected from Realtime API")

    async def send_message(
        self,
        message: str,
        context: Optional[str] = None,
    ) -> RealtimeResponse:
        """
        Send a message and receive a complete response.

        Args:
            message: User message to send
            context: Optional additional context to include

        Returns:
            RealtimeResponse with the assistant's reply
        """
        if not self.ws:
            raise RuntimeError("Not connected. Use 'async with client.connect()' context.")

        # Build the full message with context if provided
        full_message = message
        if context:
            full_message = f"{context}\n\nUser Question: {message}"

        # Create conversation item
        item_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": full_message,
                    }
                ]
            }
        }

        await self.ws.send(json.dumps(item_event))

        # Request response
        response_event = {
            "type": "response.create",
            "response": {
                "modalities": ["text"],
            }
        }

        await self.ws.send(json.dumps(response_event))

        # Collect response
        response_text = ""
        response_id = None
        usage = None

        while True:
            try:
                raw_response = await asyncio.wait_for(self.ws.recv(), timeout=30.0)
                event = json.loads(raw_response)
                event_type = event.get("type", "")

                if event_type == "response.text.delta":
                    delta = event.get("delta", "")
                    response_text += delta

                elif event_type == "response.text.done":
                    # Full text received
                    response_text = event.get("text", response_text)

                elif event_type == "response.done":
                    # Response complete
                    response_data = event.get("response", {})
                    response_id = response_data.get("id")
                    usage = response_data.get("usage")
                    break

                elif event_type == "error":
                    error_msg = event.get("error", {}).get("message", "Unknown error")
                    logger.error(f"Realtime API error: {error_msg}")
                    raise RuntimeError(f"Realtime API error: {error_msg}")

            except asyncio.TimeoutError:
                logger.warning("Response timeout")
                break

        return RealtimeResponse(
            text=response_text,
            conversation_id=self.conversation_id,
            response_id=response_id,
            usage=usage,
            is_complete=True,
        )

    async def send_message_stream(
        self,
        message: str,
        context: Optional[str] = None,
        on_delta: Optional[Callable[[str], None]] = None,
    ) -> RealtimeResponse:
        """
        Send a message and stream the response with callbacks.

        Args:
            message: User message to send
            context: Optional additional context
            on_delta: Callback function called with each text chunk

        Returns:
            RealtimeResponse with the complete response
        """
        if not self.ws:
            raise RuntimeError("Not connected. Use 'async with client.connect()' context.")

        full_message = message
        if context:
            full_message = f"{context}\n\nUser Question: {message}"

        # Create conversation item
        item_event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": full_message}]
            }
        }

        await self.ws.send(json.dumps(item_event))

        # Request response
        await self.ws.send(json.dumps({
            "type": "response.create",
            "response": {"modalities": ["text"]}
        }))

        response_text = ""
        response_id = None
        usage = None

        while True:
            try:
                raw_response = await asyncio.wait_for(self.ws.recv(), timeout=30.0)
                event = json.loads(raw_response)
                event_type = event.get("type", "")

                if event_type == "response.text.delta":
                    delta = event.get("delta", "")
                    response_text += delta
                    if on_delta:
                        on_delta(delta)

                elif event_type == "response.done":
                    response_data = event.get("response", {})
                    response_id = response_data.get("id")
                    usage = response_data.get("usage")
                    break

                elif event_type == "error":
                    error_msg = event.get("error", {}).get("message", "Unknown error")
                    raise RuntimeError(f"Realtime API error: {error_msg}")

            except asyncio.TimeoutError:
                break

        return RealtimeResponse(
            text=response_text,
            response_id=response_id,
            usage=usage,
            is_complete=True,
        )


# Singleton instance
_client: Optional[OpenAIRealtimeClient] = None


def get_openai_client() -> OpenAIRealtimeClient:
    """
    Get the singleton OpenAI client instance.

    Returns:
        OpenAIRealtimeClient instance
    """
    global _client
    if _client is None:
        _client = OpenAIRealtimeClient()
    return _client


def synthesize_with_llm(
    user_query: str,
    oracle_results: List[Dict[str, Any]],
    synergy_results: Optional[Dict[str, Any]],
    metagame_results: Optional[Dict[str, Any]],
    query_type: str,
) -> str:
    """
    Use LLM to synthesize a natural language response from agent results.

    This is the main integration point for using GPT to generate responses.

    Args:
        user_query: Original user question
        oracle_results: Card search results from ChromaDB
        synergy_results: Card synergy analysis results
        metagame_results: Metagame data from EDHREC/17Lands/MTGGoldfish
        query_type: Query classification (constructed/limited)

    Returns:
        Natural language response synthesized by LLM
    """
    client = get_openai_client()

    if not client.is_available:
        logger.warning("OpenAI not configured, falling back to template response")
        return None  # Signal to use template-based response

    # Build context for LLM
    context_parts = [
        "You are analyzing Magic: The Gathering data to answer a user's question.",
        f"Query Type: {query_type}",
        "",
        "=== Card Search Results ===",
    ]

    if oracle_results:
        for card in oracle_results[:5]:
            context_parts.append(f"- {card.get('name', 'Unknown')}: {card.get('type_line', '')}")
            if card.get('text'):
                context_parts.append(f"  Text: {card['text'][:200]}...")
    else:
        context_parts.append("No cards found in search.")

    context_parts.append("")
    context_parts.append("=== Synergy Analysis ===")

    if synergy_results:
        for card_name, synergies in synergy_results.items():
            context_parts.append(f"Synergies for {card_name}:")
            for syn in synergies[:3]:
                context_parts.append(f"  - {syn.get('card', 'Unknown')} (score: {syn.get('score', 0):.2f})")
    else:
        context_parts.append("No synergy data available.")

    context_parts.append("")
    context_parts.append("=== Metagame Data ===")

    if metagame_results and "error" not in metagame_results:
        if "commander_recommendations" in metagame_results:
            cmd = metagame_results["commander_recommendations"]
            context_parts.append(f"Commander: {cmd.get('commander', 'Unknown')}")
            if cmd.get('themes'):
                context_parts.append(f"Themes: {', '.join(cmd['themes'][:5])}")
            if cmd.get('cards'):
                context_parts.append("Top recommended cards:")
                for card in cmd['cards'][:10]:
                    context_parts.append(f"  - {card.get('name', 'Unknown')}")

        elif "top_decks" in metagame_results:
            context_parts.append("Top metagame decks:")
            for deck in metagame_results["top_decks"][:5]:
                context_parts.append(f"  - {deck.get('name', 'Unknown')}: {deck.get('meta_share', 'N/A')}")

        elif "color_pairs" in metagame_results:
            context_parts.append("Color pair performance:")
            pairs = sorted(
                metagame_results["color_pairs"],
                key=lambda x: x.get("win_rate", 0),
                reverse=True
            )
            for pair in pairs[:5]:
                context_parts.append(f"  - {pair['colors']}: {pair.get('win_rate', 0):.1%} win rate")
    else:
        context_parts.append("No metagame data available.")

    context = "\n".join(context_parts)

    # Generate response using Chat API (sync for now)
    system_prompt = (
        "You are an expert Magic: The Gathering advisor. "
        "Based on the provided data, give a helpful, accurate, and concise response "
        "to the user's question. Reference specific cards and statistics when available. "
        "Format your response clearly with sections if needed."
    )

    try:
        response = client.chat(
            message=user_query,
            system_prompt=system_prompt,
            conversation_history=[{"role": "user", "content": f"Context:\n{context}"}],
        )
        return response
    except Exception as e:
        logger.error(f"LLM synthesis failed: {e}")
        return None  # Fall back to template
