"""Keyword-based intent classifier for natural language input.

Matches user input against category keywords to infer intent.
Uses weighted scoring: primary > specific > secondary keywords.

Example:
    >>> classifier = IntentClassifier()
    >>> matches = classifier.classify("beautiful woman portrait in garden outdoor")
    >>> matches[0].category.id
    'portrait'
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from comfy_gen.api.schemas.category import Category, CategoryType
    from comfy_gen.categories.registry import CategoryRegistry
    from comfy_gen.parsing.tag_parser import TagParser

logger = logging.getLogger(__name__)


@dataclass
class CategoryMatch:
    """A category match with confidence score.

    Attributes:
        category: The matched category
        confidence: Confidence score (0.0 - 1.0)
        matched_keywords: Keywords that triggered this match
        keyword_type: Highest-priority keyword type matched
    """

    category: Category
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    keyword_type: str = "secondary"  # "primary", "secondary", or "specific"


class IntentClassifier:
    """Keyword-based intent classifier.

    Matches user input against category keywords to infer intent.
    Primary keywords have highest weight, then specific, then secondary.
    """

    # Keyword weights
    WEIGHTS = {
        "primary": 1.0,
        "secondary": 0.6,
        "specific": 0.8,
    }

    def __init__(
        self,
        registry: Optional[CategoryRegistry] = None,
        min_confidence: float = 0.3,
    ) -> None:
        """Initialize the intent classifier.

        Args:
            registry: Category registry for lookups. Uses global instance if None.
            min_confidence: Minimum confidence threshold for matches (0.0 - 1.0)
        """
        self._registry = registry
        self._registry_loaded = registry is not None
        self.min_confidence = min_confidence
        self._keyword_index: Optional[dict[str, list[tuple[str, str, float]]]] = None

    @property
    def registry(self) -> CategoryRegistry:
        """Get the category registry, loading it lazily."""
        if not self._registry_loaded:
            from comfy_gen.categories.registry import CategoryRegistry

            self._registry = CategoryRegistry.get_instance()
            self._registry_loaded = True
        return self._registry  # type: ignore[return-value]

    @property
    def keyword_index(self) -> dict[str, list[tuple[str, str, float]]]:
        """Get keyword index, building it lazily."""
        if self._keyword_index is None:
            self._keyword_index = self._build_index()
        return self._keyword_index

    def _build_index(self) -> dict[str, list[tuple[str, str, float]]]:
        """Build inverted index: keyword -> [(category_id, keyword_type, weight), ...].

        Returns:
            Dict mapping lowercase keywords to list of (category_id, type, weight) tuples
        """
        index: dict[str, list[tuple[str, str, float]]] = defaultdict(list)

        for category in self.registry.all():
            # Index primary keywords
            for kw in category.keywords.primary:
                index[kw.lower()].append((category.id, "primary", self.WEIGHTS["primary"]))

            # Index secondary keywords
            for kw in category.keywords.secondary:
                index[kw.lower()].append((category.id, "secondary", self.WEIGHTS["secondary"]))

            # Index specific keywords
            for kw in category.keywords.specific:
                index[kw.lower()].append((category.id, "specific", self.WEIGHTS["specific"]))

        logger.debug(f"Built keyword index with {len(index)} unique keywords")
        return dict(index)

    def classify(self, text: str) -> list[CategoryMatch]:
        """Classify text and return matching categories ranked by confidence.

        Args:
            text: User input text to classify

        Returns:
            List of CategoryMatch objects above min_confidence threshold,
            sorted by confidence descending
        """
        # Tokenize and normalize
        tokens = self._tokenize(text)

        # Score each category
        scores: dict[str, dict] = defaultdict(lambda: {"score": 0.0, "matched": [], "keyword_type": None})

        for token in tokens:
            if token in self.keyword_index:
                for category_id, kw_type, weight in self.keyword_index[token]:
                    scores[category_id]["score"] += weight
                    scores[category_id]["matched"].append(token)

                    # Track highest-priority keyword type
                    current_type = scores[category_id]["keyword_type"]
                    if current_type is None:
                        scores[category_id]["keyword_type"] = kw_type
                    elif self.WEIGHTS[kw_type] > self.WEIGHTS.get(current_type, 0):
                        scores[category_id]["keyword_type"] = kw_type

        if not scores:
            return []

        # Normalize scores to 0-1 confidence
        max_score = max(s["score"] for s in scores.values())
        if max_score <= 0:
            return []

        # Build results
        results: list[CategoryMatch] = []
        for category_id, data in scores.items():
            confidence = data["score"] / max_score

            if confidence >= self.min_confidence:
                category = self.registry.get(category_id)
                if category:
                    results.append(
                        CategoryMatch(
                            category=category,
                            confidence=confidence,
                            matched_keywords=list(set(data["matched"])),
                            keyword_type=data["keyword_type"] or "secondary",
                        )
                    )

        # Sort by confidence descending
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize and normalize text.

        Args:
            text: Input text

        Returns:
            List of lowercase word tokens
        """
        # Lowercase and split on non-alphanumeric (keeping hyphens for compound words)
        # First normalize hyphens
        text = text.replace("-", " ")
        tokens = re.findall(r"[a-zA-Z]+", text.lower())
        return tokens

    def get_top_categories(
        self,
        text: str,
        max_results: int = 3,
        required_types: Optional[list[CategoryType]] = None,
    ) -> list[Category]:
        """Get top N matching categories.

        Args:
            text: Input text to classify
            max_results: Maximum number of categories to return
            required_types: Optional filter by category types

        Returns:
            List of top matching Category objects
        """
        matches = self.classify(text)

        if required_types:
            matches = [m for m in matches if m.category.type in required_types]

        return [m.category for m in matches[:max_results]]

    def refresh_index(self) -> None:
        """Refresh the keyword index (call if categories change)."""
        self._keyword_index = self._build_index()


class HybridParser:
    """Combines @tag parsing with keyword intent classification.

    First extracts explicit @tags, then uses keyword matching to
    infer additional categories from the remaining text.
    """

    def __init__(
        self,
        registry: Optional[CategoryRegistry] = None,
        min_confidence: float = 0.3,
    ) -> None:
        """Initialize the hybrid parser.

        Args:
            registry: Category registry for lookups
            min_confidence: Minimum confidence for keyword matches
        """

        self._registry = registry
        self._registry_loaded = registry is not None
        self.min_confidence = min_confidence
        self._tag_parser: Optional[TagParser] = None
        self._classifier: Optional[IntentClassifier] = None

    @property
    def registry(self) -> CategoryRegistry:
        """Get the category registry, loading it lazily."""
        if not self._registry_loaded:
            from comfy_gen.categories.registry import CategoryRegistry

            self._registry = CategoryRegistry.get_instance()
            self._registry_loaded = True
        return self._registry  # type: ignore[return-value]

    @property
    def tag_parser(self) -> TagParser:
        """Get tag parser instance."""
        if self._tag_parser is None:
            from comfy_gen.parsing.tag_parser import TagParser

            self._tag_parser = TagParser(self.registry)
        return self._tag_parser

    @property
    def classifier(self) -> IntentClassifier:
        """Get classifier instance."""
        if self._classifier is None:
            self._classifier = IntentClassifier(self.registry, self.min_confidence)
        return self._classifier

    def parse(self, text: str) -> dict:
        """Parse input using both @tags and keyword matching.

        @tags take precedence, then keyword matches fill gaps.

        Args:
            text: User input text with optional @tags

        Returns:
            Dict with:
                - explicit_categories: List of category IDs from @tags
                - explicit_strengths: Dict of category_id -> strength from @tags
                - inferred_categories: List of (category_id, confidence) from keywords
                - unmatched_tags: List of @tags that didn't match
                - remaining_prompt: Text after @tag extraction
        """
        # First pass: extract explicit @tags
        tag_result = self.tag_parser.parse(text)
        explicit_ids = {m.category_id for m in tag_result.matched_tags}

        # Second pass: classify remaining text
        keyword_matches = self.classifier.classify(tag_result.remaining_text)

        # Filter out already-matched categories
        inferred = [m for m in keyword_matches if m.category.id not in explicit_ids]

        return {
            "explicit_categories": [m.category_id for m in tag_result.matched_tags],
            "explicit_strengths": {m.category_id: m.strength for m in tag_result.matched_tags},
            "inferred_categories": [(m.category.id, m.confidence) for m in inferred],
            "unmatched_tags": tag_result.unmatched_tags,
            "remaining_prompt": tag_result.remaining_text,
        }

    def get_all_categories(
        self,
        text: str,
        max_inferred: int = 2,
    ) -> list[str]:
        """Get all category IDs (explicit + top inferred).

        Args:
            text: User input text
            max_inferred: Maximum inferred categories to include

        Returns:
            List of category IDs
        """
        result = self.parse(text)
        categories = result["explicit_categories"].copy()

        # Add inferred up to max
        for cat_id, _confidence in result["inferred_categories"][:max_inferred]:
            if cat_id not in categories:
                categories.append(cat_id)

        return categories
