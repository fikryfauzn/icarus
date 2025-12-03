# Icarus - Personal Performance OS

![Icarus Logo](https://img.shields.io/badge/Icarus-Personal%20Performance%20OS-blue)
![Python](https://img.shields.io/badge/Python-3.13+-green)
![Svelte](https://img.shields.io/badge/Svelte-5-orange)
![Flask](https://img.shields.io/badge/Flask-API-lightgrey)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue)

A comprehensive personal performance tracking system with multiple interface options, built on clean architecture principles. Track sleep, work sessions, tasks, and daily analytics with a sophisticated rating system.

## Features

### Multi-Interface Support
- **Web Interface**: Modern Svelte 5 frontend with real-time analytics
- **Desktop GUI**: Tkinter application for local desktop use
- **CLI**: Command-line interface for quick operations and scripting
- **REST API**: Headless mode for integration with other tools

### Comprehensive Tracking
- **Sleep Patterns**: Track sleep duration, quality, and patterns
- **Work Sessions**: Log focused work sessions with detailed ratings
- **Task Management**: Organize and track tasks with priority levels
- **Daily Analytics**: Automatic daily summaries and insights
- **Biological State**: Monitor energy, stress, and focus levels

### Sophisticated Rating System
- **Progress Rating**: Track completion and advancement
- **Quality Rating**: Assess work output quality
- **Focus Rating**: Measure concentration and distraction levels
- **Energy/Stress Levels**: Monitor physical and mental state

## Architecture

Icarus follows clean architecture principles with clear separation of concerns:

```
icarus/
├── core/           # Domain models and business logic
├── services/       # Business logic services
├── storage/        # Data persistence layer (SQLite)
├── api/           # Flask REST API
├── ui/            # Tkinter desktop GUI
├── cli/           # Command-line interface
└── client/        # Svelte web frontend
```

### Technology Stack
- **Backend**: Python 3.13 + Flask + SQLite
- **Frontend**: Svelte 5 + Vite + TailwindCSS
- **Desktop**: Tkinter (Python native GUI)
- **Database**: SQLite (local file storage)
- **Architecture**: Clean Architecture + Repository Pattern

## Installation

### Prerequisites
- Python 3.13 or higher
- Node.js 18+ (for web frontend)
- SQLite3

### Backend Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/icarus.git
cd icarus

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Initialize database
python -c "from app_bootstrap import bootstrap; bootstrap()"
```

### Frontend Setup
```bash
cd client
npm install
```

## Usage

### Web Interface (Recommended)
```bash
# Terminal 1: Start Flask API
cd icarus
source .venv/bin/activate
python -m api.app

# Terminal 2: Start Svelte frontend
cd icarus/client
npm run dev
```
Access at: http://localhost:5173

### Desktop GUI
```bash
cd icarus
source .venv/bin/activate
python -m ui.app
```

### CLI Interface
```bash
cd icarus
source .venv/bin/activate
python -m cli.main --help
```

### Headless Mode (Python Library)
```python
from app_bootstrap import bootstrap
from services.session_service import SessionService

# Bootstrap application
app_context = bootstrap()

# Use services
session_service = SessionService()
sessions = session_service.get_today_sessions()
```

## Data Model

Icarus tracks:
- **Sleep**: Duration, quality, wake-up time, notes
- **Work Sessions**: Start/end time, work type, ratings
- **Tasks**: Description, priority, status, due dates
- **Daily Summaries**: Automatic aggregation of daily metrics
- **Ratings**: Multi-dimensional assessment system

## Rating System

Detailed in `docs/RATING_GUIDE.md`, the rating system includes:
- **Progress (0-10)**: Task completion and advancement
- **Quality (0-10)**: Output excellence and craftsmanship
- **Focus (0-10)**: Concentration level and distraction management
- **Energy/Stress (-5 to +5)**: Physical and mental state

## Development

### Project Structure
```
icarus/
├── core/           # Domain entities and value objects
│   ├── models.py   # Data models (Sleep, Session, Task, Day)
│   └── enums.py    # Enumerations (WorkType, TaskStatus, etc.)
├── services/       # Business logic
│   ├── session_service.py
│   ├── sleep_service.py
│   ├── task_service.py
│   └── analytics_service.py
├── storage/        # Data persistence
│   ├── base.py     # Base repository interface
│   └── sqlite_*.py # SQLite implementations
├── api/           # REST API (Flask)
├── ui/            # Desktop GUI (Tkinter)
├── cli/           # Command-line interface
└── client/        # Web frontend (Svelte)
```

### Running Tests
```bash
# Run Python tests
pytest

# Run frontend tests
cd client
npm test
```

### Code Quality
```bash
# Format Python code
black .
isort .

# Lint Python code
flake8
mypy .

# Format frontend code
cd client
npm run format
```

## Roadmap

### Short-term
- [ ] Mobile-responsive web interface
- [ ] Data export/import functionality
- [ ] Advanced analytics and visualization
- [ ] Notification system

### Long-term
- [ ] Mobile app (React Native)
- [ ] Machine learning insights
- [ ] Integration with health APIs (Apple Health, Google Fit)
- [ ] Team/group tracking features

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please read `CONTRIBUTING.md` for detailed guidelines.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgments

- Clean Architecture inspiration from Robert C. Martin
- Svelte community for the amazing frontend framework
- Python ecosystem for robust backend development

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the documentation in `docs/`
- Review the `CLAUDE.md` for project context

---

**Icarus** - Soar higher with data-driven self-improvement. 🦅