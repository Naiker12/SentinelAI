const data = $json;
const risk = data.resultado?.nivel_riesgo ?? "BAJO";
const event = data.entrada ?? {};
const tracking = data.tracking ?? {};
const decision = data.decision ?? {};
const score = data.resultado?.score_riesgo ?? 0;
const factors = (data.resultado?.factores ?? [])
  .slice(-5)
  .map((factor) => `- ${factor.code}: ${factor.detail}`)
  .join("\n");

const text = [
  `SentinelAI ${risk}`,
  `Accion: ${decision.accion_tomada ?? decision.accion ?? "REGISTRAR_EVENTO"}`,
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
      disable_notification: risk !== "CRITICO",
    },
  },
];
