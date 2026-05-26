const data = $json;
const risk = data.resultado?.nivel_riesgo ?? "BAJO";
const event = data.entrada ?? {};
const tracking = data.tracking ?? {};
const decision = data.decision ?? {};
const score = data.resultado?.score_riesgo ?? 0;
const reviewRequired = Boolean(
  decision.requiere_revision_humana ?? decision.requires_human_review,
);
const reviewStatus = decision.estado_revision_humana ?? decision.human_review_status ?? "NO_REQUERIDA";
const trackId = tracking.track_id ?? tracking.person_id ?? "sin_track";
const reviewKey = String(trackId).replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 32) || "sin_track";
const factors = (data.resultado?.factores ?? [])
  .slice(-5)
  .map((factor) => `- ${factor.code}: ${factor.detail}`)
  .join("\n");

const text = [
  `SentinelAI - Revision ${risk}`,
  `Accion: ${decision.accion_tomada ?? decision.accion ?? "REGISTRAR_EVENTO"}`,
  `Revision humana: ${reviewStatus}`,
  `Camara: ${event.camara ?? "PC-01"}`,
  `Objeto: ${event.objeto ?? "unknown"} (${event.confianza ?? 0})`,
  `Score: ${score}`,
  tracking.person_id ? `Persona asociada: ${tracking.person_id}` : null,
  tracking.track_id ? `Track: ${tracking.track_id}` : null,
  data.resultado?.resumen_ia ? `IA: ${data.resultado.resumen_ia}` : null,
  factors ? `Factores:\n${factors}` : null,
].filter(Boolean).join("\n");

return [
  {
    json: {
      text,
      parse_mode: "HTML",
      disable_notification: !["CRITICO", "ALTO"].includes(risk),
      reply_markup: reviewRequired
        ? {
            inline_keyboard: [
              [
                { text: "Confirmar amenaza", callback_data: `sentinel:confirm:${reviewKey}` },
                { text: "Falso positivo", callback_data: `sentinel:false:${reviewKey}` },
              ],
              [
                { text: "Mas revision", callback_data: `sentinel:review:${reviewKey}` },
              ],
            ],
          }
        : undefined,
      review_context: {
        tracking_id: trackId,
        requires_human_review: reviewRequired,
        human_review_status: reviewStatus,
        risk,
      },
    },
  },
];
