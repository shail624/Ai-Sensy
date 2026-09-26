"""Provider-independent Customer identity resolution layer (M13-02)."""

from app.identity.domain import (
    APPROVED_IDENTITY_NAMESPACES,
    PHONE_IDENTITY_NAMESPACES,
    IdentityAssertion,
    IdentityConfidence,
    IdentityConflictStatus,
    IdentityKind,
    IdentityMergeRecommendationStatus,
    IdentityNormalizerRegistry,
    IdentityResolutionStatus,
    IdentitySource,
    NormalizedIdentity,
    default_identity_normalizers,
)

__all__ = [
    "APPROVED_IDENTITY_NAMESPACES",
    "PHONE_IDENTITY_NAMESPACES",
    "IdentityAssertion",
    "IdentityConfidence",
    "IdentityConflictStatus",
    "IdentityKind",
    "IdentityMergeRecommendationStatus",
    "IdentityNormalizerRegistry",
    "IdentityResolutionStatus",
    "IdentitySource",
    "NormalizedIdentity",
    "default_identity_normalizers",
]
