"""Bounded, explainable reference-matching recommendations for OpenMaster."""

from .service import (
    REFERENCE_RECOMMENDATION_SCHEMA_VERSION,
    ReferenceComparison,
    ReferenceMatchFinding,
    ReferenceMatchingService,
    ReferenceMatchPolicy,
    ReferenceMatchRecommendation,
)

__all__ = [
    "REFERENCE_RECOMMENDATION_SCHEMA_VERSION",
    "ReferenceComparison",
    "ReferenceMatchFinding",
    "ReferenceMatchPolicy",
    "ReferenceMatchRecommendation",
    "ReferenceMatchingService",
]
