"""LLM-powered intent parsing for sophisticated natural language understanding.

Optional enhancement that uses local LLM (model-manager GPT-OSS) for more
nuanced intent extraction. Falls back gracefully to keyword parser if unavailable.

Example:
    >>> parser = LLMIntentParser()
    >>> parser.set_available_categories(["portrait", "landscape", "night"])
    >>> result = await parser.parse("photo of a woman at golden hour")
    >>> result.categories
    ['portrait']
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

import httpx

if TYPE_CHECKING:
    from comfy_gen.categories.registry import CategoryRegistry

logger = logging.getLogger(__name__)


# Environment configuration
# Default to ant-man Jetson Orin Nano running Ollama with deepseek-r1:7b
# Previously used moira's model-manager (192.168.1.215:8006) but GPU is busy with ComfyUI
LLM_ENDPOINT = os.getenv("COMFYGEN_LLM_ENDPOINT", "http://192.168.1.253:11434/v1/chat/completions")
LLM_MODEL = os.getenv("COMFYGEN_LLM_MODEL", "deepseek-r1:7b")
LLM_TIMEOUT = int(os.getenv("COMFYGEN_LLM_TIMEOUT", "60"))  # Reasoning models need more time


class ContentTier(Enum):
    """Content policy tier for generation."""

    GENERAL = "general"
    MATURE = "mature"
    EXPLICIT = "explicit"


@dataclass
class ParsedIntent:
    """Structured intent extracted from user prompt.

    Attributes:
        categories: List of matched category IDs
        subject: Main subject of the image
        style: Art style or aesthetic
        modifiers: Additional parameters or effects
        content_tier: Content policy tier
        source: Where this intent came from ("llm", "keyword", "hybrid")
        confidence: Overall confidence in the parse (0.0-1.0)
    """

    categories: list[str] = field(default_factory=list)
    subject: Optional[str] = None
    style: Optional[str] = None
    modifiers: dict[str, str] = field(default_factory=dict)
    content_tier: ContentTier = ContentTier.GENERAL
    source: str = "unknown"
    confidence: float = 1.0


SYSTEM_PROMPT = """You are an image generation intent parser. Given a user prompt, extract:
1. categories: List of category names that match the request (from available categories)
2. subject: Main subject of the image
3. style: Art style or aesthetic
4. modifiers: Additional parameters or effects as key-value pairs
5. content_tier: One of "general", "mature", or "explicit"

Available categories: {categories}

Respond with valid JSON only, no explanation.
Example response:
{{
  "categories": ["portrait", "outdoor"],
  "subject": "woman in garden",
  "style": "photorealistic",
  "modifiers": {{"lighting": "golden hour", "mood": "serene"}},
  "content_tier": "general"
}}"""


class LLMIntentParser:
    """Parse user intent using local LLM with structured output.

    Uses model-manager GPT-OSS endpoint for sophisticated NLU.
    Falls back gracefully if LLM is unavailable.
    """

    def __init__(
        self,
        endpoint: str = LLM_ENDPOINT,
        model: str = LLM_MODEL,
        timeout: int = LLM_TIMEOUT,
    ) -> None:
        """Initialize the LLM intent parser.

        Args:
            endpoint: LLM API endpoint URL
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout
        self._available_categories: list[str] = []
        self._cache: dict[str, ParsedIntent] = {}

    def set_available_categories(self, categories: list[str]) -> None:
        """Update the list of available categories for the prompt.

        Args:
            categories: List of valid category IDs
        """
        self._available_categories = categories

    def _get_cache_key(self, prompt: str) -> str:
        """Generate cache key from prompt.

        Args:
            prompt: User prompt

        Returns:
            Short hash key for caching
        """
        normalized = prompt.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    async def parse(self, prompt: str) -> Optional[ParsedIntent]:
        """Parse user prompt using LLM.

        Returns None if LLM unavailable (caller should fallback to keyword parser).

        Args:
            prompt: User input text

        Returns:
            ParsedIntent if successful, None if LLM unavailable
        """
        # Check cache
        cache_key = self._get_cache_key(prompt)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for prompt: {prompt[:50]}...")
            return self._cache[cache_key]

        try:
            result = await self._call_llm(prompt)
            if result:
                self._cache[cache_key] = result
            return result
        except Exception as e:
            # Log but don't fail - caller will fallback
            logger.warning(f"LLM parsing failed: {e}")
            return None

    async def _call_llm(self, prompt: str) -> Optional[ParsedIntent]:
        """Make LLM API call and parse response.

        Args:
            prompt: User input text

        Returns:
            ParsedIntent if successful, None on error
        """
        system = SYSTEM_PROMPT.format(categories=", ".join(self._available_categories))

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,  # Low temp for consistent parsing
            "max_tokens": 500,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            return self._parse_response(content)

    def _parse_response(self, content: str) -> Optional[ParsedIntent]:
        """Parse LLM JSON response into ParsedIntent.

        Args:
            content: Raw response content from LLM

        Returns:
            ParsedIntent if valid JSON, None on parse error
        """
        try:
            # Try to extract JSON from response (LLM might add extra text)
            json_match = content
            if "```json" in content:
                # Extract from markdown code block
                import re

                match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
                if match:
                    json_match = match.group(1)
            elif "{" in content:
                # Find JSON object
                start = content.find("{")
                end = content.rfind("}") + 1
                json_match = content[start:end]

            parsed = json.loads(json_match)

            # Validate categories against available list
            valid_categories = [c for c in parsed.get("categories", []) if c in self._available_categories]

            # Parse content tier
            tier_str = parsed.get("content_tier", "general").lower()
            try:
                content_tier = ContentTier(tier_str)
            except ValueError:
                content_tier = ContentTier.GENERAL

            return ParsedIntent(
                categories=valid_categories,
                subject=parsed.get("subject"),
                style=parsed.get("style"),
                modifiers=parsed.get("modifiers", {}),
                content_tier=content_tier,
                source="llm",
                confidence=0.9 if valid_categories else 0.5,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {content}")
            return None

    def clear_cache(self) -> None:
        """Clear the intent cache."""
        self._cache.clear()
        logger.debug("LLM intent cache cleared")


class HybridLLMParser:
    """Combines LLM and keyword-based parsing.

    Strategy:
    1. Try LLM first (if available)
    2. Fallback to keyword parser
    3. Merge results for best coverage
    """

    def __init__(
        self,
        registry: Optional[CategoryRegistry] = None,
        llm_endpoint: str = LLM_ENDPOINT,
        llm_model: str = LLM_MODEL,
        llm_timeout: int = LLM_TIMEOUT,
        min_confidence: float = 0.3,
    ) -> None:
        """Initialize the hybrid parser.

        Args:
            registry: Category registry for lookups
            llm_endpoint: LLM API endpoint
            llm_model: Model name to use
            llm_timeout: Request timeout
            min_confidence: Minimum confidence for keyword matches
        """
        self._registry = registry
        self._registry_loaded = registry is not None
        self._llm_parser: Optional[LLMIntentParser] = None
        self._keyword_parser = None  # Lazy loaded
        self._llm_endpoint = llm_endpoint
        self._llm_model = llm_model
        self._llm_timeout = llm_timeout
        self._min_confidence = min_confidence
        self._llm_available: Optional[bool] = None

    @property
    def registry(self) -> CategoryRegistry:
        """Get the category registry, loading it lazily."""
        if not self._registry_loaded:
            from comfy_gen.categories.registry import CategoryRegistry

            self._registry = CategoryRegistry.get_instance()
            self._registry_loaded = True
        return self._registry  # type: ignore[return-value]

    @property
    def llm_parser(self) -> LLMIntentParser:
        """Get LLM parser instance, creating lazily."""
        if self._llm_parser is None:
            self._llm_parser = LLMIntentParser(
                endpoint=self._llm_endpoint,
                model=self._llm_model,
                timeout=self._llm_timeout,
            )
            # Set available categories
            self._llm_parser.set_available_categories([c.id for c in self.registry.all()])
        return self._llm_parser

    @property
    def keyword_parser(self):
        """Get keyword parser instance."""
        if self._keyword_parser is None:
            from comfy_gen.parsing.intent_classifier import HybridParser

            self._keyword_parser = HybridParser(self.registry, self._min_confidence)
        return self._keyword_parser

    async def check_llm_health(self) -> bool:
        """Check if LLM endpoint is available.

        Returns:
            True if LLM is healthy, False otherwise
        """
        try:
            # Check models endpoint
            models_url = self._llm_endpoint.replace("/chat/completions", "/models")
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(models_url)
                return response.status_code == 200
        except Exception:
            return False

    async def parse(self, text: str) -> ParsedIntent:
        """Parse prompt using hybrid approach.

        Args:
            text: User input text

        Returns:
            ParsedIntent with merged results
        """
        # Always run keyword parser (fast, reliable baseline)
        keyword_result = self.keyword_parser.parse(text)

        # Check LLM availability (cache result)
        if self._llm_available is None:
            self._llm_available = await self.check_llm_health()

        if not self._llm_available:
            logger.debug("LLM unavailable, using keyword-only parsing")
            return self._keyword_to_intent(keyword_result)

        # Try LLM parser
        llm_result = await self.llm_parser.parse(text)

        if llm_result is None:
            # LLM call failed - use keyword only
            return self._keyword_to_intent(keyword_result)

        # Merge results
        return self._merge_results(keyword_result, llm_result)

    def _keyword_to_intent(self, keyword_result: dict) -> ParsedIntent:
        """Convert keyword parser result to ParsedIntent.

        Args:
            keyword_result: Result from HybridParser.parse()

        Returns:
            ParsedIntent from keyword results
        """
        all_categories = keyword_result["explicit_categories"].copy()

        # Add inferred categories
        for cat_id, _confidence in keyword_result["inferred_categories"]:
            if cat_id not in all_categories:
                all_categories.append(cat_id)

        return ParsedIntent(
            categories=all_categories,
            subject=keyword_result["remaining_prompt"] if keyword_result["remaining_prompt"] else None,
            style=None,
            modifiers={},
            content_tier=ContentTier.GENERAL,
            source="keyword",
            confidence=0.7 if all_categories else 0.3,
        )

    def _merge_results(self, keyword_result: dict, llm_result: ParsedIntent) -> ParsedIntent:
        """Merge keyword and LLM results.

        Args:
            keyword_result: Result from keyword parser
            llm_result: Result from LLM parser

        Returns:
            Merged ParsedIntent with best of both
        """
        # Explicit @tags from keyword parser take precedence
        explicit_categories = keyword_result["explicit_categories"]

        # Combine with LLM categories (no duplicates)
        all_categories = explicit_categories.copy()
        for cat_id in llm_result.categories:
            if cat_id not in all_categories:
                all_categories.append(cat_id)

        # Add keyword-inferred categories
        for cat_id, _confidence in keyword_result["inferred_categories"]:
            if cat_id not in all_categories:
                all_categories.append(cat_id)

        # Use LLM for semantic fields (richer understanding)
        return ParsedIntent(
            categories=all_categories,
            subject=llm_result.subject or keyword_result["remaining_prompt"],
            style=llm_result.style,
            modifiers=llm_result.modifiers,
            content_tier=llm_result.content_tier,
            source="hybrid",
            confidence=0.95 if all_categories else 0.5,
        )

    def reset_llm_status(self) -> None:
        """Reset LLM availability status (recheck on next parse)."""
        self._llm_available = None


def create_llm_intent_parser(
    registry: Optional[CategoryRegistry] = None,
) -> HybridLLMParser:
    """Factory function for creating a configured LLM intent parser.

    Args:
        registry: Category registry (uses global instance if None)

    Returns:
        Configured HybridLLMParser
    """
    return HybridLLMParser(registry=registry)
