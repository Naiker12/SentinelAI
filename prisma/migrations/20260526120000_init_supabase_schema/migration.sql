-- CreateEnum
CREATE TYPE "RiskLevel" AS ENUM ('BAJO', 'MEDIO', 'ALTO', 'DESCONOCIDO');

-- CreateTable
CREATE TABLE "camaras" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "codigo" TEXT NOT NULL,
    "nombre" TEXT NOT NULL,
    "ubicacion" TEXT,
    "activa" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "camaras_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "detection_events" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "objeto" TEXT NOT NULL,
    "confianza" DECIMAL(5,4) NOT NULL,
    "riesgo" "RiskLevel" NOT NULL,
    "detected_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "camara_id" TEXT NOT NULL,
    "box" JSONB NOT NULL,
    "imagen_url" TEXT,
    "ubicacion" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "detection_events_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "camaras_codigo_key" ON "camaras"("codigo");

-- CreateIndex
CREATE INDEX "idx_detection_events_camera_detected_at" ON "detection_events"("camara_id", "detected_at" DESC);

-- CreateIndex
CREATE INDEX "idx_detection_events_detected_at" ON "detection_events"("detected_at" DESC);

-- CreateIndex
CREATE INDEX "idx_detection_events_risk_detected_at" ON "detection_events"("riesgo", "detected_at" DESC);

-- CreateIndex
CREATE INDEX "idx_detection_events_object_detected_at" ON "detection_events"("objeto", "detected_at" DESC);
