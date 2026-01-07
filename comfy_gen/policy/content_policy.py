"""Content policy enforcement layer.

Validates that requested categories are allowed at the client's policy tier.
Tier hierarchy: general < mature < explicit

Example:
    >>> from comfy_gen.policy import check_policy
    >>> result = check_policy(categories, "general")
    >>> if not result.allowed:
    ...     print(f"Blocked: {result.violations}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from comfy_gen.api.schemas.category import Category, PolicyTier

logger = logging.getLogger(__name__)


class PolicyLevel(IntEnum):
    """Policy tier levels for numerical comparison.

    Higher values can access lower tier content.
    """

    GENERAL = 0
    MATURE = 1
    EXPLICIT = 2

    @classmethod
    def from_tier(cls, tier: PolicyTier | str) -> PolicyLevel:
        """Convert PolicyTier enum or string to PolicyLevel.

        Args:
            tier: PolicyTier enum or string value

        Returns:
            Corresponding PolicyLevel
        """
        from comfy_gen.api.schemas.category import PolicyTier

        if isinstance(tier, str):
            tier = PolicyTier(tier)

        mapping = {
            PolicyTier.GENERAL: cls.GENERAL,
            PolicyTier.MATURE: cls.MATURE,
            PolicyTier.EXPLICIT: cls.EXPLICIT,
        }
        return mapping[tier]


@dataclass
class PolicyViolation:
    """A single policy violation.

    Attributes:
        category_id: ID of the violating category
        category_tier: The category's required tier
        required_tier: The request's tier level
        message: Human-readable violation message
    """

    category_id: str
    category_tier: str  # Using string to avoid import cycle
    required_tier: str
    message: str


@dataclass
class PolicyResult:
    """Result of a policy check.

    Attributes:
        allowed: True if all categories pass policy check
        violations: List of policy violations
        checked_categories: List of category IDs that were checked
        request_tier: The tier level of the request
    """

    allowed: bool
    violations: list[PolicyViolation] = field(default_factory=list)
    checked_categories: list[str] = field(default_factory=list)
    request_tier: str = "general"

    @property
    def violation_messages(self) -> list[str]:
        """Get all violation messages."""
        return [v.message for v in self.violations]


class PolicyEnforcer:
    """Enforces content policy tiers.

    Validates that all requested categories are allowed
    at the client's policy tier level.

    Example:
        >>> enforcer = PolicyEnforcer()
        >>> result = enforcer.check(categories, "general")
        >>> if not result.allowed:
        ...     raise PolicyError(result.violations)
    """

    def __init__(self, audit_log: bool = True) -> None:
        """Initialize the policy enforcer.

        Args:
            audit_log: Whether to log policy decisions
        """
        self.audit_log = audit_log

    def check(
        self,
        categories: list[Category],
        request_tier: PolicyTier | str,
    ) -> PolicyResult:
        """Check if all categories are allowed at the request tier.

        Args:
            categories: List of Category objects to check
            request_tier: The requested policy tier

        Returns:
            PolicyResult with allowed=False if any violations
        """
        from comfy_gen.api.schemas.category import PolicyTier

        if isinstance(request_tier, str):
            request_tier = PolicyTier(request_tier)

        request_level = PolicyLevel.from_tier(request_tier)
        violations: list[PolicyViolation] = []

        for category in categories:
            category_level = PolicyLevel.from_tier(category.policy_tier)

            if category_level > request_level:
                violations.append(
                    PolicyViolation(
                        category_id=category.id,
                        category_tier=category.policy_tier.value,
                        required_tier=request_tier.value,
                        message=self._build_message(category, request_tier),
                    )
                )

        result = PolicyResult(
            allowed=len(violations) == 0,
            violations=violations,
            checked_categories=[c.id for c in categories],
            request_tier=request_tier.value,
        )

        if self.audit_log:
            self._log_decision(result)

        return result

    def _build_message(
        self,
        category: Category,
        request_tier: PolicyTier,
    ) -> str:
        """Build human-readable violation message.

        Args:
            category: The violating category
            request_tier: The request's tier

        Returns:
            Human-readable message
        """
        return (
            f'Category "{category.id}" requires policy_tier="{category.policy_tier.value}" '
            f'but request specified "{request_tier.value}". '
            f"Upgrade policy_tier to access this category."
        )

    def _log_decision(self, result: PolicyResult) -> None:
        """Log policy decision for audit.

        Args:
            result: The policy check result
        """
        if result.allowed:
            logger.info(f"Policy ALLOWED: tier={result.request_tier}, categories={result.checked_categories}")
        else:
            logger.warning(
                f"Policy DENIED: tier={result.request_tier}, violations={[v.category_id for v in result.violations]}"
            )

    def filter_allowed(
        self,
        categories: list[Category],
        request_tier: PolicyTier | str,
    ) -> list[Category]:
        """Filter categories to only those allowed at request tier.

        Useful for UI to show only accessible categories.

        Args:
            categories: List of categories to filter
            request_tier: The request's tier level

        Returns:
            List of categories at or below request tier
        """
        from comfy_gen.api.schemas.category import PolicyTier

        if isinstance(request_tier, str):
            request_tier = PolicyTier(request_tier)

        request_level = PolicyLevel.from_tier(request_tier)

        return [c for c in categories if PolicyLevel.from_tier(c.policy_tier) <= request_level]


# Module-level singleton instance
_enforcer: Optional[PolicyEnforcer] = None


def _get_enforcer() -> PolicyEnforcer:
    """Get or create the global policy enforcer."""
    global _enforcer
    if _enforcer is None:
        _enforcer = PolicyEnforcer()
    return _enforcer


def check_policy(
    categories: list[Category],
    request_tier: PolicyTier | str,
) -> PolicyResult:
    """Convenience function to check policy.

    Args:
        categories: Categories to check
        request_tier: Request's policy tier

    Returns:
        PolicyResult
    """
    return _get_enforcer().check(categories, request_tier)


def filter_by_policy(
    categories: list[Category],
    request_tier: PolicyTier | str,
) -> list[Category]:
    """Convenience function to filter categories by policy tier.

    Args:
        categories: Categories to filter
        request_tier: Request's policy tier

    Returns:
        Filtered list of categories
    """
    return _get_enforcer().filter_allowed(categories, request_tier)
