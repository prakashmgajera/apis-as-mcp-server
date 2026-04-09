/**
 * Catch-all proxy route for CopilotKit sub-paths (e.g. /info, /action).
 *
 * Forwards /api/copilotkit/<anything> → BACKEND/copilotkit/<anything>
 */

const BACKEND_URL =
  process.env.COPILOTKIT_BACKEND_URL || "http://localhost:8000";

async function proxyRequest(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const subPath = path.join("/");
  const backendTarget = `${BACKEND_URL}/copilotkit/${subPath}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!["host", "content-length"].includes(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const body = request.method !== "GET" ? await request.text() : undefined;

  const response = await fetch(backendTarget, {
    method: request.method,
    headers,
    body,
  });

  return new Response(response.body, {
    status: response.status,
    headers: {
      "Content-Type":
        response.headers.get("Content-Type") || "application/json",
      "Cache-Control": "no-cache",
    },
  });
}

export const GET = proxyRequest;
export const POST = proxyRequest;
