const payload = $json.body ?? $json;
const callback = payload.callback_query ?? payload.callback ?? {};
const callbackData = String(callback.data ?? payload.callback_data ?? "");
const parts = callbackData.split(":");

const actionMap = {
  confirm: {
    human_label: "real_threat",
    estado_revision_humana: "CONFIRMADA",
    accion_final: "ACTIVAR_PROTOCOLO",
    alimentar_entrenamiento: true,
    titulo: "ALERTA ACTIVADA",
    detalle: "Amenaza confirmada por supervisor. Activar protocolo operativo.",
  },
  false: {
    human_label: "false_positive",
    estado_revision_humana: "FALSO_POSITIVO",
    accion_final: "CERRAR_EVENTO",
    alimentar_entrenamiento: true,
    titulo: "EVENTO CERRADO",
    detalle: "Marcado como falso positivo. Guardar feedback para reentrenamiento.",
  },
  review: {
    human_label: "needs_more_review",
    estado_revision_humana: "REQUIERE_MAS_REVISION",
    accion_final: "SOLICITAR_MAS_CONTEXTO",
    alimentar_entrenamiento: false,
    titulo: "REVISION ADICIONAL",
    detalle: "Solicitar nueva captura o enviar el evento a un nodo IA para explicar la escena.",
  },
};

const actionKey = parts[0] === "sentinel" ? parts[1] ?? "" : "";
const reviewId = parts[0] === "sentinel" ? parts[2] ?? "" : payload.review_id ?? "";
const trackingId = payload.tracking_id ?? "";
const selected = actionMap[actionKey] ?? {
  human_label: "unknown",
  estado_revision_humana: "DESCONOCIDA",
  accion_final: "REVISAR_MANUALMENTE",
  alimentar_entrenamiento: false,
  titulo: "RESPUESTA RECIBIDA",
  detalle: "Accion no reconocida. Revisar manualmente.",
};

return [
  {
    json: {
      source: "telegram_supervisor",
      callback_data: callbackData,
      review_id: reviewId,
      tracking_id: trackingId,
      answer_callback_query: {
        callback_query_id: callback.id ?? payload.callback_query_id ?? null,
        text: `SentinelAI: ${selected.estado_revision_humana}`,
        show_alert: false,
      },
      supervisor: {
        user_id: callback.from?.id ?? payload.user_id ?? null,
        username: callback.from?.username ?? payload.username ?? null,
        decided_at: new Date().toISOString(),
        ...selected,
      },
      telegram_followup: {
        text: [
          `<b>SentinelAI - ${selected.titulo}</b>`,
          `Revision: ${reviewId || "sin_evento"}`,
          `Estado: ${selected.estado_revision_humana}`,
          selected.detalle,
        ].join("\n"),
        parse_mode: "HTML",
        request_new_capture: actionKey === "review",
        run_ai_review: actionKey === "review" || actionKey === "confirm",
      },
      persistencia_feedback: {
        review_id: reviewId,
        tracking_id: trackingId,
        camara_id: payload.camara_id ?? null,
        detection_event_id: payload.detection_event_id ?? null,
        human_label: selected.human_label,
        estado_revision_humana: selected.estado_revision_humana,
        accion_final: selected.accion_final,
        supervisor_user_id: callback.from?.id ?? payload.user_id ?? null,
        supervisor_username: callback.from?.username ?? payload.username ?? null,
        alimentar_entrenamiento: selected.alimentar_entrenamiento,
        raw_callback: callbackData,
        decided_at: new Date().toISOString(),
      },
    },
  },
];
