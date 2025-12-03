# Icarus - Personal Performance OS

## Project Overview
A personal performance tracking system with multiple interface options (web, desktop GUI, CLI) built on a clean architecture.

## Technology Stack
- **Backend**: Python 3.13 + Flask (API) + Tkinter (GUI)
- **Frontend**: Svelte 5 + Vite + TailwindCSS
- **Database**: SQLite (local file storage)
- **Architecture**: Clean architecture with clear separation of concerns

## Directory Structure

```
icarus/
├── api/                    # Flask REST API (headless mode)
├── client/                 # Svelte frontend (modern web UI)
├── cli/                    # Command-line interface
├── config/                 # Configuration settings
├── core/                   # Domain models and business logic
├── docs/                   # Documentation (including RATING_GUIDE.md)
├── services/               # Business logic services
├── storage/                # Data persistence layer (SQLite implementations)
├── ui/                     # Tkinter desktop GUI
├── data/                   # SQLite database files
├── .venv/                  # Python virtual environment
├── app_bootstrap.py        # Application composition root
└── __init__.py             # Package initialization
```

## Key Features
1. **Multiple Interfaces**: REST API, Tkinter GUI, CLI, and web frontend
2. **Comprehensive Tracking**: Sleep, work sessions, tasks, daily analytics
3. **Detailed Rating System**: Progress, quality, focus, energy/stress levels
4. **Clean Architecture**: Core domain, services, storage, and UI layers separated
5. **Local-First**: SQLite database for privacy and offline use

## Development Setup
- **Backend**: Python virtual environment with SQLite database
- **Frontend**: Svelte/Vite development server (port 5173)
- **API**: Flask server (port 5000)
- **Database**: SQLite file at `data/icarus.db`

## Usage Options
1. **Web Interface**: Run Flask API + Svelte frontend
2. **Desktop GUI**: Tkinter application
3. **CLI**: Command-line interface for quick operations
4. **Headless**: Import as Python library for scripting

## Domain Model
Tracks sleep patterns, work sessions with detailed ratings, daily summaries, and task management using a comprehensive rating system documented in `docs/RATING_GUIDE.md`.

## Project Status
Active development with well-structured codebase following software engineering best practices.