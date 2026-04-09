/**
 * Catch-all proxy: forwards /api/copilotkit/<path> → BACKEND/copilotkit/<path>
 *
 * Handles CopilotKit sub-endpoints like /info, /action, etc.
 */

const BACKEND_URL =
  process.env.COPILOTKIT_BACKEND_URL || "http://localhost:8000";

const HOP_BY_HOP = new Set([
  "host",
  "content-length",
  "connection",
  "transfer-encoding",
]);

async function proxyRequest(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const subPath = path.join("/");
  const backendTarget = `${BACKEND_URL}/copilotkit/${subPath}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const body = request.method !== "GET" ? await request.text() : undefined;

  try {
    const response = await fetch(backendTarget, {
      method: request.method,
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
    responseHeaders.set("Cache-Control", "no-cache");

    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error(`Proxy error for /copilotkit/${subPath}:`, error);
    return new Response(
      JSON.stringify({ error: "Failed to reach backend server" }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
