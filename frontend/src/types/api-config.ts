export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
export type ParameterLocation = "query" | "path" | "header" | "body";
export type AuthType = "none" | "bearer" | "api_key" | "basic";
export type ConfigSource = "builtin" | "user";

export interface ApiParameter {
  name: string;
  description: string;
  type: string;
  required: boolean;
  location: ParameterLocation;
  default?: unknown;
}

export interface AuthConfig {
  type: AuthType;
  token_env_var?: string | null;
  header_name: string;
  prefix: string;
}

export interface ApiEndpointConfig {
  id: string;
  name: string;
  description: string;
  base_url: string;
  path: string;
  method: HttpMethod;
  parameters: ApiParameter[];
  headers: Record<string, string>;
  auth: AuthConfig;
  timeout: number;
  response_template?: string | null;
  source: ConfigSource;
  group_name?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ToolSummary {
  name: string;
  description: string;
}

export interface ToolsResponse {
  tools: ToolSummary[];
  count: number;
}

export interface ConfigsResponse {
  configs: ApiEndpointConfig[];
  builtin_count: number;
  user_count: number;
}
