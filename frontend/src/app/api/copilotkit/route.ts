/**
 * Proxy API route that forwards CopilotKit requests to the Python backend.
 *
 * Uses COPILOTKIT_BACKEND_URL (server-side, runtime env var — NOT NEXT_PUBLIC_)
 * so it doesn't need to be present at build time.
 */

const BACKEND_URL =
  process.env.COPILOTKIT_BACKEND_URL || "http://localhost:8000";

export async function POST(request: Request) {
  const backendTarget = `${BACKEND_URL}/copilotkit`;

  // Forward all headers (including X-Model-Provider, X-Api-Key, etc.)
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    // Skip host and content-length (will be set by fetch)
    if (!["host", "content-length"].includes(key.toLowerCase())) {
      headers.set(key, value);
    }
  });

  const body = await request.text();

  const response = await fetch(backendTarget, {
    method: "POST",
    headers,
    body,
  });

  // Stream the response back (supports SSE from CopilotKit)
  return new Response(response.body, {
    status: response.status,
    headers: {
      "Content-Type":
        response.headers.get("Content-Type") || "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
