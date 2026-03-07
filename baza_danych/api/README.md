# API (FastAPI) - FRONT.IN

## 1) Install

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Run

```bash
export DATABASE_URL='postgresql://frontin:frontin_pass@localhost:5432/frontin'
uvicorn app.main:app --reload --port 8000
```

## 3) CRUD flow demo

### Create child profile

```bash
curl -X POST "http://127.0.0.1:8000/child-profiles" \
  -H "Content-Type: application/json" \
  -d '{
    "caseCode":"FRONTIN-2026-0001",
    "declaredAge":13,
    "unaccompaniedMinor":true,
    "countryOfOrigin":"SY",
    "primaryLanguage":"ar",
    "secondaryLanguages":["ku"]
  }'
```

### Create interview

```bash
curl -X POST "http://127.0.0.1:8000/interviews" \
  -H "Content-Type: application/json" \
  -d '{
    "childProfileId":"<UUID_CHILD_PROFILE>",
    "interviewType":"rozpytanie_graniczne",
    "borderPointCode":"PL-BY-001",
    "officerId":"OFFICER-001",
    "interpreterMode":"ai"
  }'
```

### Add statement

```bash
curl -X POST "http://127.0.0.1:8000/interviews/<UUID_INTERVIEW>/statements" \
  -H "Content-Type: application/json" \
  -d '{
    "stepCode":"identity.family",
    "questionText":"Czy podróżujesz z rodzicem?",
    "answerOriginal":"...",
    "answerLanguage":"ar",
    "askedAt":"2026-03-07T10:00:00Z"
  }'
```

### List statements

```bash
curl "http://127.0.0.1:8000/interviews/<UUID_INTERVIEW>/statements"
```

## 4) Test PCM endpoint

```bash
curl -X POST "http://127.0.0.1:8000/language/detect-audio" \
  -H "Content-Type: application/octet-stream" \
  -H "X-Audio-Format: pcm_s16le" \
  -H "X-Sample-Rate: 16000" \
  -H "X-Channels: 1" \
  -H "X-Interview-Id: <UUID_INTERVIEW>" \
  -H "X-Actor-Id: OFFICER-001" \
  --data-binary "@sample.pcm"
```
