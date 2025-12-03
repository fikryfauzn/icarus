"""
Flask HTTP API for Icarus (Headless).

This is a pure JSON API layer over the service layer.
It supports the Svelte frontend via CORS.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

from ..app_bootstrap import create_app, AppContainer
from ..config.settings import DATE_FORMAT
from ..core.enums import CompletionStatus, Domain, WorkType
from ..core.models import DaySummary, PerformanceSession, SleepNight, Task
from ..services.analytics_service import WeeklyStats
from ..services.sleep_service import SleepInput, SleepValidationError
from ..services.session_service import (
    EndSessionInput,
    SessionNotFoundError,
    ManualSessionInput,
    SessionService,
    SessionValidationError,
    StartSessionInput,
    UpdateWorkTypeInput,
)
from ..services.work_type_classifier import WorkTypeClassifier, WorkTypeSuggestion

# Single shared container for the process
_container: AppContainer = create_app()

app = Flask(__name__)
# Enable Cross-Origin Resource Sharing so Svelte (port 5173) can talk to Flask (port 5000)
CORS(app)


# ---------------------------------------------------------------------------
# Helpers: parsing
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError as e:
        raise ValueError(f"Invalid date '{value}', expected format {DATE_FORMAT}") from e


def _parse_iso_datetime(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except ValueError as e:
        # Fallback for weird formats if necessary
        raise ValueError(
            f"Invalid datetime '{value}', expected ISO format."
        ) from e

# ---------------------------------------------------------------------------
# Helpers: serialization
# ---------------------------------------------------------------------------


def _sleep_to_dict(sleep: SleepNight) -> Dict[str, Any]:
    return {
        "date": sleep.date.isoformat(),
        "sleep_start": sleep.sleep_start.isoformat(),
        "sleep_end": sleep.sleep_end.isoformat(),
        "sleep_quality": sleep.sleep_quality,
        "awakenings_count": sleep.awakenings_count,
        "energy_morning": sleep.energy_morning,
        "mood_morning": sleep.mood_morning,
        "screen_last_hour": sleep.screen_last_hour,
        "caffeine_after_17": sleep.caffeine_after_17,
        "bedtime_consistent": sleep.bedtime_consistent,
        "duration_minutes": sleep.duration_minutes(),
    }


def _session_to_dict(session: PerformanceSession) -> Dict[str, Any]:
    ctx = session.context
    before = session.before
    after = session.after
    outcome = session.outcome

    return {
        "id": session.id,
        "start_time": session.start_time.isoformat(),
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "date": session.date.isoformat(),
        "duration_minutes": session.duration_minutes,
        "context": {
            "domain": ctx.domain.value,
            "project_name": ctx.project_name,
            "activity_description": ctx.activity_description,
            "work_type": ctx.work_type.value,
            "planned_duration_min": ctx.planned_duration_min,
        },
        "before": {
            "energy": before.energy,
            "stress": before.stress,
            "resistance": before.resistance,
        },
        "after": (
            {
                "energy": after.energy,
                "stress": after.stress,
                "feel_tag": after.feel_tag,
            }
            if after
            else None
        ),
        "outcome": (
            {
                "completion_status": outcome.completion_status.value,
                "progress_rating": outcome.progress_rating,
                "quality_rating": outcome.quality_rating,
                "focus_quality": outcome.focus_quality,
                "moves_main_goal": outcome.moves_main_goal,
                "evidence_note": outcome.evidence_note,
            }
            if outcome
            else None
        ),
        "energy_delta": session.energy_delta,
        "stress_delta": session.stress_delta,
        "is_finished": session.is_finished,
    }


def _day_summary_to_dict(summary: DaySummary) -> Dict[str, Any]:
    return {
        "date": summary.date.isoformat(),
        "total_sessions": summary.total_sessions,
        "deep_minutes": summary.deep_minutes,
        "shallow_minutes": summary.shallow_minutes,
        "maintenance_minutes": summary.maintenance_minutes,
        "minutes_by_domain": {d.value: m for d, m in summary.minutes_by_domain.items()},
        "avg_focus_quality": summary.avg_focus_quality,
        "avg_progress_rating": summary.avg_progress_rating,
        "avg_quality_rating": summary.avg_quality_rating,
        "sleep_duration_minutes": summary.sleep_duration_minutes,
        "sleep_quality": summary.sleep_quality,
        "energy_morning": summary.energy_morning,
    }


def _weekly_stats_to_dict(stats: WeeklyStats) -> Dict[str, Any]:
    return {
        "week_start": stats.week_start.isoformat(),
        "week_end": stats.week_end.isoformat(),
        "total_sessions": stats.total_sessions,
        "deep_minutes": stats.deep_minutes,
        "shallow_minutes": stats.shallow_minutes,
        "maintenance_minutes": stats.maintenance_minutes,
        "minutes_by_domain": {d.value: m for d, m in stats.minutes_by_domain.items()},
        "avg_focus_quality": stats.avg_focus_quality,
        "avg_progress_rating": stats.avg_progress_rating,
        "avg_quality_rating": stats.avg_quality_rating,
        "avg_sleep_duration_minutes": stats.avg_sleep_duration_minutes,
        "avg_sleep_quality": stats.avg_sleep_quality,
        "avg_energy_morning": stats.avg_energy_morning,
    }


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(SleepValidationError)
@app.errorhandler(SessionValidationError)
@app.errorhandler(ValueError)
def handle_validation_error(err: Exception):
    response = {
        "error": "validation_error",
        "message": str(err),
    }
    return jsonify(response), 400


@app.errorhandler(SessionNotFoundError)
def handle_not_found(err: Exception):
    response = {
        "error": "not_found",
        "message": str(err),
    }
    return jsonify(response), 404


@app.errorhandler(Exception)
def handle_generic_error(err: Exception):
    # Last-resort handler; in dev you’ll still see tracebacks in console.
    response = {
        "error": "internal_error",
        "message": str(err),
    }
    return jsonify(response), 500


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index() -> Any:
    """
    Root endpoint to verify API is running.
    """
    return jsonify({
        "service": "Icarus Performance OS",
        "status": "online",
        "version": "1.0.0 (Headless)"
    })

@app.route("/api/health", methods=["GET"])
def health() -> Any:
    """
    Simple health check.
    """
    return jsonify({"status": "ok"})

@app.route("/api/sleep-vs-deepwork", methods=["GET"])
def sleep_vs_deepwork() -> Any:
    """
    Sleep vs deep work series.
    Query params: ?start=YYYY-MM-DD&end=YYYY-MM-DD
    """
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    if not start_str or not end_str:
        raise ValueError("Both 'start' and 'end' query parameters are required.")

    start = _parse_date(start_str)
    end = _parse_date(end_str)

    series = _container.analytics_service.get_sleep_vs_deepwork_series(start, end)
    data = [
        {
            "date": d.isoformat(),
            "sleep_minutes": sleep_minutes,
            "deep_minutes": deep_minutes,
        }
        for (d, sleep_minutes, deep_minutes) in series
    ]
    return jsonify(data), 200


@app.route("/api/sleep", methods=["POST"])
def log_sleep() -> Any:
    """
    Log or update sleep.
    """
    payload = request.get_json(force=True)

    sleep_input = SleepInput(
        date=_parse_date(payload["date"]),
        sleep_start=_parse_iso_datetime(payload["sleep_start"]),
        sleep_end=_parse_iso_datetime(payload["sleep_end"]),
        sleep_quality=int(payload["sleep_quality"]),
        awakenings_count=int(payload.get("awakenings_count", 0)),
        energy_morning=int(payload["energy_morning"]),
        mood_morning=int(payload["mood_morning"]),
        screen_last_hour=bool(payload.get("screen_last_hour", False)),
        caffeine_after_17=bool(payload.get("caffeine_after_17", False)),
        bedtime_consistent=bool(payload.get("bedtime_consistent", False)),
    )

    sleep = _container.sleep_service.log_sleep(sleep_input)
    return jsonify(_sleep_to_dict(sleep)), 200


@app.route("/api/sessions", methods=["POST"])
def start_session() -> Any:
    """
    Start a new session.
    """
    payload = request.get_json(force=True)

    start_input = StartSessionInput(
        domain=Domain(payload["domain"]),
        project_name=payload["project_name"],
        activity_description=payload["activity_description"],
        work_type=WorkType(payload["work_type"]),
        planned_duration_min=(
            int(payload["planned_duration_min"])
            if payload.get("planned_duration_min") is not None
            else None
        ),
        energy_before=int(payload["energy_before"]),
        stress_before=int(payload["stress_before"]),
        resistance_before=int(payload["resistance_before"]),
    )

    session = _container.session_service.start_session(start_input)
    return jsonify(_session_to_dict(session)), 201


@app.route("/api/sessions/<int:session_id>/end", methods=["POST"])
def end_session(session_id: int) -> Any:
    """
    End an existing session.
    """
    payload = request.get_json(force=True)

    end_input = EndSessionInput(
        completion_status=CompletionStatus(payload["completion_status"]),
        progress_rating=int(payload["progress_rating"]),
        quality_rating=int(payload["quality_rating"]),
        focus_quality=int(payload["focus_quality"]),
        moves_main_goal=bool(payload.get("moves_main_goal", False)),
        evidence_note=payload.get("evidence_note"),
        energy_after=int(payload["energy_after"]),
        stress_after=int(payload["stress_after"]),
        feel_tag=payload["feel_tag"],
    )

    session = _container.session_service.end_session(session_id, end_input)
    return jsonify(_session_to_dict(session)), 200


@app.route("/api/day-summary", methods=["GET"])
def day_summary() -> Any:
    """
    Get summary for a single day.
    Query param: ?date=YYYY-MM-DD
    """
    date_str = request.args.get("date")
    if date_str:
        day = _parse_date(date_str)
    else:
        day = date.today()

    summary = _container.day_service.build_day_summary(day)
    return jsonify(_day_summary_to_dict(summary)), 200


@app.route("/api/weekly-stats", methods=["GET"])
def weekly_stats() -> Any:
    """
    Get weekly stats.
    Query param: ?week_start=YYYY-MM-DD
    """
    week_start_str = request.args.get("week_start")
    if week_start_str:
        week_start = _parse_date(week_start_str)
    else:
        today = date.today()
        # Default to this week's Monday
        week_start = today - timedelta(days=today.weekday())

    stats = _container.analytics_service.get_weekly_stats(week_start)
    return jsonify(_weekly_stats_to_dict(stats)), 200

@app.route("/api/sessions/active", methods=["GET"])
def get_active_session() -> Any:
    """
    Check if there is a session currently running (unfinished).
    """
    session = _container.session_service.get_latest_open_session()
    if session is None:
        return jsonify(None), 200
    return jsonify(_session_to_dict(session)), 200

@app.route("/api/sessions", methods=["GET"])
def list_sessions() -> Any:
    """
    List sessions between start_date and end_date.
    Query params: ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """
    start_str = request.args.get("start_date")
    end_str = request.args.get("end_date")

    # Default to today if parameters are missing
    if not start_str or not end_str:
        today = date.today()
        start = today
        end = today
    else:
        start = _parse_date(start_str)
        end = _parse_date(end_str)

    sessions = _container.session_service.get_sessions_between(start, end)
    return jsonify([_session_to_dict(s) for s in sessions]), 200

@app.route("/api/history/sessions", methods=["GET"])
def history_sessions() -> Any:
    """
    Get a list of recent sessions (e.g., last 50), ordered by date desc.
    Query params: ?limit=50
    """
    limit = int(request.args.get("limit", 50))
    # We can use list_all_sessions and slice it, or add a proper limit query later.
    # For now, getting all and slicing in Python is acceptable for <10k records.
    all_sessions = _container.session_service.get_all_sessions()
    
    # Sort Descending (Newest first)
    sorted_sessions = sorted(
        all_sessions, 
        key=lambda s: s.start_time, 
        reverse=True
    )
    return jsonify([_session_to_dict(s) for s in sorted_sessions[:limit]]), 200


@app.route("/api/history/sleep", methods=["GET"])
def history_sleep() -> Any:
    """
    Get a list of recent sleep records (e.g., last 30), ordered by date desc.
    Query params: ?limit=30
    """
    limit = int(request.args.get("limit", 30))
    # Using existing service method, requesting 30 days back-ish
    # Actually, let's just fetch a wide range for now.
    end = date.today()
    start = end - timedelta(days=limit)
    
    sleeps = _container.sleep_service.get_recent_sleep(days=limit, inclusive_of_today=True)
    
    # Sort Descending
    sorted_sleeps = sorted(
        sleeps, 
        key=lambda s: s.date, 
        reverse=True
    )
    return jsonify([_sleep_to_dict(s) for s in sorted_sleeps]), 200


@app.route("/api/analytics/calendar", methods=["GET"])
def analytics_calendar() -> Any:
    data = _container.analytics_service.get_calendar_data()
    return jsonify(data), 200

@app.route("/api/sleep", methods=["GET"])
def get_sleep() -> Any:
    """
    Get sleep record for a specific date.
    Query param: ?date=YYYY-MM-DD
    """
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Date required"}), 400
        
    day = _parse_date(date_str)
    sleep = _container.sleep_service.get_sleep_by_date(day)
    
    if sleep is None:
        return jsonify(None), 200
        
    return jsonify(_sleep_to_dict(sleep)), 200

@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def delete_session(session_id: int) -> Any:
    _container.session_service.delete_session(session_id)
    return jsonify({"status": "deleted"}), 200

@app.route("/api/sessions/<int:session_id>/work-type", methods=["PUT"])
def update_session_work_type(session_id: int) -> Any:
    """
    Update the work type of an existing session.
    """
    payload = request.get_json(force=True)

    update_input = UpdateWorkTypeInput(
        work_type=WorkType(payload["work_type"])
    )

    session = _container.session_service.update_session_work_type(session_id, update_input)
    return jsonify(_session_to_dict(session)), 200

@app.route("/api/suggest-work-type", methods=["POST"])
def suggest_work_type() -> Any:
    """
    Suggest work type based on activity description.
    """
    payload = request.get_json(force=True)
    activity_description = payload.get("activity_description", "")

    if not activity_description:
        return jsonify({"error": "activity_description is required"}), 400

    # Get recent sessions for historical context
    recent_sessions = _container.session_service.get_all_sessions()[-50:]  # Last 50 sessions

    suggestion = _container.work_type_classifier.suggest_work_type(
        activity_description=activity_description,
        historical_sessions=recent_sessions
    )

    return jsonify({
        "suggested_work_type": suggestion.work_type.value,
        "confidence": suggestion.confidence.value,
        "score": suggestion.score,
        "reasons": suggestion.reasons
    }), 200

@app.route("/api/sessions/manual", methods=["POST"])
def log_manual_session() -> Any:
    """
    Log a session that already happened (retro-active).
    """
    payload = request.get_json(force=True)
    
    manual_input = ManualSessionInput(
        # Timing
        start_time=_parse_iso_datetime(payload["start_time"]),
        end_time=_parse_iso_datetime(payload["end_time"]),
        
        # Context
        domain=Domain(payload["domain"]),
        project_name=payload["project_name"],
        activity_description=payload["activity_description"],
        work_type=WorkType(payload["work_type"]),
        planned_duration_min=payload.get("planned_duration_min"),
        
        # Before
        energy_before=int(payload["energy_before"]),
        stress_before=int(payload["stress_before"]),
        resistance_before=int(payload["resistance_before"]),
        
        # Outcome
        completion_status=CompletionStatus(payload["completion_status"]),
        progress_rating=int(payload["progress_rating"]),
        quality_rating=int(payload["quality_rating"]),
        focus_quality=int(payload["focus_quality"]),
        moves_main_goal=bool(payload.get("moves_main_goal", False)),
        evidence_note=payload.get("evidence_note"),
        
        # After
        energy_after=int(payload["energy_after"]),
        stress_after=int(payload["stress_after"]),
        feel_tag=payload["feel_tag"],
    )

    session = _container.session_service.log_manual_session(manual_input)
    return jsonify(_session_to_dict(session)), 201

def _get_date_range_from_args():
    """Helper to extract start/end from query params or default to Today."""
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    if start_str and end_str and start_str.strip() and end_str.strip():
        return _parse_date(start_str), _parse_date(end_str)

    return date.today(), date.today()

@app.route("/api/analytics/score", methods=["GET"])
def analytics_score() -> Any:
    start, end = _get_date_range_from_args()
    score = _container.analytics_service.get_aggregate_score(start, end)
    return jsonify({"score": score}), 200

@app.route("/api/analytics/patterns", methods=["GET"])
def analytics_patterns() -> Any:
    start, end = _get_date_range_from_args()
    patterns = _container.analytics_service.get_session_patterns(start, end)
    return jsonify(patterns), 200

@app.route("/api/analytics/chronotype", methods=["GET"])
def analytics_chronotype() -> Any:
    start, end = _get_date_range_from_args()
    data = _container.analytics_service.get_chronotype_profile(start, end)
    return jsonify(data), 200

@app.route("/api/analytics/energy-ledger", methods=["GET"])
def analytics_energy_ledger() -> Any:
    start, end = _get_date_range_from_args()
    data = _container.analytics_service.get_energy_ledger(start, end)
    return jsonify(data), 200

@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    tasks = _container.task_storage.list()
    return jsonify([{
        "id": t.id, "domain": t.domain.value, "project_name": t.project_name, 
        "activity_description": t.activity_description, "work_type": t.work_type.value
    } for t in tasks])

@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json(force=True)
    task = Task(
        id=None,
        domain=Domain(data['domain']),
        project_name=data['project_name'],
        activity_description=data['activity_description'],
        work_type=WorkType(data['work_type']),
        created_at=datetime.now()
    )
    new_task = _container.task_storage.create(task)
    return jsonify({"id": new_task.id}), 201

@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    _container.task_storage.delete(task_id)
    return jsonify({"status": "ok"})
    
@app.route("/api/intake", methods=["GET"])
def get_intake():
    date_str = request.args.get("date", str(date.today()))
    day = _parse_date(date_str)
    data = _container.intake_service.get_intake(day)
    return jsonify({
        "date": data.date.isoformat(),
        "water_count": data.water_count,
        "breakfast_time": data.breakfast_time.isoformat() if data.breakfast_time else None,
        "lunch_time": data.lunch_time.isoformat() if data.lunch_time else None,
        "dinner_time": data.dinner_time.isoformat() if data.dinner_time else None,
    })

@app.route("/api/intake/water", methods=["POST"])
def add_water():
    # Always assumes 'today' for quick logging
    data = _container.intake_service.add_water(date.today())
    return jsonify({"water_count": data.water_count})

@app.route("/api/intake/meal", methods=["POST"])
def log_meal():
    payload = request.get_json(force=True)
    meal_type = payload.get("type") # 'breakfast', 'lunch', 'dinner'
    if meal_type not in ['breakfast', 'lunch', 'dinner']:
        return jsonify({"error": "Invalid meal type"}), 400
        
    data = _container.intake_service.log_meal(date.today(), meal_type)
    return jsonify({"status": "logged", "type": meal_type})

# Optional: process-level cleanup
@app.teardown_appcontext
def teardown(exception):
    pass

if __name__ == "__main__":
    app.run(debug=True)