-- SepsisGuard AI prototype schema. PostgreSQL 16+.
-- No names, dates of birth, addresses, MRNs, free text, or raw credentials.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS sepsisguard;
SET search_path TO sepsisguard, public;

CREATE TABLE users (
  user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  external_subject_hash varchar(128) UNIQUE NOT NULL,
  role_code varchar(32) NOT NULL CHECK (role_code IN ('admin','clinician','analyst','service')),
  active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(), disabled_at timestamptz
);
CREATE TABLE patients (
  patient_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  subject_pseudonym varchar(128) UNIQUE NOT NULL,
  birth_year smallint CHECK (birth_year BETWEEN 1850 AND 2100), sex_at_birth varchar(16),
  source_system varchar(32) NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), retired_at timestamptz
);
CREATE TABLE icu_stays (
  stay_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(patient_id),
  source_stay_pseudonym varchar(128) UNIQUE NOT NULL, admitted_at timestamptz NOT NULL, discharged_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(), CHECK (discharged_at IS NULL OR discharged_at >= admitted_at)
);
CREATE INDEX icu_stays_patient_admit_ix ON icu_stays(patient_id, admitted_at DESC);

CREATE TABLE model_versions (
  model_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), model_name varchar(80) NOT NULL,
  semantic_version varchar(48) NOT NULL, artifact_uri text NOT NULL, artifact_sha256 char(64) NOT NULL,
  feature_schema_sha256 char(64) NOT NULL, training_data_version varchar(80) NOT NULL,
  calibration_method varchar(64), decision_threshold numeric(6,5), validation_summary jsonb NOT NULL DEFAULT '{}',
  status varchar(24) NOT NULL CHECK (status IN ('candidate','validated','active','retired','blocked')),
  created_at timestamptz NOT NULL DEFAULT now(), activated_at timestamptz, retired_at timestamptz,
  UNIQUE(model_name, semantic_version)
);
CREATE UNIQUE INDEX one_active_model_ix ON model_versions(model_name) WHERE status='active';

CREATE TABLE observations (
  observation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), stay_id uuid NOT NULL REFERENCES icu_stays(stay_id),
  observed_at timestamptz NOT NULL, received_at timestamptz NOT NULL DEFAULT now(),
  vital_type varchar(32) NOT NULL CHECK (vital_type IN ('heart_rate','map','sbp','resp_rate','spo2','temperature_c')),
  value numeric(12,4), unit varchar(16) NOT NULL, source varchar(32) NOT NULL,
  signal_quality varchar(8) CHECK (signal_quality IN ('HIGH','MEDIUM','LOW')),
  quality_reason jsonb NOT NULL DEFAULT '[]', raw_value numeric(12,4), usable_value numeric(12,4),
  source_event_hash char(64) UNIQUE, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX observations_stay_time_ix ON observations(stay_id, observed_at DESC);
CREATE INDEX observations_type_time_ix ON observations(vital_type, observed_at DESC);

CREATE TABLE laboratory_results (
  lab_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), stay_id uuid NOT NULL REFERENCES icu_stays(stay_id),
  collected_at timestamptz NOT NULL, received_at timestamptz NOT NULL DEFAULT now(), lab_code varchar(64) NOT NULL,
  value numeric(14,5), unit varchar(24), abnormal_flag varchar(16), source_event_hash char(64) UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX laboratory_results_stay_time_ix ON laboratory_results(stay_id, collected_at DESC);
CREATE INDEX laboratory_results_code_time_ix ON laboratory_results(lab_code, collected_at DESC);

CREATE TABLE model_predictions (
  prediction_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), stay_id uuid NOT NULL REFERENCES icu_stays(stay_id),
  model_version_id uuid NOT NULL REFERENCES model_versions(model_version_id),
  prediction_at timestamptz NOT NULL, horizon_minutes smallint NOT NULL CHECK (horizon_minutes > 0),
  risk_probability numeric(6,5) NOT NULL CHECK (risk_probability BETWEEN 0 AND 1),
  interval_lower numeric(6,5) CHECK (interval_lower BETWEEN 0 AND 1), interval_upper numeric(6,5) CHECK (interval_upper BETWEEN 0 AND 1),
  confidence varchar(8) NOT NULL CHECK (confidence IN ('HIGH','MEDIUM','LOW')),
  signal_quality varchar(8) NOT NULL CHECK (signal_quality IN ('HIGH','MEDIUM','LOW')),
  feature_snapshot jsonb NOT NULL, latency_ms numeric(10,3), correlation_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (interval_lower IS NULL OR interval_upper IS NULL OR interval_lower <= interval_upper)
);
CREATE INDEX predictions_stay_time_ix ON model_predictions(stay_id, prediction_at DESC);
CREATE INDEX predictions_model_time_ix ON model_predictions(model_version_id, prediction_at DESC);
CREATE INDEX predictions_correlation_ix ON model_predictions(correlation_id);

CREATE TABLE explanations (
  explanation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), prediction_id uuid NOT NULL REFERENCES model_predictions(prediction_id) ON DELETE CASCADE,
  method varchar(48) NOT NULL CHECK (method IN ('tree_shap','integrated_gradients','coefficient','hybrid_provenance')),
  method_version varchar(48) NOT NULL, baseline_reference jsonb, global_ranked_features jsonb,
  local_contributions jsonb NOT NULL, plain_language text NOT NULL, disclaimer text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX explanations_prediction_ix ON explanations(prediction_id);

CREATE TABLE alerts (
  alert_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), stay_id uuid NOT NULL REFERENCES icu_stays(stay_id),
  prediction_id uuid REFERENCES model_predictions(prediction_id), opened_at timestamptz NOT NULL,
  closed_at timestamptz, severity varchar(24) NOT NULL CHECK (severity IN ('YELLOW_WATCH','ORANGE_REVIEW','RED_URGENT')),
  status varchar(16) NOT NULL CHECK (status IN ('active','closed','suppressed','cancelled')),
  review_level varchar(80) NOT NULL, reason jsonb NOT NULL, deduplication_key char(64) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(), CHECK (closed_at IS NULL OR closed_at >= opened_at)
);
CREATE INDEX alerts_stay_active_ix ON alerts(stay_id, opened_at DESC) WHERE status='active';
CREATE INDEX alerts_dedupe_ix ON alerts(deduplication_key, opened_at DESC);

CREATE TABLE alert_history (
  alert_history_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), alert_id uuid NOT NULL REFERENCES alerts(alert_id) ON DELETE CASCADE,
  occurred_at timestamptz NOT NULL, event_type varchar(24) NOT NULL CHECK (event_type IN ('opened','escalated','repeated','suppressed','downgraded','closed','acknowledged')),
  from_severity varchar(24), to_severity varchar(24), reason jsonb NOT NULL DEFAULT '{}',
  actor_user_id uuid REFERENCES users(user_id), correlation_id uuid, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX alert_history_alert_time_ix ON alert_history(alert_id, occurred_at);

CREATE TABLE clinical_feedback (
  feedback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), prediction_id uuid REFERENCES model_predictions(prediction_id), alert_id uuid REFERENCES alerts(alert_id),
  reviewer_user_id uuid REFERENCES users(user_id), submitted_at timestamptz NOT NULL DEFAULT now(),
  disposition varchar(32) NOT NULL CHECK (disposition IN ('useful','not_useful','data_quality_concern','not_reviewed')),
  structured_reason varchar(64), comment_redacted text, created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (prediction_id IS NOT NULL OR alert_id IS NOT NULL)
);
CREATE INDEX clinical_feedback_prediction_ix ON clinical_feedback(prediction_id, submitted_at DESC);

CREATE TABLE system_logs (
  log_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, occurred_at timestamptz NOT NULL DEFAULT now(),
  level varchar(8) NOT NULL CHECK (level IN ('DEBUG','INFO','WARNING','ERROR','CRITICAL')),
  component varchar(64) NOT NULL, event_type varchar(64) NOT NULL, correlation_id uuid,
  stay_id uuid REFERENCES icu_stays(stay_id), model_version_id uuid REFERENCES model_versions(model_version_id),
  details jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX system_logs_time_ix ON system_logs(occurred_at DESC);
CREATE INDEX system_logs_correlation_ix ON system_logs(correlation_id);

CREATE TABLE audit_events (
  audit_event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, occurred_at timestamptz NOT NULL DEFAULT now(),
  actor_user_id uuid REFERENCES users(user_id), actor_type varchar(16) NOT NULL CHECK (actor_type IN ('user','service','system')),
  action varchar(64) NOT NULL, entity_type varchar(64) NOT NULL, entity_id uuid, correlation_id uuid,
  before_state jsonb, after_state jsonb, request_metadata jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX audit_events_entity_ix ON audit_events(entity_type, entity_id, occurred_at DESC);
CREATE INDEX audit_events_actor_time_ix ON audit_events(actor_user_id, occurred_at DESC);

-- Retention defaults (execute via a scheduled privileged job, after policy approval):
-- observations/laboratory_results: 30 days hot, then aggregated/de-identified archive;
-- predictions/explanations/alerts/feedback/audit: 7 years or approved governance period;
-- system_logs: 90 days hot, then security archive; never delete audit data ad hoc.
