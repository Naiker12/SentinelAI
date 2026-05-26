const data = $json;

return [
  {
    json: {
      status: data.status ?? "procesado",
      agente: data.agente ?? "AgenteRiesgo",
      version: data.version ?? "0.5.0",
      pipeline: data.pipeline ?? [
        "AgentePercepcion",
        "AgenteTracking",
        "AgenteAnalisisIA",
        "AgenteRiesgo",
        "AgenteAccion",
        "AgenteMemoria",
      ],
      entrada: data.entrada,
      contexto: data.contexto,
      tracking: data.tracking,
      memoria: data.memoria,
      resultado: data.resultado,
      decision: data.decision,
      persistencia: data.persistencia,
      mensaje: data.mensaje,
      procesado_en: data.procesado_en ?? new Date().toISOString(),
    },
  },
];
