const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readError(response, fallback) {
  const body = await response.json().catch(() => ({}));
  const detail = body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const text = detail.map((item) => item.msg || item.message).filter(Boolean).join(" ");
    if (text) return text;
  }
  return fallback;
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch {
    throw new ApiError(0, "The API could not be reached. Start the backend on port 8000 and allow this frontend origin in CORS.");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response, `Request failed: ${response.status}`));
  }
  return response.json();
}

export function getHealth() {
  return request("/api/v1/health");
}

export function getTargets(planet) {
  const query = planet ? `?planet=${encodeURIComponent(planet)}` : "";
  return request(`/api/v1/targets${query}`);
}

export function getTarget(siteId, planet) {
  return request(`/api/v1/targets/${encodeURIComponent(siteId)}?planet=${encodeURIComponent(planet)}`);
}

export function searchAnalogs(payload) {
  return request("/api/v1/analogs/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
