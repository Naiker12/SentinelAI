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
const reviewId = data.persistencia?.review_id ?? decision.review_id ?? data.review_id ?? "";
const legacyTrackId = tracking.track_id ?? tracking.person_id ?? "";
const reviewKey = sanitizeKey(reviewId || legacyTrackId || `${event.camara ?? "PC-01"}_${event.objeto ?? "unknown"}_${event.hora ?? Date.now()}`);
const factors = (data.resultado?.factores ?? [])
  .slice(-5)
  .map((factor) => `- ${escapeHtml(factor.code)}: ${escapeHtml(factor.detail)}`)
  .join("\n");

function sanitizeKey(value) {
  const safe = String(value).replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 40);
  return safe || "sin_evento";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

const text = [
  `<b>SentinelAI | Revision requerida - ${escapeHtml(risk)}</b>`,
  `Revision: ${escapeHtml(reviewKey)}`,
  `Camara: ${escapeHtml(event.camara ?? "PC-01")}`,
  `Deteccion: ${escapeHtml(event.objeto ?? "unknown")}`,
  `Confianza: ${escapeHtml(event.confianza ?? 0)}`,
  `Score: ${escapeHtml(score)}`,
  `Accion sugerida: ${escapeHtml(decision.accion_tomada ?? decision.accion ?? "REGISTRAR_EVENTO")}`,
  `Estado: ${escapeHtml(reviewStatus)}`,
  data.resultado?.resumen_ia ? `IA: ${escapeHtml(data.resultado.resumen_ia)}` : null,
  factors ? `Factores principales:\n${factors}` : null,
  reviewRequired ? "Decision: confirme el riesgo, descartelo o pida mas evidencia." : null,
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
                { text: "Confirmar riesgo", callback_data: `sentinel:confirm:${reviewKey}` },
                { text: "Descartar alerta", callback_data: `sentinel:false:${reviewKey}` },
              ],
              [
                { text: "Solicitar mas evidencia", callback_data: `sentinel:review:${reviewKey}` },
              ],
            ],
          }
        : undefined,
      review_context: {
        review_id: reviewKey,
        tracking_id: legacyTrackId || null,
        camara_id: event.camara ?? "PC-01",
        objeto: event.objeto ?? "unknown",
        requires_human_review: reviewRequired,
        human_review_status: reviewStatus,
        risk,
        score,
      },
    },
  },
];
