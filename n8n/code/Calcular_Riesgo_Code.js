const parsed = $("Parsear_JSON_LLM").first().json;
if (parsed.resultado && parsed.decision && parsed.persistencia) {
  return [{ json: parsed }];
}
const historyRows = $input.all().map((item) => item.json ?? {});

const riskRank = { BAJO: 0, MEDIO: 1, ALTO: 2, CRITICO: 3 };
const dangerousObjects = new Set(["arma", "arma_blanca", "fusil", "violencia"]);

function clamp(value, min, max, fallback) {
  const parsedNumber = Number(value);
  if (!Number.isFinite(parsedNumber)) return fallback;
  return Math.max(min, Math.min(max, parsedNumber));
}

function normalizeObject(value) {
  const normalized = String(value ?? "").trim().toLowerCase().replace(/[_\s]+/g, "_");
  const aliases = {
    pistol: "arma",
    pistola: "arma",
    handgun: "arma",
    firearm: "arma",
    weapon: "arma",
    gun: "arma",
    rifle: "fusil",
    knife: "arma_blanca",
    cuchillo: "arma_blanca",
    scissors: "arma_blanca",
    cellphone: "cell_phone",
    mobile_phone: "cell_phone",
    phone: "cell_phone",
    nonviolence: "no_violencia",
    non_violence: "no_violencia",
    "non-violence": "no_violencia",
    no_violence: "no_violencia",
    "no-violence": "no_violencia",
    normal: "no_violencia",
    person: "persona",
    people: "multitud",
    crowd: "multitud",
    pelea: "violencia",
    fight: "violencia",
    fighting: "violencia",
    violence: "violencia",
  };
  return aliases[normalized] ?? normalized;
}

function riskFromScore(score) {
  if (score >= 90) return "CRITICO";
  if (score >= 70) return "ALTO";
  if (score >= 30) return "MEDIO";
  return "BAJO";
}

function actionFromRisk(risk, confidence) {
  const reviewActions = ["CONFIRMAR_AMENAZA", "FALSO_POSITIVO", "REQUIERE_MAS_REVISION"];
  if (risk === "CRITICO") {
    return {
      accion: "SOLICITAR_VALIDACION_URGENTE",
      prioridad: 10,
      notificar: true,
      canales: ["telegram_supervisor", "dashboard_realtime"],
      requiere_revision_humana: true,
      estado_revision_humana: "PENDIENTE",
      acciones_humanas_permitidas: reviewActions,
      automatizacion_bloqueada: true,
    };
  }
  if (risk === "ALTO") {
    return {
      accion: "SOLICITAR_VALIDACION_HUMANA",
      prioridad: 8,
      notificar: true,
      canales: ["telegram_supervisor", "dashboard_realtime"],
      requiere_revision_humana: true,
      estado_revision_humana: "PENDIENTE",
      acciones_humanas_permitidas: reviewActions,
      automatizacion_bloqueada: true,
    };
  }
  if (risk === "MEDIO") {
    return {
      accion: "SOLICITAR_REVISION_HUMANA",
      prioridad: 5,
      notificar: true,
      canales: ["telegram_supervisor"],
      requiere_revision_humana: true,
      estado_revision_humana: "PENDIENTE",
      acciones_humanas_permitidas: reviewActions,
      automatizacion_bloqueada: true,
    };
  }
  const accion = confidence < 0.5 ? "IGNORAR_BAJA_CONFIANZA" : "REGISTRAR_EVENTO";
  return {
    accion,
    prioridad: confidence < 0.5 ? 1 : 2,
    notificar: false,
    canales: [],
    requiere_revision_humana: false,
    estado_revision_humana: "NO_REQUERIDA",
    acciones_humanas_permitidas: [],
    automatizacion_bloqueada: false,
  };
}

function parseDate(value) {
  const date = new Date(value ?? "");
  return Number.isNaN(date.getTime()) ? null : date;
}

function sameCamera(row) {
  const camera = row.camara_id ?? row.camara ?? row.camera;
  return String(camera ?? "") === String(parsed.entrada?.camara ?? "");
}

function rowRisk(row) {
  return String(row.nivel_riesgo ?? row.riesgo ?? "").toUpperCase();
}

function addFactor(factors, points, code, detail) {
  factors.push({ code, points, detail });
  return points;
}

const now = parseDate(parsed.entrada?.hora) ?? new Date();
const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
const recentRows = historyRows.filter((row) => {
  if (!sameCamera(row)) return false;
  const detectedAt = parseDate(row.detected_at ?? row.fecha ?? row.timestamp);
  return detectedAt ? detectedAt >= dayAgo : true;
});

const previousAlerts24h = recentRows.filter((row) => ["ALTO", "CRITICO"].includes(rowRisk(row))).length;
const previousEvents24h = recentRows.length;

const factors = [...(parsed.resultado?.factores ?? [])];
let score = clamp(parsed.resultado?.score, 0, 100, 0);
const object = normalizeObject(parsed.entrada?.objeto);
const confidence = clamp(parsed.entrada?.confianza, 0, 1, 0);
const context = parsed.contexto ?? {};

if (previousAlerts24h >= 3) {
  score += addFactor(
    factors,
    12,
    "historial_alertas_sheets",
    `Historial en Sheets con ${previousAlerts24h} alertas recientes.`,
  );
} else if (previousAlerts24h >= 1) {
  score += addFactor(
    factors,
    6,
    "historial_alerta_reciente",
    `Historial en Sheets con ${previousAlerts24h} alerta reciente.`,
  );
}

if (previousEvents24h >= 20) {
  score += addFactor(
    factors,
    8,
    "actividad_recurrente",
    `Camara con ${previousEvents24h} eventos en 24h.`,
  );
}

if (object === "persona" && !dangerousObjects.has(object) && confidence < 0.7) {
  score -= addFactor(
    factors,
    8,
    "persona_baja_confianza",
    "Persona con baja confianza: se reduce riesgo para evitar falsa alarma.",
  );
}

score = Math.max(0, Math.min(100, Math.round(score)));
let risk = riskFromScore(score);

const llmRisk = String(parsed.resultado?.riesgo ?? parsed.resultado?.nivel_riesgo ?? "").toUpperCase();
const llmConfidence = clamp(parsed.resultado?.ia_confianza, 0, 1, 0);
if (llmConfidence >= 0.85 && riskRank[llmRisk] > riskRank[risk]) {
  risk = llmRisk;
  score = Math.max(score, { MEDIO: 30, ALTO: 70, CRITICO: 90 }[risk] ?? score);
}

const decision = actionFromRisk(risk, confidence);
const scoreRisk = Math.round((score / 100) * 10000) / 10000;

return [
  {
    json: {
      ...parsed,
      memoria: {
        ...(parsed.memoria ?? {}),
        eventos_previos_24h: previousEvents24h,
        alertas_previas_24h: previousAlerts24h,
      },
      resultado: {
        ...(parsed.resultado ?? {}),
        riesgo: risk,
        nivel_riesgo: risk,
        severidad: risk === "CRITICO" ? "CRITICA" : risk,
        score,
        score_riesgo: scoreRisk,
        factores: factors,
        algoritmo: "risk_rules_v3_history_llm_guarded",
        historial_consultado: true,
      },
      decision: {
        accion: decision.accion,
        accion_tomada: decision.accion,
        prioridad: decision.prioridad,
        notificar: decision.notificar,
        canales: decision.canales,
        guardar_en_supabase: true,
        guardar_en_sheets: true,
        requiere_revision_humana: decision.requiere_revision_humana,
        estado_revision_humana: decision.estado_revision_humana,
        acciones_humanas_permitidas: decision.acciones_humanas_permitidas,
        automatizacion_bloqueada: decision.automatizacion_bloqueada,
      },
      persistencia: {
        camara_id: parsed.entrada?.camara,
        objeto: parsed.entrada?.objeto,
        confianza: parsed.entrada?.confianza,
        score_riesgo: scoreRisk,
        nivel_riesgo: risk,
        accion_tomada: decision.accion,
        alertas_previas_24h: previousAlerts24h,
        detected_at: parsed.entrada?.hora,
        box: parsed.entrada?.box,
        contexto: parsed.contexto,
        tracking: parsed.tracking,
        memoria: {
          ...(parsed.memoria ?? {}),
          eventos_previos_24h: previousEvents24h,
          alertas_previas_24h: previousAlerts24h,
        },
        resumen_ia: parsed.resultado?.resumen_ia ?? "",
        factores_ia: parsed.resultado?.factores_ia ?? [],
        requiere_revision_humana: decision.requiere_revision_humana,
        estado_revision_humana: decision.estado_revision_humana,
        review_id: parsed.persistencia?.review_id ?? parsed.review_id,
      },
      mensaje: `${decision.accion}: ${risk} con score ${scoreRisk}`,
      procesado_en: new Date().toISOString(),
    },
  },
];
