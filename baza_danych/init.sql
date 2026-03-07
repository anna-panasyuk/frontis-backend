CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS child_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_code text NOT NULL UNIQUE,
  declared_age int CHECK (declared_age BETWEEN 0 AND 25),
  age_confidence numeric(3,2) CHECK (age_confidence BETWEEN 0 AND 1),
  unaccompanied_minor boolean NOT NULL DEFAULT true,
  country_of_origin text,
  primary_language text,
  secondary_languages text[] DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_profile_id uuid NOT NULL REFERENCES child_profiles(id) ON DELETE CASCADE,
  interview_type text NOT NULL CHECK (interview_type IN ('rozpytanie_graniczne','wysluchanie_opiekuncze','wniosek_ochrona')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','closed')),
  border_point_code text,
  officer_id text NOT NULL,
  interpreter_mode text NOT NULL CHECK (interpreter_mode IN ('human','ai')),
  rights_explained boolean NOT NULL DEFAULT false,
  rights_language_code text,
  rights_explained_at timestamptz,
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz
);

CREATE TABLE IF NOT EXISTS interview_statements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  interview_id uuid NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
  step_code text NOT NULL,
  question_text text NOT NULL,
  answer_original text NOT NULL,
  answer_language text NOT NULL,
  answer_translated text,
  translation_confidence numeric(3,2) CHECK (translation_confidence BETWEEN 0 AND 1),
  asked_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS safeguarding_flags (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  interview_id uuid NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
  code text NOT NULL CHECK (code IN (
    'unaccompanied_minor',
    'possible_trafficking',
    'urgent_medical_need',
    'severe_distress',
    'possible_age_dispute'
  )),
  severity text NOT NULL CHECK (severity IN ('low','medium','high','critical')),
  source text NOT NULL CHECK (source IN ('officer','psychologist','system')),
  note text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS protection_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_profile_id uuid NOT NULL REFERENCES child_profiles(id) ON DELETE CASCADE,
  interview_id uuid REFERENCES interviews(id),
  legal_status text NOT NULL CHECK (legal_status IN (
    'screening',
    'guardianship_pending',
    'guardianship_assigned',
    'asylum_application_drafted',
    'asylum_application_submitted',
    'referred_for_age_assessment',
    'closed'
  )),
  guardian_assigned boolean NOT NULL DEFAULT false,
  guardian_id text,
  next_action text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audio_inputs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  interview_id uuid NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
  audio_format text NOT NULL CHECK (audio_format = 'pcm_s16le'),
  sample_rate_hz int NOT NULL CHECK (sample_rate_hz = 16000),
  channels int NOT NULL CHECK (channels = 1),
  duration_ms int,
  sha256 text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS language_detections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  audio_input_id uuid NOT NULL REFERENCES audio_inputs(id) ON DELETE CASCADE,
  primary_language text NOT NULL,
  confidence numeric(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  provider text NOT NULL DEFAULT 'faster-whisper',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id text NOT NULL,
  entity_type text NOT NULL CHECK (entity_type IN (
    'child_profile','interview','statement','flag','case','audio_input','language_detection'
  )),
  entity_id uuid NOT NULL,
  action text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_interviews_child ON interviews(child_profile_id);
CREATE INDEX IF NOT EXISTS idx_statements_interview ON interview_statements(interview_id);
CREATE INDEX IF NOT EXISTS idx_flags_interview ON safeguarding_flags(interview_id);
CREATE INDEX IF NOT EXISTS idx_cases_child ON protection_cases(child_profile_id);
CREATE INDEX IF NOT EXISTS idx_audio_interview ON audio_inputs(interview_id);
CREATE INDEX IF NOT EXISTS idx_detection_audio ON language_detections(audio_input_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
