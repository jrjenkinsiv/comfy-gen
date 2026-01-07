"""Tag parser for @tag syntax in user input.

Extracts explicit category references from user input using @tag notation.
Supports optional strength modifiers: @portrait:0.8

Example:
    >>> parser = TagParser()
    >>> result = parser.parse("@portrait @outdoor a woman in a garden")
    >>> result.matched_tags[0].category_id
    'portrait'
    >>> result.remaining_text
    'a woman in a garden'
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from comfy_gen.categories.registry import CategoryRegistry

logger = logging.getLogger(__name__)


@dataclass
class TagMatch:
    """A matched @tag reference.

    Attributes:
        tag: Original tag text (lowercase)
        category_id: Resolved category ID
        strength: Strength modifier (default 1.0)
        position: Start and end position in original text
    """

    tag: str
    category_id: str
    strength: float = 1.0
    position: tuple[int, int] = field(default_factory=lambda: (0, 0))


@dataclass
class ParseResult:
    """Result of parsing user input for @tags.

    Attributes:
        matched_tags: Tags that resolved to categories
        unmatched_tags: Tags that didn't match any category
        remaining_text: Input text with @tags removed
        original_text: Original input text
    """

    matched_tags: list[TagMatch]
    unmatched_tags: list[str]
    remaining_text: str
    original_text: str

    @property
    def has_matches(self) -> bool:
        """True if any tags matched categories."""
        return len(self.matched_tags) > 0

    @property
    def category_ids(self) -> list[str]:
        """Get list of matched category IDs."""
        return [m.category_id for m in self.matched_tags]

    def get_strength(self, category_id: str) -> float:
        """Get strength modifier for a category ID."""
        for match in self.matched_tags:
            if match.category_id == category_id:
                return match.strength
        return 1.0


class TagParser:
    """Parser for @tag syntax in user input.

    Extracts @tag references from text, resolves them to categories,
    and returns the remaining text for further processing.

    Example:
        >>> parser = TagParser()
        >>> result = parser.parse("@portrait professional headshot")
        >>> print(result.category_ids)
        ['portrait']
    """

    # Pattern: @tag or @tag:0.8
    # Tag must start with letter or underscore, then alphanumeric/underscore
    TAG_PATTERN = re.compile(
        r"@([a-zA-Z_][a-zA-Z0-9_-]*)(?::([\d.]+))?",
        re.IGNORECASE,
    )

    def __init__(self, registry: Optional[CategoryRegistry] = None) -> None:
        """Initialize the tag parser.

        Args:
            registry: Category registry for lookups. Uses global instance if None.
        """
        self._registry = registry
        self._registry_loaded = registry is not None

    @property
    def registry(self) -> CategoryRegistry:
        """Get the category registry, loading it lazily."""
        if not self._registry_loaded:
            from comfy_gen.categories.registry import CategoryRegistry

            self._registry = CategoryRegistry.get_instance()
            self._registry_loaded = True
        return self._registry  # type: ignore[return-value]

    def parse(self, text: str) -> ParseResult:
        """Parse @tags from input text.

        Extracts all @tag references, resolves them to categories,
        and returns the remaining text.

        Args:
            text: User input text possibly containing @tags

        Returns:
            ParseResult with matched categories, unmatched tags, and remaining text
        """
        matched: list[TagMatch] = []
        unmatched: list[str] = []

        for match in self.TAG_PATTERN.finditer(text):
            tag = match.group(1).lower()
            strength_str = match.group(2)
            strength = float(strength_str) if strength_str else 1.0
            position = (match.start(), match.end())

            # Clamp strength to valid range
            strength = max(0.0, min(2.0, strength))

            # Try direct lookup by ID
            category = self.registry.get(tag)

            if category:
                matched.append(
                    TagMatch(
                        tag=tag,
                        category_id=category.id,
                        strength=strength,
                        position=position,
                    )
                )
                logger.debug(f"Tag @{tag} matched category {category.id}")
            else:
                # Try alias/keyword lookup
                categories = self.registry.search_by_keyword(tag)
                if categories:
                    # Use first match (highest relevance)
                    matched.append(
                        TagMatch(
                            tag=tag,
                            category_id=categories[0].id,
                            strength=strength,
                            position=position,
                        )
                    )
                    logger.debug(f"Tag @{tag} matched via keyword: {categories[0].id}")
                else:
                    unmatched.append(tag)
                    logger.warning(f"Unknown tag @{tag} - no matching category found")

        # Remove tags from text to get remaining prompt
        remaining = self.TAG_PATTERN.sub("", text).strip()
        # Clean up extra whitespace
        remaining = re.sub(r"\s+", " ", remaining)

        return ParseResult(
            matched_tags=matched,
            unmatched_tags=unmatched,
            remaining_text=remaining,
            original_text=text,
        )

    def extract_category_ids(self, text: str) -> list[str]:
        """Convenience method to just get matched category IDs.

        Args:
            text: User input text

        Returns:
            List of category IDs from @tags
        """
        result = self.parse(text)
        return result.category_ids

    def extract_with_strengths(self, text: str) -> dict[str, float]:
        """Extract category IDs with their strength modifiers.

        Args:
            text: User input text

        Returns:
            Dict mapping category_id to strength
        """
        result = self.parse(text)
        return {m.category_id: m.strength for m in result.matched_tags}

    def validate_tags(self, text: str) -> tuple[bool, list[str]]:
        """Validate that all @tags in text resolve to categories.

        Args:
            text: User input text

        Returns:
            Tuple of (all_valid, list_of_invalid_tags)
        """
        result = self.parse(text)
        return (len(result.unmatched_tags) == 0, result.unmatched_tags)
