"""
Simple keyword-based work type classifier.

This service suggests work types based on activity descriptions and historical patterns.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..core.enums import WorkType
from ..core.models import PerformanceSession


class ConfidenceLevel(str, Enum):
    """Confidence level for classification suggestions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class WorkTypeSuggestion:
    """A suggested work type with confidence score."""
    work_type: WorkType
    confidence: ConfidenceLevel
    reasons: List[str]
    score: float  # 0-1 scale


class WorkTypeClassifier:
    """
    Classifies work types based on activity descriptions and historical patterns.
    """

    # Keyword patterns for different work types
    DEEP_KEYWORDS = [
        "code", "programming", "develop", "algorithm", "architecture", "design",
        "write", "draft", "create", "build", "implement", "solve", "debug",
        "analyze", "research", "plan", "strategy", "prototype", "experiment",
        "think", "concentrate", "focus", "problem", "solution", "innovate",
        "invent", "compose", "author", "engineer", "calculate", "model"
    ]

    SHALLOW_KEYWORDS = [
        "email", "meeting", "call", "chat", "review", "read", "browse",
        "organize", "clean", "update", "respond", "reply", "check",
        "schedule", "coordinate", "admin", "paperwork", "invoice", "report",
        "communicate", "discuss", "coordinate", "planning", "organizing",
        "scan", "skim", "quick", "routine", "daily", "check-in", "follow-up",
        "checking", "scheduling", "planning", "coordinating", "emailing",
        "meetings", "calls", "chats", "reviews", "reading", "browsing"
    ]

    MAINTENANCE_KEYWORDS = [
        "fix", "patch", "update", "upgrade", "maintain", "cleanup",
        "refactor", "optimize", "tune", "configure", "setup", "install",
        "backup", "restore", "monitor", "test", "verify", "document",
        "improve", "enhance", "adjust", "correct", "repair", "troubleshoot",
        "debugging", "polish", "finalize", "complete", "finish"
    ]

    def __init__(self):
        self.keyword_weights = {
            WorkType.DEEP: {kw: 1.0 for kw in self.DEEP_KEYWORDS},
            WorkType.SHALLOW: {kw: 1.0 for kw in self.SHALLOW_KEYWORDS},
            WorkType.MAINTENANCE: {kw: 1.0 for kw in self.MAINTENANCE_KEYWORDS},
        }

    def suggest_work_type(
        self,
        activity_description: str,
        historical_sessions: Optional[List[PerformanceSession]] = None
    ) -> WorkTypeSuggestion:
        """
        Suggest work type based on activity description and historical patterns.

        Args:
            activity_description: Description of the activity
            historical_sessions: Optional list of historical sessions for pattern learning

        Returns:
            WorkTypeSuggestion with suggested type and confidence
        """
        # Convert to lowercase for matching
        text = activity_description.lower()

        # Calculate keyword scores
        scores = self._calculate_keyword_scores(text)

        # Apply historical patterns if available
        if historical_sessions:
            scores = self._apply_historical_patterns(scores, historical_sessions, text)

        # Find best match
        best_type = max(scores.items(), key=lambda x: x[1])

        # Determine confidence level
        confidence = self._determine_confidence(best_type[1], scores)

        # Generate reasons
        reasons = self._generate_reasons(best_type[0], text, scores)

        return WorkTypeSuggestion(
            work_type=best_type[0],
            confidence=confidence,
            reasons=reasons,
            score=best_type[1]
        )

    def _calculate_keyword_scores(self, text: str) -> Dict[WorkType, float]:
        """Calculate scores based on keyword matches."""
        scores = {wt: 0.0 for wt in [WorkType.DEEP, WorkType.SHALLOW, WorkType.MAINTENANCE]}

        for work_type, keywords in self.keyword_weights.items():
            for keyword, weight in keywords.items():
                if keyword in text:
                    scores[work_type] += weight

        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        return scores

    def _apply_historical_patterns(
        self,
        scores: Dict[WorkType, float],
        historical_sessions: List[PerformanceSession],
        current_text: str
    ) -> Dict[WorkType, float]:
        """Adjust scores based on historical patterns."""
        if not historical_sessions:
            return scores

        # Find similar historical sessions
        similar_sessions = []
        for session in historical_sessions:
            if session.context.activity_description:
                session_text = session.context.activity_description.lower()
                # Simple similarity: check for common words
                common_words = set(current_text.split()) & set(session_text.split())
                if len(common_words) >= 1:  # At least one common word
                    similar_sessions.append(session)

        if not similar_sessions:
            return scores

        # Count work types in similar sessions
        type_counts = {wt: 0 for wt in scores.keys()}
        for session in similar_sessions:
            if session.context.work_type in type_counts:
                type_counts[session.context.work_type] += 1

        # Calculate historical weights (0.3 weight for historical patterns)
        total_similar = len(similar_sessions)
        historical_weights = {
            wt: (count / total_similar) * 0.3 if total_similar > 0 else 0
            for wt, count in type_counts.items()
        }

        # Combine with keyword scores (0.7 weight for keywords)
        combined = {
            wt: (scores.get(wt, 0) * 0.7) + historical_weights.get(wt, 0)
            for wt in scores.keys()
        }

        return combined

    def _determine_confidence(self, best_score: float, all_scores: Dict[WorkType, float]) -> ConfidenceLevel:
        """Determine confidence level based on score distribution."""
        if best_score >= 0.7:
            return ConfidenceLevel.HIGH
        elif best_score >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _generate_reasons(self, work_type: WorkType, text: str, scores: Dict[WorkType, float]) -> List[str]:
        """Generate human-readable reasons for the suggestion."""
        reasons = []

        # Add keyword-based reasons
        keywords = self.keyword_weights.get(work_type, {})
        matched_keywords = [kw for kw in keywords if kw in text]
        if matched_keywords:
            reasons.append(f"Keywords matched: {', '.join(matched_keywords[:3])}")

        # Add score-based reason
        score_percent = int(scores[work_type] * 100)
        reasons.append(f"Confidence score: {score_percent}%")

        # Add comparison with other types
        other_types = [wt for wt in scores.keys() if wt != work_type]
        if other_types:
            next_best = max(other_types, key=lambda wt: scores[wt])
            diff = int((scores[work_type] - scores[next_best]) * 100)
            if diff > 0:
                reasons.append(f"{diff}% higher than {next_best.value}")

        return reasons

    def learn_from_correction(
        self,
        original_suggestion: WorkTypeSuggestion,
        corrected_type: WorkType,
        activity_description: str
    ) -> None:
        """
        Learn from user corrections to improve future suggestions.

        Args:
            original_suggestion: The original suggestion that was corrected
            corrected_type: The work type the user selected
            activity_description: The activity description
        """
        text = activity_description.lower()

        # If correction is different from suggestion, adjust weights
        if original_suggestion.work_type != corrected_type:
            # Boost keywords for corrected type
            if corrected_type in self.keyword_weights:
                for keyword in self.keyword_weights[corrected_type]:
                    if keyword in text:
                        self.keyword_weights[corrected_type][keyword] *= 1.2

            # Reduce keywords for incorrectly suggested type
            if original_suggestion.work_type in self.keyword_weights:
                for keyword in self.keyword_weights[original_suggestion.work_type]:
                    if keyword in text:
                        self.keyword_weights[original_suggestion.work_type][keyword] *= 0.8