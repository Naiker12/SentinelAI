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
  },
  false: {
    human_label: "false_positive",
    estado_revision_humana: "FALSO_POSITIVO",
    accion_final: "CERRAR_EVENTO",
    alimentar_entrenamiento: true,
  },
  review: {
    human_label: "needs_more_review",
    estado_revision_humana: "REQUIERE_MAS_REVISION",
    accion_final: "SOLICITAR_MAS_CONTEXTO",
    alimentar_entrenamiento: false,
  },
};

const actionKey = parts[1] ?? "";
const trackingId = parts[2] ?? payload.tracking_id ?? "";
const selected = actionMap[actionKey] ?? {
  human_label: "unknown",
  estado_revision_humana: "DESCONOCIDA",
  accion_final: "REVISAR_MANUALMENTE",
  alimentar_entrenamiento: false,
};

return [
  {
    json: {
      source: "telegram_supervisor",
      callback_data: callbackData,
      tracking_id: trackingId,
      supervisor: {
        user_id: callback.from?.id ?? payload.user_id ?? null,
        username: callback.from?.username ?? payload.username ?? null,
        decided_at: new Date().toISOString(),
        ...selected,
      },
      persistencia_feedback: {
        tracking_id: trackingId,
        human_label: selected.human_label,
        estado_revision_humana: selected.estado_revision_humana,
        accion_final: selected.accion_final,
        alimentar_entrenamiento: selected.alimentar_entrenamiento,
        raw_callback: callbackData,
      },
    },
  },
];
