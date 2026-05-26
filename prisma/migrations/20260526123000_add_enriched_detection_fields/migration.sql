ALTER TABLE "detection_events"
  ADD COLUMN IF NOT EXISTS "score_riesgo" DECIMAL(5,4),
  ADD COLUMN IF NOT EXISTS "nivel_riesgo" TEXT,
  ADD COLUMN IF NOT EXISTS "accion_tomada" TEXT,
  ADD COLUMN IF NOT EXISTS "alertas_previas_24h" INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS "hora_dia" INTEGER,
  ADD COLUMN IF NOT EXISTS "contexto" JSONB;

CREATE INDEX IF NOT EXISTS "idx_detection_events_camera_level_detected_at"
  ON "detection_events"("camara_id", "nivel_riesgo", "detected_at" DESC);
