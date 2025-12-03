"""
Command-line interface for the personal performance OS.

Provides simple commands to:
- log sleep
- start a session
- end a session
- inspect daily and weekly stats
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from typing import Optional

from ..app_bootstrap import create_app, AppContainer
from ..config.settings import DATE_FORMAT, DATETIME_FORMAT
from ..core.enums import CompletionStatus, Domain, WorkType
from ..services.sleep_service import SleepInput, SleepValidationError
from ..services.session_service import (
    EndSessionInput,
    ManualSessionInput,
    SessionNotFoundError,
    SessionService,
    SessionValidationError,
    StartSessionInput,
)
from ..services.day_service import DayService
from ..services.analytics_service import AnalyticsService


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
    return datetime.strptime(value, DATE_FORMAT).date()


def _parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, DATETIME_FORMAT)


def _print_header(title: str) -> None:
    print("=" * len(title))
    print(title)
    print("=" * len(title))


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_sleep_log(args: argparse.Namespace, app: AppContainer) -> None:
    """
    Log or update a sleep record for a given date.
    """
    try:
        day = _parse_date(args.date) if args.date else date.today()
        sleep_start = _parse_datetime(args.start)
        sleep_end = _parse_datetime(args.end)

        sleep_input = SleepInput(
            date=day,
            sleep_start=sleep_start,
            sleep_end=sleep_end,
            sleep_quality=args.quality,
            awakenings_count=args.awakenings,
            energy_morning=args.energy,
            mood_morning=args.mood,
            screen_last_hour=args.screen_last_hour,
            caffeine_after_17=args.caffeine_after_17,
            bedtime_consistent=args.bedtime_consistent,
        )

        sleep = app.sleep_service.log_sleep(sleep_input)

    except SleepValidationError as e:
        print("Sleep validation error:")
        print(e)
        return
    except ValueError as e:
        print("Invalid input:")
        print(e)
        return

    _print_header("Sleep logged")
    print(f"Date:           {sleep.date.isoformat()}")
    print(f"Duration (min): {sleep.duration_minutes()}")
    print(f"Quality:        {sleep.sleep_quality}")
    print(f"Energy morning: {sleep.energy_morning}")
    print(f"Mood morning:   {sleep.mood_morning}")


def cmd_session_start(args: argparse.Namespace, app: AppContainer) -> None:
    """
    Start a new performance session.
    """
    try:
        domain = Domain(args.domain)
        work_type = WorkType(args.work_type)

        planned_duration = args.planned_duration
        if planned_duration is not None and planned_duration <= 0:
            raise ValueError("planned_duration must be positive if provided.")

        start_input = StartSessionInput(
            domain=domain,
            project_name=args.project,
            activity_description=args.activity,
            work_type=work_type,
            planned_duration_min=planned_duration,
            energy_before=args.energy_before,
            stress_before=args.stress_before,
            resistance_before=args.resistance_before,
        )

        session = app.session_service.start_session(start_input)

    except (SessionValidationError, ValueError) as e:
        print("Session start error:")
        print(e)
        return

    _print_header("Session started")
    print(f"Session id:   {session.id}")
    print(f"Start time:   {session.start_time}")
    print(f"Domain:       {session.context.domain.value}")
    print(f"Project:      {session.context.project_name}")
    print(f"Activity:     {session.context.activity_description}")
    print(f"Work type:    {session.context.work_type.value}")
    print(f"Energy before:{session.before.energy}")
    print(f"Stress before:{session.before.stress}")

def cmd_session_log_manual(args: argparse.Namespace, app: AppContainer) -> None:
    """
    Log a completed session with manual start/end times in a single step.
    """
    try:
        domain = Domain(args.domain)
        work_type = WorkType(args.work_type)
        completion_status = CompletionStatus(args.completion_status)

        start_time = _parse_datetime(args.start)
        end_time = _parse_datetime(args.end)

        planned_duration = args.planned_duration
        if planned_duration is not None and planned_duration <= 0:
            raise ValueError("planned_duration must be positive if provided.")

        manual_input = ManualSessionInput(
            start_time=start_time,
            end_time=end_time,
            domain=domain,
            project_name=args.project,
            activity_description=args.activity,
            work_type=work_type,
            planned_duration_min=planned_duration,
            energy_before=args.energy_before,
            stress_before=args.stress_before,
            resistance_before=args.resistance_before,
            completion_status=completion_status,
            progress_rating=args.progress_rating,
            quality_rating=args.quality_rating,
            focus_quality=args.focus_quality,
            moves_main_goal=args.moves_main_goal,
            evidence_note=args.evidence_note,
            energy_after=args.energy_after,
            stress_after=args.stress_after,
            feel_tag=args.feel_tag,
        )

        session = app.session_service.log_manual_session(manual_input)

    except (SessionValidationError, ValueError) as e:
        print("Manual session log error:")
        print(e)
        return

    _print_header("Manual session logged")
    print(f"Session id:     {session.id}")
    print(f"Start time:     {session.start_time}")
    print(f"End time:       {session.end_time}")
    print(f"Duration (min): {session.duration_minutes}")
    print(f"Domain:         {session.context.domain.value}")
    print(f"Project:        {session.context.project_name}")
    print(f"Completion:     {session.outcome.completion_status.value}")
    print(f"Progress:       {session.outcome.progress_rating}")
    print(f"Quality:        {session.outcome.quality_rating}")
    print(f"Focus:          {session.outcome.focus_quality}")
    print(f"Energy delta:   {session.energy_delta}")
    print(f"Stress delta:   {session.stress_delta}")



def cmd_session_end(args: argparse.Namespace, app: AppContainer) -> None:
    """
    End an existing performance session.
    """
    try:
        completion_status = CompletionStatus(args.completion_status)

        end_input = EndSessionInput(
            completion_status=completion_status,
            progress_rating=args.progress_rating,
            quality_rating=args.quality_rating,
            focus_quality=args.focus_quality,
            moves_main_goal=args.moves_main_goal,
            evidence_note=args.evidence_note,
            energy_after=args.energy_after,
            stress_after=args.stress_after,
            feel_tag=args.feel_tag,
        )

        session = app.session_service.end_session(args.id, end_input)

    except SessionNotFoundError as e:
        print(e)
        return
    except (SessionValidationError, ValueError) as e:
        print("Session end error:")
        print(e)
        return

    _print_header("Session ended")
    print(f"Session id:     {session.id}")
    print(f"Start time:     {session.start_time}")
    print(f"End time:       {session.end_time}")
    print(f"Duration (min): {session.duration_minutes}")
    print(f"Domain:         {session.context.domain.value}")
    print(f"Project:        {session.context.project_name}")
    print(f"Completion:     {session.outcome.completion_status.value}")
    print(f"Progress:       {session.outcome.progress_rating}")
    print(f"Quality:        {session.outcome.quality_rating}")
    print(f"Focus:          {session.outcome.focus_quality}")
    print(f"Energy delta:   {session.energy_delta}")
    print(f"Stress delta:   {session.stress_delta}")


def cmd_day_summary(args: argparse.Namespace, app: AppContainer) -> None:
    """
    Show a summary for a single day.
    """
    day = _parse_date(args.date) if args.date else date.today()
    summary = app.day_service.build_day_summary(day)

    _print_header(f"Day summary - {summary.date.isoformat()}")

    print(f"Total sessions:      {summary.total_sessions}")
    print(f"Deep minutes:        {summary.deep_minutes}")
    print(f"Shallow minutes:     {summary.shallow_minutes}")
    print(f"Maintenance minutes: {summary.maintenance_minutes}")

    print("\nMinutes by domain:")
    if summary.minutes_by_domain:
        for domain, minutes in summary.minutes_by_domain.items():
            print(f"  {domain.value:16} {minutes:4} min")
    else:
        print("  (none)")

    print("\nSession averages (where available):")
    print(f"  Focus quality:   {summary.avg_focus_quality}")
    print(f"  Progress rating: {summary.avg_progress_rating}")
    print(f"  Quality rating:  {summary.avg_quality_rating}")

    print("\nSleep:")
    print(f"  Duration (min):  {summary.sleep_duration_minutes}")
    print(f"  Sleep quality:   {summary.sleep_quality}")
    print(f"  Energy morning:  {summary.energy_morning}")


def cmd_weekly_stats(args: argparse.Namespace, app: AppContainer) -> None:
    """
    Show weekly statistics for a 7-day window.
    """
    if args.week_start:
        week_start = _parse_date(args.week_start)
    else:
        # Default: current week starting Monday
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    stats = app.analytics_service.get_weekly_stats(week_start)

    _print_header(
        f"Weekly stats - {stats.week_start.isoformat()} to {stats.week_end.isoformat()}"
    )

    print(f"Total sessions:      {stats.total_sessions}")
    print(f"Deep minutes:        {stats.deep_minutes}")
    print(f"Shallow minutes:     {stats.shallow_minutes}")
    print(f"Maintenance minutes: {stats.maintenance_minutes}")

    print("\nMinutes by domain:")
    if stats.minutes_by_domain:
        for domain, minutes in stats.minutes_by_domain.items():
            print(f"  {domain.value:16} {minutes:4} min")
    else:
        print("  (none)")

    print("\nSession averages (over days with data):")
    print(f"  Focus quality:   {stats.avg_focus_quality}")
    print(f"  Progress rating: {stats.avg_progress_rating}")
    print(f"  Quality rating:  {stats.avg_quality_rating}")

    print("\nSleep (over days with data):")
    print(f"  Avg duration (min): {stats.avg_sleep_duration_minutes}")
    print(f"  Avg quality:        {stats.avg_sleep_quality}")
    print(f"  Avg energy morning: {stats.avg_energy_morning}")


# ---------------------------------------------------------------------------
# Argument parser setup
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Personal performance OS CLI",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # sleep-log
    p_sleep = subparsers.add_parser(
        "sleep-log",
        help="Log or update a sleep record",
    )
    p_sleep.add_argument(
        "--date",
        type=str,
        help=f"Date in format {DATE_FORMAT} (default: today)",
    )
    p_sleep.add_argument(
        "--start",
        type=str,
        required=True,
        help=f"Sleep start datetime in format '{DATETIME_FORMAT}'",
    )
    p_sleep.add_argument(
        "--end",
        type=str,
        required=True,
        help=f"Sleep end datetime in format '{DATETIME_FORMAT}'",
    )
    p_sleep.add_argument(
        "--quality",
        type=int,
        default=3,
        help="Sleep quality 1–5 (default: 3)",
    )
    p_sleep.add_argument(
        "--awakenings",
        type=int,
        default=0,
        help="Number of awakenings (default: 0)",
    )
    p_sleep.add_argument(
        "--energy",
        type=int,
        required=True,
        help="Morning energy 1–10",
    )
    p_sleep.add_argument(
        "--mood",
        type=int,
        required=True,
        help="Morning mood 1–10",
    )
    p_sleep.add_argument(
        "--screen-last-hour",
        action="store_true",
        help="Set if you used screens in the last hour before sleep",
    )
    p_sleep.add_argument(
        "--caffeine-after-17",
        action="store_true",
        help="Set if you consumed caffeine after 17:00",
    )
    p_sleep.add_argument(
        "--bedtime-consistent",
        action="store_true",
        help="Set if bedtime was within ~30 minutes of your usual time",
    )
    p_sleep.set_defaults(handler=cmd_sleep_log)

    # session-start
    p_start = subparsers.add_parser(
        "session-start",
        help="Start a new performance session",
    )
    p_start.add_argument(
        "--domain",
        type=str,
        required=True,
        choices=[d.value for d in Domain],
        help="Domain of the session",
    )
    p_start.add_argument(
        "--project",
        type=str,
        required=True,
        help="Project name",
    )
    p_start.add_argument(
        "--activity",
        type=str,
        required=True,
        help="Short activity description",
    )
    p_start.add_argument(
        "--work-type",
        type=str,
        required=True,
        choices=[w.value for w in WorkType],
        help="Work type",
    )
    p_start.add_argument(
        "--planned-duration",
        type=int,
        help="Planned duration in minutes (optional)",
    )
    p_start.add_argument(
        "--energy-before",
        type=int,
        required=True,
        help="Energy before 1–10",
    )
    p_start.add_argument(
        "--stress-before",
        type=int,
        required=True,
        help="Stress before 1–10",
    )
    p_start.add_argument(
        "--resistance-before",
        type=int,
        required=True,
        help="Resistance to starting 1–5",
    )
    p_start.set_defaults(handler=cmd_session_start)

    # session-end
    p_end = subparsers.add_parser(
        "session-end",
        help="End an existing performance session",
    )
    p_end.add_argument(
        "id",
        type=int,
        help="Session id to end",
    )
    p_end.add_argument(
        "--completion-status",
        type=str,
        required=True,
        choices=[c.value for c in CompletionStatus],
        help="How the session ended",
    )
    p_end.add_argument(
        "--progress-rating",
        type=int,
        required=True,
        help="Progress rating 1–5",
    )
    p_end.add_argument(
        "--quality-rating",
        type=int,
        required=True,
        help="Quality rating 1–5",
    )
    p_end.add_argument(
        "--focus-quality",
        type=int,
        required=True,
        help="Focus quality 1–5",
    )
    p_end.add_argument(
        "--moves-main-goal",
        action="store_true",
        help="Set if this session moved a main goal",
    )
    p_end.add_argument(
        "--evidence-note",
        type=str,
        help="Optional evidence note (screenshot, commit, pages, etc.)",
    )
    p_end.add_argument(
        "--energy-after",
        type=int,
        required=True,
        help="Energy after 1–10",
    )
    p_end.add_argument(
        "--stress-after",
        type=int,
        required=True,
        help="Stress after 1–10",
    )
    p_end.add_argument(
        "--feel-tag",
        type=str,
        required=True,
        help="One-word feeling tag (e.g. 'clear', 'drained')",
    )
    p_end.set_defaults(handler=cmd_session_end)

        # session-log-manual
    p_log_manual = subparsers.add_parser(
        "session-log-manual",
        help="Log a completed session with manual start/end times",
    )
    p_log_manual.add_argument(
        "--start",
        type=str,
        required=True,
        help=f"Session start datetime in format '{DATETIME_FORMAT}'",
    )
    p_log_manual.add_argument(
        "--end",
        type=str,
        required=True,
        help=f"Session end datetime in format '{DATETIME_FORMAT}'",
    )
    p_log_manual.add_argument(
        "--domain",
        type=str,
        required=True,
        choices=[d.value for d in Domain],
        help="Domain of the session",
    )
    p_log_manual.add_argument(
        "--project",
        type=str,
        required=True,
        help="Project name",
    )
    p_log_manual.add_argument(
        "--activity",
        type=str,
        required=True,
        help="Short activity description",
    )
    p_log_manual.add_argument(
        "--work-type",
        type=str,
        required=True,
        choices=[w.value for w in WorkType],
        help="Work type",
    )
    p_log_manual.add_argument(
        "--planned-duration",
        type=int,
        help="Planned duration in minutes (optional)",
    )
    p_log_manual.add_argument(
        "--energy-before",
        type=int,
        required=True,
        help="Energy before 1–10",
    )
    p_log_manual.add_argument(
        "--stress-before",
        type=int,
        required=True,
        help="Stress before 1–10",
    )
    p_log_manual.add_argument(
        "--resistance-before",
        type=int,
        required=True,
        help="Resistance to starting 1–5",
    )
    p_log_manual.add_argument(
        "--completion-status",
        type=str,
        required=True,
        choices=[c.value for c in CompletionStatus],
        help="How the session ended",
    )
    p_log_manual.add_argument(
        "--progress-rating",
        type=int,
        required=True,
        help="Progress rating 1–5",
    )
    p_log_manual.add_argument(
        "--quality-rating",
        type=int,
        required=True,
        help="Quality rating 1–5",
    )
    p_log_manual.add_argument(
        "--focus-quality",
        type=int,
        required=True,
        help="Focus quality 1–5",
    )
    p_log_manual.add_argument(
        "--moves-main-goal",
        action="store_true",
        help="Set if this session moved a main goal",
    )
    p_log_manual.add_argument(
        "--evidence-note",
        type=str,
        help="Optional evidence note (screenshot, commit, pages, etc.)",
    )
    p_log_manual.add_argument(
        "--energy-after",
        type=int,
        required=True,
        help="Energy after 1–10",
    )
    p_log_manual.add_argument(
        "--stress-after",
        type=int,
        required=True,
        help="Stress after 1–10",
    )
    p_log_manual.add_argument(
        "--feel-tag",
        type=str,
        required=True,
        help="One-word feeling tag (e.g. 'clear', 'drained')",
    )
    p_log_manual.set_defaults(handler=cmd_session_log_manual)

    # day-summary
    p_day = subparsers.add_parser(
        "day-summary",
        help="Show a summary for a single day",
    )
    p_day.add_argument(
        "--date",
        type=str,
        help=f"Date in format {DATE_FORMAT} (default: today)",
    )
    p_day.set_defaults(handler=cmd_day_summary)

    # weekly-stats
    p_week = subparsers.add_parser(
        "weekly-stats",
        help="Show weekly stats (current week or specified start date)",
    )
    p_week.add_argument(
        "--week-start",
        type=str,
        help=f"Start date of week in format {DATE_FORMAT} (default: this Monday)",
    )
    p_week.set_defaults(handler=cmd_weekly_stats)

    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    app = create_app()
    try:
        handler = getattr(args, "handler", None)
        if handler is None:
            parser.print_help()
            return
        handler(args, app)
    finally:
        app.close()


if __name__ == "__main__":
    main()
