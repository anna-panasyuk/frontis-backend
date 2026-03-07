from __future__ import annotations

import hashlib
import os
import tempfile
import wave
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from faster_whisper import WhisperModel

PCM_FORMAT = "pcm_s16le"
PCM_SAMPLE_RATE = 16000
PCM_CHANNELS = 1
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://frontin:frontin_pass@localhost:5432/frontin")

app = FastAPI(title="FRONT.IN API", version="0.2.0")
MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
MODEL_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_SIZE, compute_type=MODEL_COMPUTE_TYPE)
    return _model


class ChildProfileCreate(BaseModel):
    caseCode: str
    declaredAge: Optional[int] = Field(default=None, ge=0, le=25)
    ageConfidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    unaccompaniedMinor: bool = True
    countryOfOrigin: Optional[str] = None
    primaryLanguage: Optional[str] = None
    secondaryLanguages: list[str] = Field(default_factory=list)


class ChildProfileOut(BaseModel):
    id: UUID
    caseCode: str
    declaredAge: Optional[int]
    ageConfidence: Optional[float]
    unaccompaniedMinor: bool
    countryOfOrigin: Optional[str]
    primaryLanguage: Optional[str]
    secondaryLanguages: list[str]
    createdAt: datetime


class InterviewCreate(BaseModel):
    childProfileId: UUID
    interviewType: Literal["rozpytanie_graniczne", "wysluchanie_opiekuncze", "wniosek_ochrona"]
    borderPointCode: Optional[str] = None
    officerId: str
    interpreterMode: Literal["human", "ai"]


class InterviewOut(BaseModel):
    id: UUID
    childProfileId: UUID
    interviewType: str
    status: str
    borderPointCode: Optional[str]
    officerId: str
    interpreterMode: str
    rightsExplained: bool
    rightsLanguageCode: Optional[str]
    rightsExplainedAt: Optional[datetime]
    startedAt: datetime
    endedAt: Optional[datetime]


class StatementCreate(BaseModel):
    stepCode: str
    questionText: str
    answerOriginal: str
    answerLanguage: str
    answerTranslated: Optional[str] = None
    translationConfidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    askedAt: datetime


class StatementOut(BaseModel):
    id: UUID
    interviewId: UUID
    stepCode: str
    questionText: str
    answerOriginal: str
    answerLanguage: str
    answerTranslated: Optional[str]
    translationConfidence: Optional[float]
    askedAt: datetime
    createdAt: datetime


class Candidate(BaseModel):
    languageCode: str
    confidence: float = Field(ge=0.0, le=1.0)


class DetectResponse(BaseModel):
    primaryLanguage: str
    candidates: list[Candidate]
    detectedAt: datetime


def db_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def validate_pcm(fmt: str, rate: int, channels: int) -> None:
    if fmt != PCM_FORMAT:
        raise HTTPException(status_code=415, detail=f"Expected {PCM_FORMAT}")
    if rate != PCM_SAMPLE_RATE:
        raise HTTPException(status_code=422, detail=f"Expected sample rate {PCM_SAMPLE_RATE}")
    if channels != PCM_CHANNELS:
        raise HTTPException(status_code=422, detail=f"Expected channels {PCM_CHANNELS}")


def bytes_to_wav(data: bytes) -> str:
    if len(data) < 2:
        raise HTTPException(status_code=400, detail="Empty/too short audio")
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(PCM_CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(PCM_SAMPLE_RATE)
        wf.writeframes(data)
    return path


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/child-profiles", response_model=ChildProfileOut)
def create_child_profile(payload: ChildProfileCreate):
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into child_profiles (
                  case_code, declared_age, age_confidence, unaccompanied_minor,
                  country_of_origin, primary_language, secondary_languages
                ) values (%s, %s, %s, %s, %s, %s, %s)
                returning id, case_code, declared_age, age_confidence, unaccompanied_minor,
                          country_of_origin, primary_language, secondary_languages, created_at
                """,
                (
                    payload.caseCode,
                    payload.declaredAge,
                    payload.ageConfidence,
                    payload.unaccompaniedMinor,
                    payload.countryOfOrigin,
                    payload.primaryLanguage,
                    payload.secondaryLanguages,
                ),
            )
            row = cur.fetchone()
    return ChildProfileOut(
        id=row["id"],
        caseCode=row["case_code"],
        declaredAge=row["declared_age"],
        ageConfidence=float(row["age_confidence"]) if row["age_confidence"] is not None else None,
        unaccompaniedMinor=row["unaccompanied_minor"],
        countryOfOrigin=row["country_of_origin"],
        primaryLanguage=row["primary_language"],
        secondaryLanguages=row["secondary_languages"] or [],
        createdAt=row["created_at"],
    )


@app.get("/child-profiles/{child_id}", response_model=ChildProfileOut)
def get_child_profile(child_id: UUID):
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, case_code, declared_age, age_confidence, unaccompanied_minor,
                       country_of_origin, primary_language, secondary_languages, created_at
                from child_profiles where id = %s::uuid
                """,
                (child_id,),
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Child profile not found")

    return ChildProfileOut(
        id=row["id"],
        caseCode=row["case_code"],
        declaredAge=row["declared_age"],
        ageConfidence=float(row["age_confidence"]) if row["age_confidence"] is not None else None,
        unaccompaniedMinor=row["unaccompanied_minor"],
        countryOfOrigin=row["country_of_origin"],
        primaryLanguage=row["primary_language"],
        secondaryLanguages=row["secondary_languages"] or [],
        createdAt=row["created_at"],
    )


@app.post("/interviews", response_model=InterviewOut)
def create_interview(payload: InterviewCreate):
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from child_profiles where id = %s::uuid", (payload.childProfileId,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Child profile not found")

            cur.execute(
                """
                insert into interviews (
                  child_profile_id, interview_type, border_point_code, officer_id, interpreter_mode
                ) values (%s::uuid, %s, %s, %s, %s)
                returning id, child_profile_id, interview_type, status, border_point_code,
                          officer_id, interpreter_mode, rights_explained, rights_language_code,
                          rights_explained_at, started_at, ended_at
                """,
                (
                    payload.childProfileId,
                    payload.interviewType,
                    payload.borderPointCode,
                    payload.officerId,
                    payload.interpreterMode,
                ),
            )
            row = cur.fetchone()

    return InterviewOut(
        id=row["id"],
        childProfileId=row["child_profile_id"],
        interviewType=row["interview_type"],
        status=row["status"],
        borderPointCode=row["border_point_code"],
        officerId=row["officer_id"],
        interpreterMode=row["interpreter_mode"],
        rightsExplained=row["rights_explained"],
        rightsLanguageCode=row["rights_language_code"],
        rightsExplainedAt=row["rights_explained_at"],
        startedAt=row["started_at"],
        endedAt=row["ended_at"],
    )


@app.post("/interviews/{interview_id}/statements", response_model=StatementOut)
def create_statement(interview_id: UUID, payload: StatementCreate):
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from interviews where id = %s::uuid", (interview_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Interview not found")

            cur.execute(
                """
                insert into interview_statements (
                  interview_id, step_code, question_text, answer_original, answer_language,
                  answer_translated, translation_confidence, asked_at
                ) values (%s::uuid, %s, %s, %s, %s, %s, %s, %s)
                returning id, interview_id, step_code, question_text, answer_original,
                          answer_language, answer_translated, translation_confidence,
                          asked_at, created_at
                """,
                (
                    interview_id,
                    payload.stepCode,
                    payload.questionText,
                    payload.answerOriginal,
                    payload.answerLanguage,
                    payload.answerTranslated,
                    payload.translationConfidence,
                    payload.askedAt,
                ),
            )
            row = cur.fetchone()

    return StatementOut(
        id=row["id"],
        interviewId=row["interview_id"],
        stepCode=row["step_code"],
        questionText=row["question_text"],
        answerOriginal=row["answer_original"],
        answerLanguage=row["answer_language"],
        answerTranslated=row["answer_translated"],
        translationConfidence=float(row["translation_confidence"]) if row["translation_confidence"] is not None else None,
        askedAt=row["asked_at"],
        createdAt=row["created_at"],
    )


@app.get("/interviews/{interview_id}/statements", response_model=list[StatementOut])
def list_statements(interview_id: UUID):
    with db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select id, interview_id, step_code, question_text, answer_original,
                       answer_language, answer_translated, translation_confidence,
                       asked_at, created_at
                from interview_statements
                where interview_id = %s::uuid
                order by asked_at asc
                """,
                (interview_id,),
            )
            rows = cur.fetchall()

    return [
        StatementOut(
            id=row["id"],
            interviewId=row["interview_id"],
            stepCode=row["step_code"],
            questionText=row["question_text"],
            answerOriginal=row["answer_original"],
            answerLanguage=row["answer_language"],
            answerTranslated=row["answer_translated"],
            translationConfidence=float(row["translation_confidence"]) if row["translation_confidence"] is not None else None,
            askedAt=row["asked_at"],
            createdAt=row["created_at"],
        )
        for row in rows
    ]


@app.post("/language/detect-audio", response_model=DetectResponse)
def detect_audio(
    body: bytes,
    x_audio_format: Literal["pcm_s16le"] = Header(..., alias="X-Audio-Format"),
    x_sample_rate: int = Header(..., alias="X-Sample-Rate"),
    x_channels: int = Header(..., alias="X-Channels"),
    x_interview_id: str = Header(..., alias="X-Interview-Id"),
    x_actor_id: str = Header("system", alias="X-Actor-Id"),
) -> DetectResponse:
    validate_pcm(x_audio_format, x_sample_rate, x_channels)

    wav_path = bytes_to_wav(body)
    sha = hashlib.sha256(body).hexdigest()

    try:
        whisper_model = get_model()
        segments, info = whisper_model.transcribe(wav_path, task="transcribe", vad_filter=True, beam_size=1, best_of=1)
        _ = list(segments)

        lang = info.language or "und"
        conf = float(info.language_probability or 0.0)
        conf = max(0.0, min(conf, 1.0))

        with db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into audio_inputs (interview_id, audio_format, sample_rate_hz, channels, duration_ms, sha256)
                    values (%s::uuid, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (x_interview_id, PCM_FORMAT, PCM_SAMPLE_RATE, PCM_CHANNELS, None, sha),
                )
                audio_input_id = cur.fetchone()["id"]

                cur.execute(
                    """
                    insert into language_detections (audio_input_id, primary_language, confidence, provider)
                    values (%s::uuid, %s, %s, 'faster-whisper')
                    """,
                    (audio_input_id, lang, conf),
                )

                cur.execute(
                    """
                    insert into audit_logs (actor_id, entity_type, entity_id, action, metadata)
                    values (%s, 'language_detection', %s::uuid, 'language.detected', %s::jsonb)
                    """,
                    (x_actor_id, audio_input_id, '{"source":"pcm"}'),
                )

        return DetectResponse(
            primaryLanguage=lang,
            candidates=[Candidate(languageCode=lang, confidence=conf)],
            detectedAt=datetime.now(timezone.utc),
        )
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)
