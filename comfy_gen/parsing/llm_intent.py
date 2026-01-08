"""LLM-powered intent parsing for sophisticated natural language understanding.

Optional enhancement that uses local LLM (Ollama on ant-man) for more
nuanced intent extraction. Falls back gracefully to keyword parser if unavailable.

Features:
- Full request/response logging for experiment tracking
- Progress callbacks for visibility
- Inventory-aware system prompts
- Streaming support for thinking visibility (reasoning models)

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
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

import httpx

if TYPE_CHECKING:
    from comfy_gen.categories.registry import CategoryRegistry

logger = logging.getLogger(__name__)


# Environment configuration
# Default to ant-man Jetson Orin Nano running Ollama with deepseek-r1:7b
# Previously used moira's model-manager (192.168.1.215:8006) but GPU is busy with ComfyUI
LLM_ENDPOINT = os.getenv("COMFYGEN_LLM_ENDPOINT", "http://192.168.1.253:11434/v1/chat/completions")
LLM_MODEL = os.getenv("COMFYGEN_LLM_MODEL", "deepseek-r1:7b")
LLM_TIMEOUT = int(os.getenv("COMFYGEN_LLM_TIMEOUT", "120"))  # Reasoning models need more time


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
        metadata: Optional LLM call metadata for logging/experiments
    """

    categories: list[str] = field(default_factory=list)
    subject: Optional[str] = None
    style: Optional[str] = None
    modifiers: dict[str, str] = field(default_factory=dict)
    content_tier: ContentTier = ContentTier.GENERAL
    source: str = "unknown"
    confidence: float = 1.0
    metadata: Optional[LLMCallMetadata] = None


@dataclass
class LLMCallMetadata:
    """Full metadata from an LLM call for experiment tracking.

    Captures everything needed to reproduce and analyze LLM behavior.
    """

    timestamp: str = ""
    model: str = ""
    endpoint: str = ""

    # Request
    system_prompt: str = ""
    user_prompt: str = ""
    temperature: float = 0.1
    max_tokens: int = 2000  # Reasoning models need more tokens for <think> blocks
    top_p: float = 1.0

    # Response
    raw_response: str = ""
    thinking: Optional[str] = None  # Extracted <think> content from reasoning models
    parsed_json: Optional[dict] = None

    # Timing
    request_start: float = 0.0
    request_end: float = 0.0
    duration_seconds: float = 0.0

    # Status
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "timestamp": self.timestamp,
            "model": self.model,
            "endpoint": self.endpoint,
            "request": {
                "system_prompt": self.system_prompt,
                "user_prompt": self.user_prompt,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "top_p": self.top_p,
            },
            "response": {
                "raw": self.raw_response,
                "thinking": self.thinking,
                "parsed": self.parsed_json,
            },
            "timing": {
                "duration_seconds": self.duration_seconds,
            },
            "status": {
                "success": self.success,
                "error": self.error,
            },
        }


# Progress callback type
ProgressCallback = Callable[[str, Optional[dict]], None]


SYSTEM_PROMPT = """You are an image generation intent parser for ComfyUI workflows.

## Your Task
Parse user prompts to extract structured information for image generation.

## Available Categories
These are the ONLY valid category IDs you can return:
{categories}

## Category Descriptions
{category_descriptions}

## Available LoRAs (for reference)
{loras}

## Available Workflows
{workflows}

## Output Format
Respond with valid JSON only. No explanation, no markdown code blocks.

Required fields:
- categories: List of category IDs from available categories that match the request
- subject: Main subject of the image (person, object, scene)
- style: Art style or aesthetic (photorealistic, anime, oil painting, etc.)
- modifiers: Key-value pairs for additional parameters (lighting, mood, camera, etc.)
- content_tier: One of "general", "mature", or "explicit"

Example output:
{{"categories": ["portrait", "outdoor"], "subject": "woman in garden", "style": "photorealistic", "modifiers": {{"lighting": "golden hour", "mood": "serene"}}, "content_tier": "general"}}

## Important
- Only use category IDs from the available list
- Be precise with content_tier classification
- Extract as much semantic information as possible"""


# Simpler prompt for models that struggle with large context
SYSTEM_PROMPT_SIMPLE = """Parse user prompts for image generation. Output JSON only.

Available categories: {categories}

Output format:
{{"categories": ["cat1"], "subject": "main subject", "style": "art style", "modifiers": {{}}, "content_tier": "general|mature|explicit"}}

Only use categories from the list. No explanation."""


class LLMIntentParser:
    """Parse user intent using local LLM with structured output.

    Uses Ollama on ant-man (Jetson) for sophisticated NLU.
    Falls back gracefully if LLM is unavailable.

    Features:
    - Progress callbacks for visibility during long requests
    - Full metadata capture for experiment tracking
    - Thinking extraction for reasoning models (deepseek-r1)
    - Configurable temperature/top_p for precision tuning
    """

    def __init__(
        self,
        endpoint: str = LLM_ENDPOINT,
        model: str = LLM_MODEL,
        timeout: int = LLM_TIMEOUT,
        temperature: float = 0.1,
        top_p: float = 0.9,
        progress_callback: Optional[ProgressCallback] = None,
        use_simple_prompt: bool = False,
    ) -> None:
        """Initialize the LLM intent parser.

        Args:
            endpoint: LLM API endpoint URL
            model: Model name to use
            timeout: Request timeout in seconds
            temperature: Sampling temperature (lower = more deterministic)
            top_p: Nucleus sampling parameter
            progress_callback: Optional callback for progress updates
            use_simple_prompt: Use simpler system prompt for smaller models
        """
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.top_p = top_p
        self.progress_callback = progress_callback
        self.use_simple_prompt = use_simple_prompt
        self._available_categories: list[str] = []
        self._category_descriptions: dict[str, str] = {}
        self._available_loras: list[str] = []
        self._available_workflows: list[str] = []
        self._cache: dict[str, ParsedIntent] = {}
        self._last_metadata: Optional[LLMCallMetadata] = None

    def _progress(self, message: str, data: Optional[dict] = None) -> None:
        """Send progress update via callback."""
        logger.info(f"[LLM] {message}")
        if self.progress_callback:
            self.progress_callback(message, data)

    def set_available_categories(self, categories: list[str]) -> None:
        """Update the list of available categories for the prompt.

        Args:
            categories: List of valid category IDs
        """
        self._available_categories = categories

    def set_category_descriptions(self, descriptions: dict[str, str]) -> None:
        """Set category descriptions for richer context.

        Args:
            descriptions: Dict mapping category ID to description
        """
        self._category_descriptions = descriptions

    def set_available_loras(self, loras: list[str]) -> None:
        """Set available LoRAs for context.

        Args:
            loras: List of LoRA names
        """
        self._available_loras = loras

    def set_available_workflows(self, workflows: list[str]) -> None:
        """Set available workflows for context.

        Args:
            workflows: List of workflow names
        """
        self._available_workflows = workflows

    def get_last_metadata(self) -> Optional[LLMCallMetadata]:
        """Get metadata from the last LLM call.

        Returns:
            LLMCallMetadata or None if no calls made
        """
        return self._last_metadata

    def _get_cache_key(self, prompt: str) -> str:
        """Generate cache key from prompt.

        Args:
            prompt: User prompt

        Returns:
            Short hash key for caching
        """
        normalized = prompt.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _build_system_prompt(self) -> str:
        """Build the system prompt with inventory context."""
        if self.use_simple_prompt:
            return SYSTEM_PROMPT_SIMPLE.format(categories=", ".join(self._available_categories))

        # Build category descriptions
        cat_desc_lines = []
        for cat_id in self._available_categories:
            desc = self._category_descriptions.get(cat_id, "No description")
            cat_desc_lines.append(f"- {cat_id}: {desc}")

        return SYSTEM_PROMPT.format(
            categories=", ".join(self._available_categories),
            category_descriptions="\n".join(cat_desc_lines) if cat_desc_lines else "No descriptions available",
            loras=", ".join(self._available_loras[:20]) if self._available_loras else "No LoRAs loaded",
            workflows=", ".join(self._available_workflows) if self._available_workflows else "flux-dev.json (default)",
        )

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
            self._progress("Cache hit", {"prompt": prompt[:50]})
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
        # Build system prompt with full inventory context
        system = self._build_system_prompt()

        # Initialize metadata
        metadata = LLMCallMetadata(
            timestamp=datetime.now().isoformat(),
            model=self.model,
            endpoint=self.endpoint,
            system_prompt=system,
            user_prompt=prompt,
            temperature=self.temperature,
            max_tokens=2000,  # Reasoning models need more for <think> blocks
            top_p=self.top_p,
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": 2000,  # Reasoning models need more for <think> blocks
            "top_p": self.top_p,
        }

        self._progress(
            "Sending request to LLM",
            {
                "model": self.model,
                "endpoint": self.endpoint,
                "prompt_length": len(prompt),
            },
        )

        metadata.request_start = time.time()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                self._progress(f"Waiting for response (timeout: {self.timeout}s)...")
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()

                metadata.request_end = time.time()
                metadata.duration_seconds = metadata.request_end - metadata.request_start

                data = response.json()
                content = data["choices"][0]["message"]["content"]

                metadata.raw_response = content
                metadata.success = True

                self._progress(
                    f"Response received in {metadata.duration_seconds:.1f}s",
                    {
                        "duration": metadata.duration_seconds,
                        "response_length": len(content),
                    },
                )

                # Extract thinking from reasoning models (deepseek-r1 uses <think> tags)
                thinking, clean_content = self._extract_thinking(content)
                if thinking:
                    metadata.thinking = thinking
                    self._progress("Reasoning extracted", {"thinking_length": len(thinking)})
                    logger.debug(f"Model thinking: {thinking[:500]}...")

                self._last_metadata = metadata
                return self._parse_response(clean_content, metadata)

        except httpx.TimeoutException:
            metadata.request_end = time.time()
            metadata.duration_seconds = metadata.request_end - metadata.request_start
            metadata.success = False
            metadata.error = f"Timeout after {self.timeout}s"
            self._last_metadata = metadata
            self._progress(f"Timeout after {metadata.duration_seconds:.1f}s", {"error": "timeout"})
            logger.warning(f"LLM request timed out after {self.timeout}s")
            return None

        except httpx.HTTPStatusError as e:
            metadata.success = False
            metadata.error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            self._last_metadata = metadata
            self._progress(f"HTTP error: {e.response.status_code}", {"error": str(e)})
            logger.warning(f"LLM HTTP error: {e}")
            return None

        except Exception as e:
            metadata.success = False
            metadata.error = str(e)
            self._last_metadata = metadata
            self._progress(f"Error: {e}", {"error": str(e)})
            raise

    def _extract_thinking(self, content: str) -> tuple[Optional[str], str]:
        """Extract thinking from reasoning model output.

        deepseek-r1 and similar models wrap reasoning in <think>...</think> tags.

        Args:
            content: Raw LLM response

        Returns:
            Tuple of (thinking content or None, content without thinking tags)
        """
        import re

        # Match <think>...</think> blocks
        think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)

        if think_match:
            thinking = think_match.group(1).strip()
            # Remove the thinking block from content
            clean_content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            return thinking, clean_content

        return None, content

    def _parse_response(self, content: str, metadata: LLMCallMetadata) -> Optional[ParsedIntent]:
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

            # Store parsed result in metadata
            metadata.parsed_json = parsed

            self._progress(
                "Parsed successfully",
                {
                    "categories": valid_categories,
                    "subject": parsed.get("subject"),
                    "content_tier": tier_str,
                },
            )

            return ParsedIntent(
                categories=valid_categories,
                subject=parsed.get("subject"),
                style=parsed.get("style"),
                modifiers=parsed.get("modifiers", {}),
                content_tier=content_tier,
                source="llm",
                confidence=0.9 if valid_categories else 0.5,
                metadata=metadata,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            metadata.error = f"Parse error: {e}"
            self._progress(f"Parse failed: {e}", {"raw": content[:200]})
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

    Features:
    - Passes full inventory context to LLM (categories, LoRAs, workflows)
    - Progress callbacks for visibility
    - Full metadata capture for experiment tracking
    """

    def __init__(
        self,
        registry: Optional[CategoryRegistry] = None,
        llm_endpoint: str = LLM_ENDPOINT,
        llm_model: str = LLM_MODEL,
        llm_timeout: int = LLM_TIMEOUT,
        min_confidence: float = 0.3,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        """Initialize the hybrid parser.

        Args:
            registry: Category registry for lookups
            llm_endpoint: LLM API endpoint
            llm_model: Model name to use
            llm_timeout: Request timeout
            min_confidence: Minimum confidence for keyword matches
            progress_callback: Optional callback for progress updates
        """
        self._registry = registry
        self._registry_loaded = registry is not None
        self._llm_parser: Optional[LLMIntentParser] = None
        self._keyword_parser = None  # Lazy loaded
        self._llm_endpoint = llm_endpoint
        self._llm_model = llm_model
        self._llm_timeout = llm_timeout
        self._min_confidence = min_confidence
        self._progress_callback = progress_callback
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
        """Get LLM parser instance, creating lazily with full inventory context."""
        if self._llm_parser is None:
            self._llm_parser = LLMIntentParser(
                endpoint=self._llm_endpoint,
                model=self._llm_model,
                timeout=self._llm_timeout,
                progress_callback=self._progress_callback,
            )
            # Set available categories with descriptions
            categories = self.registry.all()
            self._llm_parser.set_available_categories([c.id for c in categories])

            # Set category descriptions for richer context
            descriptions = {}
            for cat in categories:
                if hasattr(cat, "description") and cat.description:
                    descriptions[cat.id] = cat.description
                elif hasattr(cat, "keywords") and cat.keywords:
                    descriptions[cat.id] = f"Keywords: {', '.join(cat.keywords[:5])}"
            self._llm_parser.set_category_descriptions(descriptions)

            # Try to load LoRA catalog for context
            try:
                from pathlib import Path

                import yaml

                lora_path = Path(__file__).parent.parent.parent / "lora_catalog.yaml"
                if lora_path.exists():
                    with open(lora_path) as f:
                        lora_data = yaml.safe_load(f)
                    if lora_data and "loras" in lora_data:
                        lora_names = [l.get("name", l.get("filename", "")) for l in lora_data["loras"][:30]]
                        self._llm_parser.set_available_loras(lora_names)
            except Exception as e:
                logger.debug(f"Could not load LoRA catalog: {e}")

            # Set available workflows
            try:
                from pathlib import Path

                workflow_dir = Path(__file__).parent.parent.parent / "workflows"
                if workflow_dir.exists():
                    workflows = [f.stem for f in workflow_dir.glob("*.json")]
                    self._llm_parser.set_available_workflows(workflows)
            except Exception as e:
                logger.debug(f"Could not load workflows: {e}")

        return self._llm_parser

    def get_last_llm_metadata(self) -> Optional[LLMCallMetadata]:
        """Get metadata from the last LLM call.

        Returns:
            LLMCallMetadata or None
        """
        if self._llm_parser:
            return self._llm_parser.get_last_metadata()
        return None

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
            # Check tags endpoint (Ollama-specific)
            base_url = self._llm_endpoint.replace("/v1/chat/completions", "")
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{base_url}/api/tags")
                if response.status_code == 200:
                    return True
                # Fallback to OpenAI models endpoint
                response = await client.get(f"{base_url}/v1/models")
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
