# FRONT.IN Backend

Backend system for managing interviews and safeguarding of unaccompanied minor migrants at border points. Supports child profile management, structured interviews, AI-assisted language detection from audio, and a full audit trail.

## Tech Stack

| Layer | Technology |
|---|---|
| API | Python 3.12, FastAPI 0.116, Uvicorn |
| Database | PostgreSQL 17.5 |
| Audio / NLP | faster-whisper (Whisper model via CTranslate2) |
| ORM / DB driver | psycopg3 |
| Validation | Pydantic v2 |
| Containerization | Docker, Docker Compose |

## How to Run Locally

**Prerequisites:** Docker and Docker Compose installed.

1. Copy the example env file and fill in values:
   ```bash
   cp .env.example .env
   ```

   Minimum required variables:
   ```
   POSTGRES_DB=frontin
   POSTGRES_USER=frontin
   POSTGRES_PASSWORD=frontin_pass
   DB_PORT=5432
   API_PORT=8000
   WHISPER_MODEL_SIZE=base
   WHISPER_COMPUTE_TYPE=int8
   ```

2. Start all services:
   ```bash
   cd baza_danych
   docker compose up --build
   ```

   The API will be available at `http://localhost:8000`.
   Interactive docs: `http://localhost:8000/docs`

3. To stop:
   ```bash
   docker compose down
   ```

### Running Migrations Manually

```bash
cd baza_danych
bash scripts/run_migrations.sh
# rollback:
bash scripts/rollback_last.sh
```

## Project Structure

```
frontis-backend-main/
└── baza_danych/
    ├── api/
    │   ├── app/
    │   │   └── main.py          # FastAPI app — all routes and models
    │   ├── Dockerfile
    │   └── requirements.txt
    ├── migrations/
    │   ├── 001_init.up.sql      # Schema creation
    │   └── 001_init.down.sql    # Schema rollback
    ├── scripts/
    │   ├── run_migrations.sh
    │   └── rollback_last.sh
    ├── init.sql                 # Auto-applied on first DB container start
    └── docker-compose.yml
```

## Database Schema

| Table | Purpose |
|---|---|
| `child_profiles` | Core record per child (case code, age, origin, language) |
| `interviews` | Interview sessions linked to a child profile |
| `interview_statements` | Q&A pairs recorded during an interview |
| `safeguarding_flags` | Risk flags (trafficking, medical, distress, etc.) |
| `protection_cases` | Legal status tracking per child |
| `audio_inputs` | Raw audio metadata (PCM, 16 kHz mono) |
| `language_detections` | Whisper language detection results |
| `audit_logs` | Immutable action log for all entities |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/child-profiles` | Create a child profile |
| `GET` | `/child-profiles/{id}` | Get a child profile by ID |
| `POST` | `/interviews` | Create an interview session |
| `POST` | `/interviews/{id}/statements` | Add a Q&A statement to an interview |
| `GET` | `/interviews/{id}/statements` | List all statements for an interview |
| `POST` | `/language/detect-audio` | Detect spoken language from raw PCM audio |

### Audio Detection Headers

`POST /language/detect-audio` expects raw PCM bytes in the body and these headers:

```
X-Audio-Format: pcm_s16le
X-Sample-Rate: 16000
X-Channels: 1
X-Interview-Id: <uuid>
X-Actor-Id: <actor string>   # optional, defaults to "system"
```
