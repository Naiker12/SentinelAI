const payload = $json.body ?? $json;
if (payload.entrada && payload.resultado && payload.decision) {
  return [{ json: payload }];
}
const contexto = payload.contexto ?? payload.context ?? {};
const tracking = payload.tracking ?? {};
const memoria = payload.memoria ?? payload.memory ?? {};

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

function numberOrDefault(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function boolOrDefault(value, fallback = false) {
  if (typeof value === "boolean") return value;
  if (value === undefined || value === null || value === "") return fallback;
  return ["1", "true", "yes", "si", "on"].includes(String(value).toLowerCase());
}

function addFactor(factors, points, code, detail) {
  factors.push({ code, points, detail });
  return points;
}

const objeto = normalizeObject(payload.objeto ?? payload.object);
const confianza = numberOrDefault(payload.confianza ?? payload.confidence);
const hora = String(payload.hora ?? payload.detected_at ?? new Date().toISOString());
const eventTime = new Date(hora);
const horaLocal = Number.isNaN(eventTime.getTime()) ? new Date().getHours() : eventTime.getHours();
const noche = horaLocal >= 22 || horaLocal <= 5;

const evento = {
  objeto,
  confianza,
  camara: String(payload.camara ?? payload.camera ?? payload.camara_id ?? "PC-01"),
  hora,
  box: payload.box ?? null,
  imagen: payload.imagen ?? payload.image_path ?? payload.imagen_url ?? null,
};

const escena = {
  zona: contexto.zona ?? contexto.zone ?? "sin_zona",
  iluminacion: normalizeObject(contexto.iluminacion ?? contexto.lighting ?? "desconocida"),
  cantidad_personas: numberOrDefault(contexto.cantidad_personas ?? contexto.people_count),
  hora_local: horaLocal,
  noche,
};

const seguimiento = {
  person_id: tracking.person_id ?? tracking.track_id ?? null,
  track_id: tracking.track_id ?? tracking.person_id ?? null,
  velocidad: numberOrDefault(tracking.velocidad ?? tracking.speed),
  permanencia_segundos: numberOrDefault(
    tracking.permanencia_segundos ?? tracking.loitering_seconds,
  ),
  movimiento_erratico: boolOrDefault(tracking.movimiento_erratico ?? tracking.erratic_motion),
};

const historial = {
  eventos_previos_24h: numberOrDefault(
    memoria.eventos_previos_24h ?? memoria.previous_events_24h,
  ),
  alertas_previas_24h: numberOrDefault(
    memoria.alertas_previas_24h ?? memoria.previous_alerts_24h,
  ),
};

const baseScores = {
  arma: 80,
  arma_blanca: 65,
  fusil: 95,
  violencia: 75,
  multitud: 35,
  persona_sospechosa: 45,
  no_violencia: 2,
  persona: 10,
  cell_phone: 5,
  backpack: 18,
  car: 8,
  truck: 8,
  motorcycle: 10,
};
const dangerousObjects = new Set(["arma", "arma_blanca", "fusil", "violencia"]);
const factors = [];
let score = 0;

if (!objeto) {
  score += addFactor(factors, 5, "payload_incompleto", "No se recibio objeto detectable.");
} else if (Object.prototype.hasOwnProperty.call(baseScores, objeto)) {
  score += addFactor(
    factors,
    baseScores[objeto],
    dangerousObjects.has(objeto) ? "objeto_peligroso" : "objeto_base",
    `Objeto detectado: ${objeto}.`,
  );
} else {
  score += addFactor(factors, 8, "objeto_observado", `Objeto observado sin regla critica: ${objeto}.`);
}

if (confianza >= 0.9) score += addFactor(factors, 10, "alta_confianza", `Confianza alta: ${confianza}.`);
else if (confianza >= 0.7) score += addFactor(factors, 5, "confianza_media", `Confianza aceptable: ${confianza}.`);
else score += addFactor(factors, -10, "baja_confianza", `Confianza baja: ${confianza}.`);

if (escena.noche) score += addFactor(factors, 15, "horario_nocturno", "Evento detectado en horario nocturno.");
if (["baja", "oscura", "low", "dark"].includes(escena.iluminacion)) {
  score += addFactor(factors, 10, "baja_iluminacion", "Condicion de baja iluminacion.");
}
if (historial.alertas_previas_24h >= 2) {
  score += addFactor(factors, 15, "historial_alertas", "La camara/zona tiene alertas recientes.");
}
if (historial.eventos_previos_24h >= 10) {
  score += addFactor(factors, 8, "historial_eventos", "La camara/zona tiene actividad reciente alta.");
}

score = Math.max(0, Math.min(100, Math.round(score)));

const evidencia = {
  evento,
  contexto: escena,
  tracking: seguimiento,
  memoria: historial,
  reglas: {
    score_base: score,
    factores: factors,
    objetos_peligrosos: Array.from(dangerousObjects),
  },
};

return [
  {
    json: {
      ...evidencia,
      review_id: `${evento.camara}_${objeto}_${hora}`.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 64),
      prompt_ia: JSON.stringify(evidencia, null, 2),
    },
  },
];
