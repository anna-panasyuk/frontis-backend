# FRONT.IN - backend (PostgreSQL + FastAPI)

## Struktura
- `init.sql` - pełny schemat bazy (PostgreSQL 17.5)
- `migrations/001_init.up.sql` - migracja UP
- `migrations/001_init.down.sql` - migracja DOWN
- `scripts/run_migrations.sh` - uruchamianie migracji
- `scripts/rollback_last.sh` - rollback pierwszej migracji
- `docker-compose.yml` - uruchomienie DB + API
- `api/` - FastAPI (CRUD + endpoint PCM)
- `.env.example` - przykładowa konfiguracja środowiska

## Szybki start (lokalnie)

```bash
cd "/Users/annapanasyuk/Documents/frontis-backend/baza_danych"
cp .env.example .env
docker compose up --build -d
```

Sprawdzenie:

```bash
docker compose ps
curl http://localhost:8000/health
docker compose exec db psql -U frontin -d frontin -c "\dt"
```

Zatrzymanie:

```bash
docker compose down
```

Zatrzymanie i usunięcie danych bazy:

```bash
docker compose down -v
```

## Szybki start dla zespołu (README dla kolegi)

1. Sklonuj repozytorium:

```bash
git clone <URL_REPO>
cd frontis-backend/baza_danych
```

2. Skopiuj konfigurację i uruchom:

```bash
cp .env.example .env
docker compose up --build -d
```

3. Sprawdź, czy działa:

```bash
curl http://localhost:8000/health
docker compose exec db psql -U frontin -d frontin -c "\dt"
```

4. Jeśli port `5432` jest zajęty, zmień port bazy w `.env`:

```env
DB_PORT=5433
```

Potem uruchom ponownie:

```bash
docker compose down
docker compose up --build -d
```

5. Parametry połączenia do DB z hosta:
- Host: `localhost`
- Port: `DB_PORT` z `.env` (np. `5433`)
- Database: `frontin`
- User: `frontin`
- Password: `frontin_pass`

## Typowy błąd: ORA-12541 (No listener na 1521)

Ten błąd dotyczy Oracle, nie PostgreSQL. Oznacza, że klient próbuje łączyć się z Oracle (`1521`) zamiast z PostgreSQL.

Poprawny connection string:

```txt
postgresql://frontin:frontin_pass@localhost:<DB_PORT>/frontin
```
