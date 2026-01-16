# Myome

```
                                                    
  ███╗   ███╗██╗   ██╗ ██████╗ ███╗   ███╗███████╗  
  ████╗ ████║╚██╗ ██╔╝██╔═══██╗████╗ ████║██╔════╝  
  ██╔████╔██║ ╚████╔╝ ██║   ██║██╔████╔██║█████╗    
  ██║╚██╔╝██║  ╚██╔╝  ██║   ██║██║╚██╔╝██║██╔══╝    
  ██║ ╚═╝ ██║   ██║   ╚██████╔╝██║ ╚═╝ ██║███████╗  
  ╚═╝     ╚═╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝╚══════╝  
                                                    
        Your Living Health Record Framework         
```

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)

## Overview

Myome is an open-source framework for building comprehensive, longitudinal health records that span an entire lifetime—and beyond. Unlike traditional electronic health records that capture episodic snapshots, Myome creates a **living health record** that continuously integrates data from wearables, clinical systems, environmental sensors, and genomic sources into a unified, actionable health profile.

### Key Features

- **Multi-Ome Integration** — Unify data across physiome, genome, microbiome, metabolome, exposome, anatome, and epigenome domains
- **Real-Time Sensor Fusion** — Connect wearables (Oura, Apple Watch, Garmin) and CGMs (Dexcom, Libre) with automatic calibration
- **Intelligent Analytics** — Discover cross-biomarker correlations, detect anomalies, and generate predictive health insights
- **Clinical Integration** — Export FHIR-compliant resources and generate physician-ready reports
- **Hereditary Artifacts** — Securely preserve and transfer health wisdom across generations
- **Privacy-First Architecture** — Your data stays yours with end-to-end encryption and local-first storage options

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Web Dashboard │  │  Mobile Apps  │  │  CLI Tools   │           │
│  │  (React/Vite) │  │(React Native)│  │   (Python)   │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    FastAPI + REST                         │   │
│  │         Authentication · Rate Limiting · Validation       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Sensor Layer   │ │ Analytics Engine│ │ Clinical Module │
│                 │ │                 │ │                 │
│ • Oura Ring     │ │ • Correlations  │ │ • FHIR Export   │
│ • Apple Health  │ │ • Trend Analysis│ │ • Lab Reports   │
│ • Dexcom CGM    │ │ • Anomaly Detect│ │ • Physician View│
│ • Withings      │ │ • Predictions   │ │ • Care Plans    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Storage Layer                              │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   TimescaleDB    │  │    Redis     │  │ Object Store │       │
│  │  (Time-Series)   │  │   (Cache)    │  │   (Blobs)    │       │
│  └──────────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ with TimescaleDB (provided via Docker)

### Installation

```bash
# Clone the repository
git clone https://github.com/joescanlin/myome-OS.git
cd myome-OS

# Run the setup script
./scripts/setup.sh

# Or set up manually:

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd ../frontend
npm install

# Start infrastructure
cd ..
docker-compose up -d db redis
```

### Running the Application

**Development Mode:**

```bash
# Terminal 1: Start the API
cd backend
source .venv/bin/activate
uvicorn myome.api.main:app --reload

# Terminal 2: Start the frontend
cd frontend
npm run dev
```

**Docker Compose (All Services):**

```bash
docker-compose up
```

Access the application:
- **Web Dashboard:** http://localhost:3000
- **API Documentation:** http://localhost:8000/docs
- **API Health Check:** http://localhost:8000/health

## Project Structure

```
myome/
├── backend/                 # Python FastAPI backend
│   ├── myome/
│   │   ├── api/            # REST API endpoints
│   │   ├── core/           # Configuration, models, utilities
│   │   ├── sensors/        # Device adapters and data ingestion
│   │   ├── analytics/      # Correlation engine and predictions
│   │   ├── clinical/       # FHIR export and clinical reports
│   │   └── hereditary/     # Multi-generational health artifacts
│   ├── tests/              # Test suite
│   └── migrations/         # Database migrations (Alembic)
├── frontend/               # React TypeScript frontend
│   └── src/
│       ├── components/     # Reusable UI components
│       ├── pages/          # Route pages
│       ├── hooks/          # Custom React hooks
│       ├── services/       # API client services
│       └── store/          # State management (Zustand)
├── mobile/                 # React Native mobile apps
├── docker/                 # Dockerfiles
├── scripts/                # Development and deployment scripts
└── docker-compose.yml      # Local development environment
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0, Celery |
| **Database** | PostgreSQL 15 + TimescaleDB |
| **Cache** | Redis 7 |
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS |
| **State** | TanStack Query, Zustand |
| **Charts** | Recharts, D3.js |
| **Mobile** | React Native, Expo |
| **Analytics** | NumPy, SciPy, Pandas, scikit-learn, XGBoost |

## Configuration

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql+asyncpg://myome:myome@localhost:5432/myome

# Redis
REDIS_URL=redis://localhost:6379/0

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here

# Environment
ENVIRONMENT=development
DEBUG=true
```

## Running Tests

```bash
# Backend tests
cd backend
source .venv/bin/activate
pytest tests/ -v --cov=myome

# Frontend tests
cd frontend
npm test
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/auth/login` | POST | User authentication |
| `/api/v1/users/me` | GET | Current user profile |
| `/api/v1/health/heart-rate` | GET/POST | Heart rate data |
| `/api/v1/health/sleep` | GET/POST | Sleep data |
| `/api/v1/health/analytics/score` | GET | Composite health score |
| `/api/v1/health/analytics/correlations` | GET | Cross-biomarker correlations |
| `/api/v1/alerts` | GET | Active health alerts |
| `/api/v1/clinical/fhir/export` | GET | FHIR resource export |

Full API documentation available at `/docs` when running the server.

## The Seven Omes

Myome integrates health data across seven interconnected domains:

| Ome | Description | Example Data |
|-----|-------------|--------------|
| **Physiome** | Real-time physiological measurements | Heart rate, HRV, blood pressure, SpO2 |
| **Genome** | Genetic variants and predispositions | SNPs, polygenic risk scores |
| **Microbiome** | Gut and skin microbiota composition | Bacterial diversity, enterotypes |
| **Metabolome** | Metabolic markers and processes | Glucose, lipids, hormones |
| **Exposome** | Environmental exposures | Air quality, UV, noise, location |
| **Anatome** | Structural and imaging data | Body composition, medical imaging |
| **Epigenome** | Gene expression modifications | DNA methylation, biological age |

## Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code (enforced via `ruff` and `black`)
- Use TypeScript strict mode for frontend code
- Write tests for new features
- Update documentation as needed

## Roadmap

- [ ] Core data models and storage layer
- [ ] Sensor adapters (Oura, Apple Health, Dexcom)
- [ ] Analytics engine with correlation detection
- [ ] REST API with authentication
- [ ] Web dashboard with visualizations
- [ ] FHIR clinical export
- [ ] Hereditary artifact system
- [ ] Mobile applications (iOS/Android)
- [ ] Advanced ML predictions
- [ ] Multi-user family networks

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- The quantified self and personal health data communities
- Open-source health data standards (FHIR, HL7)
- All contributors and early adopters

---

<p align="center">
  <strong>Your health story, written in data, preserved for generations.</strong>
</p>
