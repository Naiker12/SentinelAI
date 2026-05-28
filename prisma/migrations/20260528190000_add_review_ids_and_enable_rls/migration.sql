ALTER TABLE "detection_events"
  ADD COLUMN IF NOT EXISTS "review_id" TEXT;

DO $$ BEGIN
  CREATE TYPE "HumanReviewStatus" AS ENUM (
    'PENDIENTE',
    'CONFIRMADA',
    'FALSO_POSITIVO',
    'REQUIERE_MAS_REVISION',
    'NO_REQUERIDA',
    'DESCONOCIDA'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS "human_reviews" (
  "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  "detection_event_id" UUID REFERENCES "detection_events"("id"),
  "tracking_id" TEXT,
  "camara_id" TEXT,
  "estado_revision" "HumanReviewStatus" NOT NULL DEFAULT 'PENDIENTE',
  "human_label" TEXT,
  "accion_final" TEXT,
  "supervisor_user_id" TEXT,
  "supervisor_username" TEXT,
  "alimentar_entrenamiento" BOOLEAN NOT NULL DEFAULT false,
  "raw_callback" TEXT,
  "contexto" JSONB,
  "decided_at" TIMESTAMPTZ(6),
  "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT now()
);

ALTER TABLE "human_reviews"
  ADD COLUMN IF NOT EXISTS "review_id" TEXT;

CREATE INDEX IF NOT EXISTS "idx_detection_events_review_id"
  ON "detection_events"("review_id");

CREATE INDEX IF NOT EXISTS "idx_human_reviews_tracking_created_at"
  ON "human_reviews"("tracking_id", "created_at" DESC);

CREATE INDEX IF NOT EXISTS "idx_human_reviews_status_created_at"
  ON "human_reviews"("estado_revision", "created_at" DESC);

CREATE INDEX IF NOT EXISTS "idx_human_reviews_review_id_created_at"
  ON "human_reviews"("review_id", "created_at" DESC);

ALTER TABLE "camaras" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "detection_events" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "human_reviews" ENABLE ROW LEVEL SECURITY;
