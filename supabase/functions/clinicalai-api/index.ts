const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, x-client-info, content-type, Content-Type, Accept",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};

const DEFAULT_MODEL_API_URL = "https://hospital-readmission-8lq2.onrender.com";

function getModelApiUrl(): string {
  const configured = Deno.env.get("MODEL_API_URL");
  if (configured && configured.trim()) {
    return configured.trim().replace(/\/+$/, "");
  }
  return DEFAULT_MODEL_API_URL;
}

const selectFields = [
  "idx",
  "enc_id",
  "age",
  "age_group",
  "gender",
  "race",
  "stay",
  "meds",
  "inpatient",
  "er",
  "a1c",
  "diag",
  "prob",
  "tier",
  "resources",
  "top_factors",
  "actual",
].join(",");

const diagnosisCategories = new Set([
  "Circulatory",
  "Respiratory",
  "Digestive",
  "Diabetes",
  "Injury",
  "Musculoskeletal",
  "Genitourinary",
  "Neoplasms",
  "Other",
  "Other/External",
]);
const a1cResults = new Set([">8", ">7", "Norm", "None", "Missing"]);

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function requiredEnvironment(name: string) {
  const value = Deno.env.get(name);
  if (!value) throw new Error(`Missing server configuration: ${name}`);
  return value.replace(/\/+$/, "");
}

async function databaseRows(path: string, query: URLSearchParams) {
  const baseUrl = requiredEnvironment("SUPABASE_URL");
  const publicKey = Deno.env.get("SUPABASE_ANON_KEY");
  if (!publicKey) throw new Error("Missing Supabase public API key configuration");

  const response = await fetch(`${baseUrl}/rest/v1/${path}?${query}`, {
    headers: {
      apikey: publicKey,
      Authorization: `Bearer ${publicKey}`,
      Prefer: "count=exact",
    },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Database request failed (${response.status}): ${message.slice(0, 300)}`);
  }
  return { rows: await response.json(), contentRange: response.headers.get("content-range") };
}

async function worklist(requestUrl: URL) {
  const page = Math.max(1, Number.parseInt(requestUrl.searchParams.get("page") || "1", 10) || 1);
  const pageSize = Math.min(500, Math.max(1, Number.parseInt(requestUrl.searchParams.get("page_size") || "25", 10) || 25));
  const tier = requestUrl.searchParams.get("tier") || "all";
  const ageGroup = requestUrl.searchParams.get("age_group") || "all";
  const search = (requestUrl.searchParams.get("search") || "").trim().slice(0, 80);
  const query = new URLSearchParams({
    select: selectFields,
    order: "prob.desc,idx.asc",
    limit: String(pageSize),
    offset: String((page - 1) * pageSize),
  });

  if (tier === "high") query.set("prob", "gte.0.2");
  else if (tier === "moderate") query.set("and", "(prob.gte.0.12,prob.lt.0.2)");
  else if (tier === "low") query.set("prob", "lt.0.12");
  else if (tier !== "all") return json({ detail: "Invalid risk level" }, 400);

  if (ageGroup !== "all") query.set("age_group", `eq.${ageGroup}`);
  if (search) {
    const safeSearch = search.replace(/[*,%()]/g, "");
    if (safeSearch) query.set("enc_id", `ilike.*${safeSearch}*`);
  }

  const [{ rows, contentRange }, meta] = await Promise.all([
    databaseRows("demo_encounters", query),
    databaseRows("demo_governance", new URLSearchParams({ select: "summary", singleton: "eq.true", limit: "1" })),
  ]);
  const total = Number(contentRange?.split("/").at(-1)) || 0;
  const summary = meta.rows?.[0]?.summary || {};
  return json({
    results: rows,
    page,
    page_size: pageSize,
    total,
    pages: Math.max(1, Math.ceil(total / pageSize)),
    summary,
  });
}

async function predict(request: Request) {
  let input: Record<string, unknown>;
  try {
    input = await request.json();
  } catch {
    return json({ detail: "Request body must be valid JSON" }, 400);
  }

  const integerFields: Record<string, [number, number]> = {
    time_in_hospital: [1, 14],
    num_medications: [1, 50],
    number_inpatient: [0, 10],
    number_emergency: [0, 10],
  };
  if (typeof input.enc_id !== "string" || !/^ENC-\d+$/.test(input.enc_id)) {
    return json({ detail: "A valid demo encounter ID is required" }, 422);
  }
  for (const [field, [minimum, maximum]] of Object.entries(integerFields)) {
    const value = input[field];
    if (typeof value !== "number" || !Number.isInteger(value) || value < minimum || value > maximum) {
      return json({ detail: `${field} must be an integer between ${minimum} and ${maximum}` }, 422);
    }
  }
  if (typeof input.A1Cresult !== "string" || !a1cResults.has(input.A1Cresult)) {
    return json({ detail: "Invalid A1C result" }, 422);
  }
  if (typeof input.diag_1_cat !== "string" || !diagnosisCategories.has(input.diag_1_cat)) {
    return json({ detail: "Invalid diagnosis group" }, 422);
  }

  const modelUrl = getModelApiUrl();

  try {
    const modelResponse = await fetch(`${modelUrl}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      signal: AbortSignal.timeout(60_000),
    });
    const body = await modelResponse.text();
    return new Response(body, {
      status: modelResponse.status,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error) {
    return json({ detail: `Model scoring service is unavailable: ${(error as Error).message}` }, 502);
  }
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { status: 200, headers: corsHeaders });

  const requestUrl = new URL(request.url);
  const path = requestUrl.pathname.replace(/^\/functions\/v1\/clinicalai-api/, "") || "/";
  try {
    if (request.method === "GET" && path === "/api/health") {
      await databaseRows("demo_encounters", new URLSearchParams({ select: "idx", limit: "1" }));
      const modelUrl = getModelApiUrl();
      let modelOnline = false;
      try {
        const modelCheck = await fetch(`${modelUrl}/api/health`, {
          signal: AbortSignal.timeout(5000),
        });
        modelOnline = modelCheck.ok;
      } catch {
        modelOnline = false;
      }
      return json({
        status: "ok",
        service: "clinicalai-api",
        model: "calibrated ensemble",
        model_service: modelOnline ? "online" : "offline",
        model_url: modelUrl,
      });
    }
    if (request.method === "GET" && path === "/api/worklist") return await worklist(requestUrl);
    if (request.method === "GET" && path === "/api/governance") {
      const { rows } = await databaseRows("demo_governance", new URLSearchParams({
        select: "models,fairness,selected_model",
        singleton: "eq.true",
        limit: "1",
      }));
      return rows?.[0]
        ? json(rows[0])
        : json({ detail: "Governance data has not been loaded" }, 503);
    }
    const encounterMatch = request.method === "GET" && path.match(/^\/api\/encounters\/(ENC-\d+)$/);
    if (encounterMatch) {
      const { rows } = await databaseRows("demo_encounters", new URLSearchParams({
        select: selectFields,
        enc_id: `eq.${encounterMatch[1]}`,
        limit: "1",
      }));
      return rows?.[0] ? json({ encounter: rows[0] }) : json({ detail: "Encounter not found in the demo cohort" }, 404);
    }
    if (request.method === "POST" && path === "/api/predict") return await predict(request);
    return json({ detail: "Endpoint not found" }, 404);
  } catch (error) {
    console.error(error);
    return json({ detail: "The Supabase demo API could not complete this request" }, 500);
  }
});
