"""
Tkinter GUI for Icarus (personal performance OS).

Screens:
- Log Sleep
- Start Session
- End Session
- Today Summary
- History (any day)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import date, datetime, timedelta, time

from ..app_bootstrap import AppContainer, create_app
from ..config.settings import DATE_FORMAT, DATETIME_FORMAT
from ..core.enums import CompletionStatus, Domain, WorkType
from ..core.models import DaySummary, PerformanceSession
from ..services.sleep_service import SleepInput, SleepValidationError
from ..services.session_service import (
    EndSessionInput,
    SessionNotFoundError,
    SessionService,
    SessionValidationError,
    StartSessionInput,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEEL_TAG_OPTIONS = [
    "clear",
    "satisfied",
    "neutral",
    "tired",
    "drained",
    "anxious",
    "frustrated",
    "foggy",
    "proud",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
    return datetime.strptime(value, DATE_FORMAT).date()


def _today_str() -> str:
    return date.today().strftime(DATE_FORMAT)


def format_day_summary(summary: DaySummary) -> str:
    """
    Render a DaySummary as a multi-line string.
    """
    lines: list[str] = []
    lines.append(f"Day summary - {summary.date.isoformat()}")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"Total sessions:      {summary.total_sessions}")
    lines.append(f"Deep minutes:        {summary.deep_minutes}")
    lines.append(f"Shallow minutes:     {summary.shallow_minutes}")
    lines.append(f"Maintenance minutes: {summary.maintenance_minutes}")
    lines.append("")
    lines.append("Minutes by domain:")
    if summary.minutes_by_domain:
        for domain, minutes in summary.minutes_by_domain.items():
            lines.append(f"  {domain.value:16} {minutes:4} min")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Session averages (where available):")
    lines.append(f"  Focus quality:   {summary.avg_focus_quality}")
    lines.append(f"  Progress rating: {summary.avg_progress_rating}")
    lines.append(f"  Quality rating:  {summary.avg_quality_rating}")
    lines.append("")
    lines.append("Sleep:")
    lines.append(f"  Duration (min):  {summary.sleep_duration_minutes}")
    lines.append(f"  Sleep quality:   {summary.sleep_quality}")
    lines.append(f"  Energy morning:  {summary.energy_morning}")
    lines.append("")
    return "\n".join(lines)


def make_1to5_radios(parent: ttk.Frame, variable: tk.IntVar) -> ttk.Frame:
    """
    Build a row of 1–5 radio buttons bound to variable.
    """
    frame = ttk.Frame(parent)
    for i in range(1, 6):
        ttk.Radiobutton(frame, text=str(i), value=i, variable=variable).pack(
            side="left", padx=2
        )
    return frame


def make_1to10_radios(parent: ttk.Frame, variable: tk.IntVar) -> ttk.Frame:
    """
    Build a 2-row grid of 1–10 radio buttons bound to variable.
    """
    frame = ttk.Frame(parent)
    for i in range(1, 11):
        row = 0 if i <= 5 else 1
        col = (i - 1) % 5
        ttk.Radiobutton(frame, text=str(i), value=i, variable=variable).grid(
            row=row, column=col, padx=2, pady=1
        )
    return frame


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


class MainWindow(ttk.Frame):
    """
    Main Tkinter window with tabbed interface.
    """

    def __init__(self, master: tk.Tk, app: AppContainer) -> None:
        super().__init__(master)
        self.master = master
        self.app = app

        self.session_service: SessionService = app.session_service

        # In-memory pointer to "active" session id
        self._last_session_id: int | None = None

        self._configure_root()
        self._build_ui()

    def _configure_root(self) -> None:
        self.master.title("Icarus – Performance OS")
        self.master.geometry("1000x650")
        self.master.minsize(900, 550)
        self.pack(fill="both", expand=True)

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # Tabs
        self.sleep_tab = SleepTab(notebook, self.app)
        self.session_start_tab = SessionStartTab(
            notebook, self.app, self._on_session_started
        )
        self.session_end_tab = SessionEndTab(
            notebook, self.app, self._get_last_session_id
        )
        self.summary_tab = TodaySummaryTab(notebook, self.app)
        self.history_tab = HistoryTab(notebook, self.app)

        notebook.add(self.sleep_tab, text="Log Sleep")
        notebook.add(self.session_start_tab, text="Start Session")
        notebook.add(self.session_end_tab, text="End Session")
        notebook.add(self.summary_tab, text="Today Summary")
        notebook.add(self.history_tab, text="History")

        # Detect any already-open session (CLI or previous GUI)
        try:
            latest_open = self.session_service.get_latest_open_session()
        except Exception:
            latest_open = None

        if latest_open is not None:
            self._on_session_started(latest_open.id)
            self.session_start_tab.show_existing_session(latest_open)

    # ------------------------------------------------------------------ #
    # Callbacks
    # ------------------------------------------------------------------ #

    def _on_session_started(self, session_id: int) -> None:
        """
        Called when a session is successfully started.
        """
        self._last_session_id = session_id
        self.session_end_tab.set_suggested_session_id(session_id)

    def _get_last_session_id(self) -> int | None:
        return self._last_session_id


# ---------------------------------------------------------------------------
# Sleep tab
# ---------------------------------------------------------------------------


class SleepTab(ttk.Frame):
    """
    Tab for logging sleep.
    Uses:
    - Sleep date (the morning date)
    - Sleep start: time + (previous day vs same day)
    - Sleep end: time (same day as sleep date)
    """

    def __init__(self, master: ttk.Notebook, app: AppContainer) -> None:
        super().__init__(master)
        self.app = app

        # Variables
        self.sleep_date_var = tk.StringVar(value=_today_str())

        self.start_prev_day_var = tk.BooleanVar(value=True)
        self.start_hour_var = tk.IntVar(value=23)
        self.start_min_var = tk.IntVar(value=0)

        self.end_hour_var = tk.IntVar(value=7)
        self.end_min_var = tk.IntVar(value=0)

        self.quality_var = tk.IntVar(value=3)
        self.awakenings_var = tk.IntVar(value=0)
        self.energy_var = tk.IntVar(value=5)
        self.mood_var = tk.IntVar(value=5)
        self.screen_last_hour_var = tk.BooleanVar(value=False)
        self.caffeine_after_17_var = tk.BooleanVar(value=False)
        self.bedtime_consistent_var = tk.BooleanVar(value=False)

        self._build_widgets()

    def _recent_dates(self, days: int = 7) -> list[str]:
        return [
            (date.today() - timedelta(days=i)).strftime(DATE_FORMAT)
            for i in range(days)
        ]

    def _build_widgets(self) -> None:
        pad = {"padx": 4, "pady": 3}

        form = ttk.Frame(self)
        form.pack(fill="both", expand=False, padx=10, pady=10)

        # Row 0 – Sleep date (morning date)
        ttk.Label(form, text="Sleep date (morning)").grid(
            row=0, column=0, sticky="w", **pad
        )
        date_combo = ttk.Combobox(
            form,
            textvariable=self.sleep_date_var,
            values=self._recent_dates(),
            width=12,
            state="readonly",
        )
        date_combo.grid(row=0, column=1, sticky="w", **pad)
        ttk.Label(form, text=f"Format: {DATE_FORMAT}").grid(
            row=0, column=2, sticky="w", **pad
        )

        # Row 1 – Sleep start time
        ttk.Label(form, text="Sleep start time").grid(
            row=1, column=0, sticky="w", **pad
        )
        ttk.Spinbox(
            form, from_=0, to=23, textvariable=self.start_hour_var, width=4
        ).grid(row=1, column=1, sticky="w", **pad)
        ttk.Label(form, text=":").grid(row=1, column=2, sticky="e", **pad)
        ttk.Spinbox(
            form, from_=0, to=55, increment=5, textvariable=self.start_min_var, width=4
        ).grid(row=1, column=3, sticky="w", **pad)

        ttk.Radiobutton(
            form,
            text="Previous day",
            variable=self.start_prev_day_var,
            value=True,
        ).grid(row=1, column=4, sticky="w", **pad)
        ttk.Radiobutton(
            form,
            text="Same day as sleep date",
            variable=self.start_prev_day_var,
            value=False,
        ).grid(row=1, column=5, sticky="w", **pad)

        # Row 2 – Sleep end time
        ttk.Label(form, text="Sleep end time (same day)").grid(
            row=2, column=0, sticky="w", **pad
        )
        ttk.Spinbox(
            form, from_=0, to=23, textvariable=self.end_hour_var, width=4
        ).grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(form, text=":").grid(row=2, column=2, sticky="e", **pad)
        ttk.Spinbox(
            form, from_=0, to=55, increment=5, textvariable=self.end_min_var, width=4
        ).grid(row=2, column=3, sticky="w", **pad)

        # Row 3 – Quality & awakenings
        ttk.Label(form, text="Sleep quality (1–5)").grid(
            row=3, column=0, sticky="w", **pad
        )
        ttk.Spinbox(
            form, from_=1, to=5, textvariable=self.quality_var, width=4
        ).grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(form, text="Awakenings").grid(row=3, column=2, sticky="w", **pad)
        ttk.Spinbox(
            form, from_=0, to=20, textvariable=self.awakenings_var, width=4
        ).grid(row=3, column=3, sticky="w", **pad)

        # Row 4 – Morning energy & mood
        ttk.Label(form, text="Energy morning (1–10)").grid(
            row=4, column=0, sticky="w", **pad
        )
        ttk.Spinbox(
            form, from_=1, to=10, textvariable=self.energy_var, width=4
        ).grid(row=4, column=1, sticky="w", **pad)

        ttk.Label(form, text="Mood morning (1–10)").grid(
            row=4, column=2, sticky="w", **pad
        )
        ttk.Spinbox(
            form, from_=1, to=10, textvariable=self.mood_var, width=4
        ).grid(row=4, column=3, sticky="w", **pad)

        # Flags
        flags_frame = ttk.Frame(self)
        flags_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Checkbutton(
            flags_frame,
            text="Screen in last hour before sleep",
            variable=self.screen_last_hour_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            flags_frame,
            text="Caffeine after 17:00",
            variable=self.caffeine_after_17_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            flags_frame,
            text="Bedtime consistent (±30 min)",
            variable=self.bedtime_consistent_var,
        ).pack(anchor="w")

        # Submit
        ttk.Button(self, text="Save Sleep", command=self._on_save).pack(
            padx=10, pady=10, anchor="e"
        )

    def _on_save(self) -> None:
        try:
            sleep_day = _parse_date(self.sleep_date_var.get().strip())

            # Compute start/end datetimes
            if self.start_prev_day_var.get():
                start_date = sleep_day - timedelta(days=1)
            else:
                start_date = sleep_day

            start_dt = datetime.combine(
                start_date,
                time(
                    hour=int(self.start_hour_var.get()),
                    minute=int(self.start_min_var.get()),
                ),
            )
            end_dt = datetime.combine(
                sleep_day,
                time(
                    hour=int(self.end_hour_var.get()),
                    minute=int(self.end_min_var.get()),
                ),
            )

            sleep_input = SleepInput(
                date=sleep_day,
                sleep_start=start_dt,
                sleep_end=end_dt,
                sleep_quality=int(self.quality_var.get()),
                awakenings_count=int(self.awakenings_var.get()),
                energy_morning=int(self.energy_var.get()),
                mood_morning=int(self.mood_var.get()),
                screen_last_hour=bool(self.screen_last_hour_var.get()),
                caffeine_after_17=bool(self.caffeine_after_17_var.get()),
                bedtime_consistent=bool(self.bedtime_consistent_var.get()),
            )

            sleep = self.app.sleep_service.log_sleep(sleep_input)
        except SleepValidationError as e:
            messagebox.showerror("Sleep validation error", str(e), parent=self)
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save sleep:\n{e}", parent=self)
            return

        messagebox.showinfo(
            "Sleep saved",
            f"Date: {sleep.date.isoformat()}\n"
            f"Duration (min): {sleep.duration_minutes()}\n"
            f"Quality: {sleep.sleep_quality}",
            parent=self,
        )


# ---------------------------------------------------------------------------
# Session start tab
# ---------------------------------------------------------------------------


class SessionStartTab(ttk.Frame):
    """
    Tab for starting a new session.
    """

    def __init__(
        self,
        master: ttk.Notebook,
        app: AppContainer,
        on_session_started,
    ) -> None:
        super().__init__(master)
        self.app = app
        self._on_session_started = on_session_started

        # Variables
        self.domain_var = tk.StringVar(value=Domain.WORK.value)
        self.project_var = tk.StringVar(value="")
        self.activity_var = tk.StringVar(value="")
        self.work_type_var = tk.StringVar(value=WorkType.DEEP.value)
        self.planned_duration_var = tk.StringVar(value="")

        self.energy_before_var = tk.IntVar(value=6)
        self.stress_before_var = tk.IntVar(value=4)
        self.resistance_before_var = tk.IntVar(value=2)

        self.last_session_label_var = tk.StringVar(
            value="No session started yet in this app."
        )

        self._build_widgets()

    def _build_widgets(self) -> None:
        pad = {"padx": 4, "pady": 3}

        form = ttk.Frame(self)
        form.pack(fill="x", padx=10, pady=10)

        # Row 0 – Domain
        ttk.Label(form, text="Domain").grid(row=0, column=0, sticky="w", **pad)
        domain_combo = ttk.Combobox(
            form,
            textvariable=self.domain_var,
            values=[d.value for d in Domain],
            state="readonly",
            width=20,
        )
        domain_combo.grid(row=0, column=1, sticky="w", **pad)

        # Row 1 – Project
        ttk.Label(form, text="Project").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(form, textvariable=self.project_var, width=40).grid(
            row=1, column=1, columnspan=3, sticky="w", **pad
        )

        # Row 2 – Activity
        ttk.Label(form, text="Activity").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(form, textvariable=self.activity_var, width=60).grid(
            row=2, column=1, columnspan=3, sticky="w", **pad
        )

        # Row 3 – Work type + planned duration
        ttk.Label(form, text="Work type").grid(row=3, column=0, sticky="w", **pad)
        work_type_combo = ttk.Combobox(
            form,
            textvariable=self.work_type_var,
            values=[w.value for w in WorkType],
            state="readonly",
            width=20,
        )
        work_type_combo.grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(form, text="Planned duration (min)").grid(
            row=3, column=2, sticky="w", **pad
        )
        ttk.Entry(form, textvariable=self.planned_duration_var, width=8).grid(
            row=3, column=3, sticky="w", **pad
        )

        # Row 4 – Before-state
        ttk.Label(form, text="Energy before (1–10)").grid(
            row=4, column=0, sticky="w", **pad
        )
        ttk.Spinbox(
            form, from_=1, to=10, textvariable=self.energy_before_var, width=4
        ).grid(row=4, column=1, sticky="w", **pad)

        ttk.Label(form, text="Stress before (1–10)").grid(
            row=4, column=2, sticky="w", **pad
        )
        ttk.Spinbox(
            form, from_=1, to=10, textvariable=self.stress_before_var, width=4
        ).grid(row=4, column=3, sticky="w", **pad)

        ttk.Label(form, text="Resistance (1–5)").grid(
            row=5, column=0, sticky="w", **pad
        )
        ttk.Spinbox(
            form, from_=1, to=5, textvariable=self.resistance_before_var, width=4
        ).grid(row=5, column=1, sticky="w", **pad)

        # Start button
        ttk.Button(self, text="Start Session", command=self._on_start).pack(
            padx=10, pady=10, anchor="e"
        )

        # Last/active session info
        ttk.Label(self, textvariable=self.last_session_label_var).pack(
            padx=10, pady=(0, 10), anchor="w"
        )

    def show_existing_session(self, session: PerformanceSession) -> None:
        """
        Called on startup if an active session already exists (e.g. from CLI).
        """
        self.last_session_label_var.set(
            f"Active session detected: id={session.id}, "
            f"{session.context.domain.value} / {session.context.project_name} "
            f"started at {session.start_time}"
        )

    def _on_start(self) -> None:
        try:
            domain = Domain(self.domain_var.get())
            work_type = WorkType(self.work_type_var.get())

            planned_duration_str = self.planned_duration_var.get().strip()
            planned_duration = (
                int(planned_duration_str) if planned_duration_str else None
            )

            start_input = StartSessionInput(
                domain=domain,
                project_name=self.project_var.get().strip(),
                activity_description=self.activity_var.get().strip(),
                work_type=work_type,
                planned_duration_min=planned_duration,
                energy_before=int(self.energy_before_var.get()),
                stress_before=int(self.stress_before_var.get()),
                resistance_before=int(self.resistance_before_var.get()),
            )

            session = self.app.session_service.start_session(start_input)

        except (SessionValidationError, ValueError) as e:
            messagebox.showerror("Session start error", str(e), parent=self)
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start session:\n{e}", parent=self)
            return

        self.last_session_label_var.set(
            f"Last session started here: id={session.id}, "
            f"{session.context.domain.value} / {session.context.project_name} "
            f"at {session.start_time}"
        )
        messagebox.showinfo(
            "Session started",
            f"Session id: {session.id}\n"
            f"Domain: {session.context.domain.value}\n"
            f"Project: {session.context.project_name}",
            parent=self,
        )

        if self._on_session_started is not None:
            self._on_session_started(session.id)


# ---------------------------------------------------------------------------
# Session end tab
# ---------------------------------------------------------------------------


class SessionEndTab(ttk.Frame):
    """
    Tab for ending the active session.

    This does not require manual entering of session id. It uses:
    - the last session started in this app, or
    - the latest open session found via the service (CLI or GUI).
    """

    def __init__(
        self,
        master: ttk.Notebook,
        app: AppContainer,
        get_last_session_id,
    ) -> None:
        super().__init__(master)
        self.app = app
        self._get_last_session_id = get_last_session_id

        self._active_session_id: int | None = None
        self.session_id_label_var = tk.StringVar(
            value="No active session detected yet."
        )

        # Variables
        self.completion_status_var = tk.StringVar(
            value=CompletionStatus.COMPLETED.value
        )
        self.progress_rating_var = tk.IntVar(value=3)
        self.quality_rating_var = tk.IntVar(value=3)
        self.focus_quality_var = tk.IntVar(value=3)
        self.moves_main_goal_var = tk.BooleanVar(value=True)
        self.evidence_note_var = tk.StringVar(value="")
        self.energy_after_var = tk.IntVar(value=5)
        self.stress_after_var = tk.IntVar(value=5)
        self.feel_tag_var = tk.StringVar(value=FEEL_TAG_OPTIONS[0])

        self._build_widgets()

    def set_suggested_session_id(self, session_id: int) -> None:
        """
        Allow the main window to set the active session id.
        """
        self._active_session_id = session_id
        self.session_id_label_var.set(f"Active session id: {session_id}")

    def _build_widgets(self) -> None:
        pad = {"padx": 4, "pady": 3}

        form = ttk.Frame(self)
        form.pack(fill="x", padx=10, pady=10)

        # Row 0 – Active session info (no manual input)
        ttk.Label(form, text="Active session").grid(row=0, column=0, sticky="w", **pad)
        ttk.Label(form, textvariable=self.session_id_label_var).grid(
            row=0, column=1, columnspan=3, sticky="w", **pad
        )

        # Row 1 – Completion status
        ttk.Label(form, text="Completion status").grid(
            row=1, column=0, sticky="w", **pad
        )
        completion_combo = ttk.Combobox(
            form,
            textvariable=self.completion_status_var,
            values=[c.value for c in CompletionStatus],
            state="readonly",
            width=20,
        )
        completion_combo.grid(row=1, column=1, sticky="w", **pad)

        # Row 2 – Progress / Quality / Focus (radio buttons 1–5)
        ttk.Label(form, text="Progress (1–5)").grid(
            row=2, column=0, sticky="w", **pad
        )
        prog_frame = make_1to5_radios(form, self.progress_rating_var)
        prog_frame.grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(form, text="Quality (1–5)").grid(
            row=2, column=2, sticky="w", **pad
        )
        qual_frame = make_1to5_radios(form, self.quality_rating_var)
        qual_frame.grid(row=2, column=3, sticky="w", **pad)

        ttk.Label(form, text="Focus (1–5)").grid(row=3, column=0, sticky="w", **pad)
        focus_frame = make_1to5_radios(form, self.focus_quality_var)
        focus_frame.grid(row=3, column=1, sticky="w", **pad)

        # Row 4 – Moves main goal + evidence
        ttk.Checkbutton(
            form,
            text="Moves main goal",
            variable=self.moves_main_goal_var,
        ).grid(row=4, column=0, sticky="w", **pad)

        ttk.Label(form, text="Evidence note").grid(
            row=4, column=2, sticky="w", **pad
        )
        ttk.Entry(form, textvariable=self.evidence_note_var, width=30).grid(
            row=4, column=3, sticky="w", **pad
        )

        # Row 5 – After-state
        ttk.Label(form, text="Energy after (1–10)").grid(
            row=5, column=0, sticky="w", **pad
        )
        ttk.Spinbox(
            form, from_=1, to=10, textvariable=self.energy_after_var, width=4
        ).grid(row=5, column=1, sticky="w", **pad)

        ttk.Label(form, text="Stress after (1–10)").grid(
            row=5, column=2, sticky="w", **pad
        )
        stress_frame = make_1to10_radios(form, self.stress_after_var)
        stress_frame.grid(row=5, column=3, sticky="w", **pad)

        # Row 6 – Feel tag
        ttk.Label(form, text="Feel tag").grid(row=6, column=0, sticky="w", **pad)
        feel_combo = ttk.Combobox(
            form,
            textvariable=self.feel_tag_var,
            values=FEEL_TAG_OPTIONS,
            state="readonly",
            width=15,
        )
        feel_combo.grid(row=6, column=1, sticky="w", **pad)

        # Button
        ttk.Button(self, text="End Session", command=self._on_end).pack(
            padx=10, pady=10, anchor="e"
        )

    def _resolve_session_id(self) -> int | None:
        """
        Resolve which session id to end:
        - prefer explicit active_session_id set by main window
        - fall back to last_session_id known by main window
        """
        if self._active_session_id is not None:
            return self._active_session_id
        return self._get_last_session_id()

    def _on_end(self) -> None:
        session_id = self._resolve_session_id()
        if session_id is None:
            messagebox.showerror(
                "No active session",
                "No active session found. Start a session first (CLI or GUI).",
                parent=self,
            )
            return

        try:
            completion_status = CompletionStatus(self.completion_status_var.get())

            end_input = EndSessionInput(
                completion_status=completion_status,
                progress_rating=int(self.progress_rating_var.get()),
                quality_rating=int(self.quality_rating_var.get()),
                focus_quality=int(self.focus_quality_var.get()),
                moves_main_goal=bool(self.moves_main_goal_var.get()),
                evidence_note=self.evidence_note_var.get().strip() or None,
                energy_after=int(self.energy_after_var.get()),
                stress_after=int(self.stress_after_var.get()),
                feel_tag=self.feel_tag_var.get().strip(),
            )

            session = self.app.session_service.end_session(session_id, end_input)

        except SessionNotFoundError as e:
            messagebox.showerror("Session not found", str(e), parent=self)
            return
        except (SessionValidationError, ValueError) as e:
            messagebox.showerror("Session end error", str(e), parent=self)
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to end session:\n{e}", parent=self)
            return

        messagebox.showinfo(
            "Session ended",
            f"Session id: {session.id}\n"
            f"Duration (min): {session.duration_minutes}\n"
            f"Progress: {session.outcome.progress_rating}\n"
            f"Quality:  {session.outcome.quality_rating}\n"
            f"Focus:    {session.outcome.focus_quality}",
            parent=self,
        )


# ---------------------------------------------------------------------------
# Today summary tab
# ---------------------------------------------------------------------------


class TodaySummaryTab(ttk.Frame):
    """
    Tab showing today's summary, similar to the CLI day-summary.
    """

    def __init__(self, master: ttk.Notebook, app: AppContainer) -> None:
        super().__init__(master)
        self.app = app

        self._build_widgets()
        self.refresh()

    def _build_widgets(self) -> None:
        # Refresh button
        ttk.Button(self, text="Refresh", command=self.refresh).pack(
            padx=10, pady=5, anchor="e"
        )

        # Text area
        self.text = tk.Text(self, height=25, wrap="word")
        self.text.pack(fill="both", expand=True, padx=10, pady=5)
        self.text.configure(state="disabled")

    def refresh(self) -> None:
        try:
            day = date.today()
            summary = self.app.day_service.build_day_summary(day)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load summary:\n{e}", parent=self)
            return

        text_content = format_day_summary(summary)

        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text_content)
        self.text.configure(state="disabled")


# ---------------------------------------------------------------------------
# History tab
# ---------------------------------------------------------------------------


class HistoryTab(ttk.Frame):
    """
    Tab for browsing summaries of past days.

    - You can input a date.
    - Use ◀ / ▶ to step one day back/forward.
    - "Today" button jumps to today.
    """

    def __init__(self, master: ttk.Notebook, app: AppContainer) -> None:
        super().__init__(master)
        self.app = app

        self.date_var = tk.StringVar(value=_today_str())

        self._build_widgets()
        self._load()

    def _build_widgets(self) -> None:
        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=10, pady=5)

        ttk.Label(controls, text="Date").pack(side="left")
        ttk.Entry(controls, textvariable=self.date_var, width=12).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="◀", command=lambda: self._shift_day(-1)).pack(
            side="left", padx=2
        )
        ttk.Button(controls, text="▶", command=lambda: self._shift_day(1)).pack(
            side="left", padx=2
        )
        ttk.Button(controls, text="Go", command=self._load).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="Today", command=self._go_today).pack(
            side="left", padx=4
        )

        self.text = tk.Text(self, height=25, wrap="word")
        self.text.pack(fill="both", expand=True, padx=10, pady=5)
        self.text.configure(state="disabled")

    def _shift_day(self, delta_days: int) -> None:
        try:
            current = _parse_date(self.date_var.get().strip())
        except Exception:
            current = date.today()
        new_day = current + timedelta(days=delta_days)
        self.date_var.set(new_day.strftime(DATE_FORMAT))
        self._load()

    def _go_today(self) -> None:
        self.date_var.set(_today_str())
        self._load()

    def _load(self) -> None:
        try:
            day = _parse_date(self.date_var.get().strip())
            summary = self.app.day_service.build_day_summary(day)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load summary:\n{e}", parent=self)
            return

        text_content = format_day_summary(summary)

        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text_content)
        self.text.configure(state="disabled")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    app_container = create_app()
    root = tk.Tk()

    main_window = MainWindow(root, app_container)

    def on_close() -> None:
        try:
            app_container.close()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
