/**
 * Proxy route: forwards POST /api/copilotkit → BACKEND/copilotkit
 *
 * Uses COPILOTKIT_BACKEND_URL (server-side runtime env var) so it
 * doesn't need to be present at build time.
 */

const BACKEND_URL =
  process.env.COPILOTKIT_BACKEND_URL || "http://localhost:8000";

// Headers that should NOT be forwarded to the backend
const HOP_BY_HOP = new Set([
  "host",
  "content-length",
  "connection",
  "transfer-encoding",
]);

export async function POST(request: Request) {
  const backendTarget = `${BACKEND_URL}/copilotkit`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const body = await request.text();

  try {
    const response = await fetch(backendTarget, {
      method: "POST",
      headers,
      body,
    });

    // Forward all response headers from the backend
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      if (!HOP_BY_HOP.has(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });
    // Ensure streaming works
    responseHeaders.set("Cache-Control", "no-cache");

    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("Proxy error:", error);
    return new Response(
      JSON.stringify({ error: "Failed to reach backend server" }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}
