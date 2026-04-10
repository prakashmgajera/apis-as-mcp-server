import type {
  ApiEndpointConfig,
  ConfigsResponse,
  ToolsResponse,
} from "@/types/api-config";

const API_BASE = "/api/backend";

export async function fetchTools(): Promise<ToolsResponse> {
  const res = await fetch(`${API_BASE}/tools`);
  if (!res.ok) throw new Error("Failed to fetch tools");
  return res.json();
}

export async function fetchConfigs(): Promise<ConfigsResponse> {
  const res = await fetch(`${API_BASE}/configs`);
  if (!res.ok) throw new Error("Failed to fetch configs");
  return res.json();
}

export async function fetchConfig(id: string): Promise<ApiEndpointConfig> {
  const res = await fetch(`${API_BASE}/configs/${id}`);
  if (!res.ok) throw new Error("Failed to fetch config");
  return res.json();
}

export async function createConfig(
  config: Omit<ApiEndpointConfig, "id" | "source" | "created_at" | "updated_at">
): Promise<ApiEndpointConfig> {
  const res = await fetch(`${API_BASE}/configs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create config");
  }
  return res.json();
}

export async function updateConfig(
  id: string,
  config: Omit<ApiEndpointConfig, "id" | "source" | "created_at" | "updated_at">
): Promise<ApiEndpointConfig> {
  const res = await fetch(`${API_BASE}/configs/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update config");
  }
  return res.json();
}

export async function deleteConfig(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/configs/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete config");
  }
}
