const data = $json;
const persistence = data.persistencia ?? {};
const tracking = persistence.tracking ?? data.tracking ?? {};
const memory = persistence.memoria ?? data.memoria ?? {};

return [
  {
    json: {
      detected_at: persistence.detected_at ?? data.entrada?.hora ?? new Date().toISOString(),
      camara_id: persistence.camara_id ?? data.entrada?.camara ?? "PC-01",
      objeto: persistence.objeto ?? data.entrada?.objeto ?? "unknown",
      confianza: persistence.confianza ?? data.entrada?.confianza ?? 0,
      score_riesgo: persistence.score_riesgo ?? data.resultado?.score_riesgo ?? 0,
      nivel_riesgo: persistence.nivel_riesgo ?? data.resultado?.nivel_riesgo ?? "BAJO",
      accion_tomada: persistence.accion_tomada ?? data.decision?.accion_tomada ?? "REGISTRAR_EVENTO",
      track_id: tracking.track_id ?? "",
      person_id: tracking.person_id ?? "",
      velocidad: tracking.velocidad ?? 0,
      permanencia_segundos: tracking.permanencia_segundos ?? 0,
      movimiento_erratico: Boolean(tracking.movimiento_erratico),
      eventos_previos_24h: memory.eventos_previos_24h ?? 0,
      alertas_previas_24h: memory.alertas_previas_24h ?? 0,
      resumen_ia: persistence.resumen_ia ?? data.resultado?.resumen_ia ?? "",
      factores: JSON.stringify(data.resultado?.factores ?? []),
      factores_ia: JSON.stringify(persistence.factores_ia ?? data.resultado?.factores_ia ?? []),
      mensaje: data.mensaje ?? "",
      procesado_en: data.procesado_en ?? new Date().toISOString(),
    },
  },
];
