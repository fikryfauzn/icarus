"""
Service layer for higher-level analytics over days, sleep, and sessions.

Responsibilities:
- compute weekly statistics
- compute domain-level time allocation
- prepare data series for visualization (e.g. sleep vs deep work)
- compute chronotype, energy ledger, and pattern recognition
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Tuple, Any

from ..core.enums import Domain, WorkType
from ..core.models import DaySummary
from ..services.day_service import DayService
from ..services.session_service import SessionService


# ---------------------------------------------------------------------------
# Data structures for analytics outputs
# ---------------------------------------------------------------------------


@dataclass
class WeeklyStats:
    """
    Aggregate statistics for a 7-day period.
    """

    week_start: date
    week_end: date

    total_sessions: int

    deep_minutes: int
    shallow_minutes: int
    maintenance_minutes: int

    minutes_by_domain: Dict[Domain, int]

    avg_focus_quality: Optional[float]
    avg_progress_rating: Optional[float]
    avg_quality_rating: Optional[float]

    avg_sleep_duration_minutes: Optional[float]
    avg_sleep_quality: Optional[float]
    avg_energy_morning: Optional[float]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AnalyticsService:
    """
    High-level analytics on top of DaySummary objects and raw Sessions.
    """

    def __init__(self, day_service: DayService, session_service: SessionService) -> None:
        self._day_service = day_service
        self._session_service = session_service

    # ------------------------------------------------------------------ #
    # 1. Standard Reporting (Weekly / Daily)
    # ------------------------------------------------------------------ #

    def get_weekly_stats(self, week_start: date) -> WeeklyStats:
        """
        Compute WeeklyStats for the 7-day period starting at week_start.
        """
        week_end = week_start + timedelta(days=6)
        day_summaries = self._day_service.list_day_summaries(week_start, week_end)

        total_sessions = sum(d.total_sessions for d in day_summaries)

        deep_minutes = sum(d.deep_minutes for d in day_summaries)
        shallow_minutes = sum(d.shallow_minutes for d in day_summaries)
        maintenance_minutes = sum(d.maintenance_minutes for d in day_summaries)

        minutes_by_domain: Dict[Domain, int] = {}
        for d in day_summaries:
            for domain, minutes in d.minutes_by_domain.items():
                minutes_by_domain[domain] = minutes_by_domain.get(domain, 0) + minutes

        # Averages
        avg_focus_quality = self._mean_float(
            [d.avg_focus_quality for d in day_summaries if d.avg_focus_quality is not None]
        )
        avg_progress_rating = self._mean_float(
            [d.avg_progress_rating for d in day_summaries if d.avg_progress_rating is not None]
        )
        avg_quality_rating = self._mean_float(
            [d.avg_quality_rating for d in day_summaries if d.avg_quality_rating is not None]
        )

        # Sleep-related averages
        avg_sleep_duration = self._mean_float(
            [d.sleep_duration_minutes for d in day_summaries if d.sleep_duration_minutes is not None]
        )
        avg_sleep_quality = self._mean_float(
            [d.sleep_quality for d in day_summaries if d.sleep_quality is not None]
        )
        avg_energy_morning = self._mean_float(
            [d.energy_morning for d in day_summaries if d.energy_morning is not None]
        )

        return WeeklyStats(
            week_start=week_start,
            week_end=week_end,
            total_sessions=total_sessions,
            deep_minutes=deep_minutes,
            shallow_minutes=shallow_minutes,
            maintenance_minutes=maintenance_minutes,
            minutes_by_domain=minutes_by_domain,
            avg_focus_quality=avg_focus_quality,
            avg_progress_rating=avg_progress_rating,
            avg_quality_rating=avg_quality_rating,
            avg_sleep_duration_minutes=avg_sleep_duration,
            avg_sleep_quality=avg_sleep_quality,
            avg_energy_morning=avg_energy_morning,
        )

    # ------------------------------------------------------------------ #
    # 2. Performance Index (Scoring)
    # ------------------------------------------------------------------ #

    def get_daily_score(self, day: date) -> int:
        """
        Calculate a 0-100 performance score for a specific day.
        
        Formula:
        - Output (60pts): 1 point per 5 mins deep work (max 300m / 5h)
        - Input (20pts): Sleep duration > 7h (+10), Sleep quality > 3 (+10)
        - Efficiency (20pts): Avg Focus * 4
        """
        summary = self._day_service.build_day_summary(day)
        return self._compute_score_from_summary(summary)

    def get_aggregate_score(self, start_date: date, end_date: date) -> int:
        """
        Calculate the Average Daily Index over a range.
        """
        days = self._day_service.list_day_summaries(start_date, end_date)
        if not days:
            return 0
            
        total_score = sum(self._compute_score_from_summary(d) for d in days)
        return int(total_score / len(days))

    def _compute_score_from_summary(self, summary: DaySummary) -> int:
        score = 0
        
        # 1. Output (Max 60)
        score += min(60, summary.deep_minutes // 5)
        
        # 2. Input (Max 20)
        if summary.sleep_duration_minutes:
            if summary.sleep_duration_minutes >= 420: # 7h
                score += 10
            elif summary.sleep_duration_minutes >= 360: # 6h
                score += 5
            
            if summary.sleep_quality and summary.sleep_quality >= 4:
                score += 10

        # 3. Efficiency (Max 20)
        if summary.avg_focus_quality:
            score += int(summary.avg_focus_quality * 4)
            
        return min(100, score)

    # ------------------------------------------------------------------ #
    # 3. Deep Analytics (Visualizations)
    # ------------------------------------------------------------------ #

    def get_chronotype_profile(self, start_date: date, end_date: date) -> Dict[int, float]:
        """
        Aggregate focus quality by hour (0-23).
        Handles sessions spanning multiple hours.
        """
        sessions = self._session_service.get_sessions_between(start_date, end_date)
        buckets = {h: [] for h in range(24)}
        
        for s in sessions:
            # Skip incomplete sessions or those without outcomes
            if not s.outcome or not s.start_time or not s.end_time:
                continue
            
            # Current hour processing
            current_h = s.start_time.hour
            
            # Calculate duration in hours (ceiling) to cover spans
            # e.g. 18:50 to 19:10 spans 2 hours (18 and 19)
            duration_minutes = s.duration_minutes or 0
            # Simple heuristic: touch every hour block involved
            # Start at 18:50. End at 20:10. Hours: 18, 19, 20.
            
            # Loop from start hour to end hour
            end_h = s.end_time.hour
            # Handle day rollover if needed (though usually sessions are same day)
            if s.end_time.date() > s.start_time.date():
                end_h += 24
            
            for h in range(current_h, end_h + 1):
                normalized_h = h % 24
                buckets[normalized_h].append(s.outcome.focus_quality)
        
        # Average
        results = {}
        for h, scores in buckets.items():
            if scores:
                results[h] = sum(scores) / len(scores)
            else:
                results[h] = 0.0
        return results

    def get_energy_ledger(self, start_date: date, end_date: date) -> Dict[str, float]:
        """
        Aggregate energy delta (After - Before) by Domain.
        Positive = Recharging. Negative = Draining.
        """
        sessions = self._session_service.get_sessions_between(start_date, end_date)
        buckets = {}
        
        for s in sessions:
            delta = s.energy_delta
            if delta is not None:
                d = s.context.domain.value
                if d not in buckets:
                    buckets[d] = []
                buckets[d].append(delta)
        
        results = {}
        for d, deltas in buckets.items():
            results[d] = sum(deltas) / len(deltas)
            
        return results

    def get_session_patterns(self, start_date: date, end_date: date) -> Dict[str, int]:
        """
        Classify sessions into patterns based on outcome and feeling.
        """
        sessions = self._session_service.get_sessions_between(start_date, end_date)
        
        counts = {
            "Clean Win": 0,
            "Overclocked": 0,
            "Maintenance": 0,
            "Grind": 0,
            "Drift": 0
        }
        
        negative_tags = ["drained", "anxious", "tired", "wired", "frustrated", "stress"]
        
        for s in sessions:
            if not s.outcome: 
                continue
                
            wt = s.context.work_type
            if wt == WorkType.MAINTENANCE:
                counts["Maintenance"] += 1
                continue
                
            p = s.outcome.progress_rating
            f = s.outcome.focus_quality
            feel = s.after.feel_tag.lower() if s.after else ""
            
            if p >= 4:
                # High Progress
                if any(tag in feel for tag in negative_tags) or (s.energy_delta and s.energy_delta <= -2):
                    counts["Overclocked"] += 1
                else:
                    counts["Clean Win"] += 1
            elif f >= 4 and p < 4:
                # High Focus, Low Progress
                counts["Grind"] += 1
            else:
                # Low Focus, Low Progress
                counts["Drift"] += 1
                
        return counts

    def get_sleep_vs_deepwork_series(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Tuple[date, Optional[int], int]]:
        """
        Build a series of (date, sleep_duration_minutes, deep_minutes) tuples.
        """
        day_summaries = self._day_service.list_day_summaries(start_date, end_date)
        series: List[Tuple[date, Optional[int], int]] = []

        for d in day_summaries:
            series.append(
                (
                    d.date,
                    d.sleep_duration_minutes,
                    d.deep_minutes,
                )
            )

        return series

    def get_calendar_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get daily stats for the last 365 days for the Year-in-Pixels heatmap.
        """
        end = date.today()
        start = end - timedelta(weeks=52) # Last year
        
        days = self._day_service.list_day_summaries(start, end)
        
        performance_grid = []
        sleep_grid = []
        
        for d in days:
            iso = d.date.isoformat()
            
            # Use the shared scoring logic
            score = self._compute_score_from_summary(d)
            
            performance_grid.append({
                "date": iso,
                "value": score,
            })

            sleep_mins = d.sleep_duration_minutes or 0
            sleep_grid.append({
                "date": iso,
                "value": sleep_mins,
            })
            
        return {
            "performance": performance_grid,
            "sleep": sleep_grid
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _mean_float(values: List[float]) -> Optional[float]:
        """
        Return the mean of the given list of numeric values, or None if empty.
        """
        if not values:
            return None
        return sum(values) / len(values)