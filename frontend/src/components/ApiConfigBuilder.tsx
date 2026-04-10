"use client";

import { useState } from "react";
import { createConfig, updateConfig } from "@/lib/api";
import type {
  ApiEndpointConfig,
  ApiParameter,
  AuthType,
  HttpMethod,
  ParameterLocation,
} from "@/types/api-config";

const HTTP_METHODS: HttpMethod[] = ["GET", "POST", "PUT", "PATCH", "DELETE"];
const PARAM_TYPES = ["string", "integer", "number", "boolean", "object", "array"];
const PARAM_LOCATIONS: ParameterLocation[] = ["query", "path", "header", "body"];
const AUTH_TYPES: { value: AuthType; label: string }[] = [
  { value: "none", label: "None" },
  { value: "bearer", label: "Bearer Token" },
  { value: "api_key", label: "API Key" },
  { value: "basic", label: "Basic Auth" },
];

interface Props {
  existingConfig?: ApiEndpointConfig | null;
  onSave: () => void;
  onCancel: () => void;
}

const emptyParam = (): ApiParameter => ({
  name: "",
  description: "",
  type: "string",
  required: false,
  location: "query",
});

export default function ApiConfigBuilder({
  existingConfig,
  onSave,
  onCancel,
}: Props) {
  const isEditing = !!existingConfig;

  const [name, setName] = useState(existingConfig?.name || "");
  const [description, setDescription] = useState(
    existingConfig?.description || ""
  );
  const [baseUrl, setBaseUrl] = useState(existingConfig?.base_url || "");
  const [path, setPath] = useState(existingConfig?.path || "/");
  const [method, setMethod] = useState<HttpMethod>(
    existingConfig?.method || "GET"
  );
  const [parameters, setParameters] = useState<ApiParameter[]>(
    existingConfig?.parameters || []
  );
  const [authType, setAuthType] = useState<AuthType>(
    existingConfig?.auth?.type || "none"
  );
  const [tokenEnvVar, setTokenEnvVar] = useState(
    existingConfig?.auth?.token_env_var || ""
  );
  const [headerName, setHeaderName] = useState(
    existingConfig?.auth?.header_name || "Authorization"
  );
  const [authPrefix, setAuthPrefix] = useState(
    existingConfig?.auth?.prefix || "Bearer"
  );
  const [timeout, setTimeout_] = useState(existingConfig?.timeout || 30);
  const [groupName, setGroupName] = useState(
    existingConfig?.group_name || "User APIs"
  );
  const [responseTemplate, setResponseTemplate] = useState(
    existingConfig?.response_template || ""
  );
  const [customHeaders, setCustomHeaders] = useState<
    { key: string; value: string }[]
  >(
    existingConfig?.headers
      ? Object.entries(existingConfig.headers).map(([key, value]) => ({
          key,
          value,
        }))
      : []
  );

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const addParameter = () => {
    setParameters([...parameters, emptyParam()]);
  };

  const removeParameter = (index: number) => {
    setParameters(parameters.filter((_, i) => i !== index));
  };

  const updateParameter = (
    index: number,
    field: keyof ApiParameter,
    value: unknown
  ) => {
    const updated = [...parameters];
    updated[index] = { ...updated[index], [field]: value };
    setParameters(updated);
  };

  const addHeader = () => {
    setCustomHeaders([...customHeaders, { key: "", value: "" }]);
  };

  const removeHeader = (index: number) => {
    setCustomHeaders(customHeaders.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    setError("");

    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) {
      setError(
        "Name must start with a letter or underscore and contain only letters, numbers, and underscores"
      );
      return;
    }
    if (!description.trim()) {
      setError("Description is required");
      return;
    }
    if (!baseUrl.trim()) {
      setError("Base URL is required");
      return;
    }

    const headersObj: Record<string, string> = {};
    for (const h of customHeaders) {
      if (h.key.trim()) {
        headersObj[h.key.trim()] = h.value;
      }
    }

    const configData = {
      name: name.trim(),
      description: description.trim(),
      base_url: baseUrl.trim(),
      path: path.trim() || "/",
      method,
      parameters: parameters.filter((p) => p.name.trim()),
      headers: headersObj,
      auth: {
        type: authType,
        token_env_var: tokenEnvVar || null,
        header_name: headerName,
        prefix: authPrefix,
      },
      timeout,
      response_template: responseTemplate || null,
      group_name: groupName.trim() || "User APIs",
    };

    try {
      setSaving(true);
      if (isEditing && existingConfig) {
        await updateConfig(existingConfig.id, configData as ApiEndpointConfig);
      } else {
        await createConfig(configData as ApiEndpointConfig);
      }
      onSave();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to save";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onCancel}
              className="text-gray-500 hover:text-gray-700"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            <h1 className="text-xl font-semibold text-gray-900">
              {isEditing ? "Edit API" : "Add New API"}
            </h1>
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : isEditing ? "Update" : "Create"}
          </button>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Basic Info */}
        <Section title="Basic Info">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Tool Name" required>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. get_weather"
                className="input"
                disabled={isEditing}
              />
            </Field>
            <Field label="Group Name">
              <input
                type="text"
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="User APIs"
                className="input"
              />
            </Field>
          </div>
          <Field label="Description" required>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this API does..."
              className="input"
              rows={2}
            />
          </Field>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Method">
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value as HttpMethod)}
                className="input"
              >
                {HTTP_METHODS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Base URL" required>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.example.com"
                className="input"
              />
            </Field>
            <Field label="Path" required>
              <input
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="/users/{id}"
                className="input"
              />
            </Field>
          </div>
        </Section>

        {/* Parameters */}
        <Section
          title="Parameters"
          action={
            <button
              onClick={addParameter}
              className="text-sm text-blue-600 hover:underline"
            >
              + Add parameter
            </button>
          }
        >
          {parameters.length === 0 ? (
            <p className="text-sm text-gray-500">
              No parameters. Click &quot;Add parameter&quot; to define one.
            </p>
          ) : (
            <div className="space-y-3">
              {parameters.map((param, i) => (
                <div
                  key={i}
                  className="border border-gray-200 rounded-lg p-3 bg-gray-50"
                >
                  <div className="grid grid-cols-4 gap-3">
                    <input
                      type="text"
                      value={param.name}
                      onChange={(e) =>
                        updateParameter(i, "name", e.target.value)
                      }
                      placeholder="name"
                      className="input text-sm"
                    />
                    <select
                      value={param.type}
                      onChange={(e) =>
                        updateParameter(i, "type", e.target.value)
                      }
                      className="input text-sm"
                    >
                      {PARAM_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                    <select
                      value={param.location}
                      onChange={(e) =>
                        updateParameter(
                          i,
                          "location",
                          e.target.value as ParameterLocation
                        )
                      }
                      className="input text-sm"
                    >
                      {PARAM_LOCATIONS.map((l) => (
                        <option key={l} value={l}>
                          {l}
                        </option>
                      ))}
                    </select>
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-1 text-sm">
                        <input
                          type="checkbox"
                          checked={param.required}
                          onChange={(e) =>
                            updateParameter(i, "required", e.target.checked)
                          }
                          className="rounded border-gray-300"
                        />
                        Required
                      </label>
                      <button
                        onClick={() => removeParameter(i)}
                        className="ml-auto text-red-500 hover:text-red-700 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                  <input
                    type="text"
                    value={param.description}
                    onChange={(e) =>
                      updateParameter(i, "description", e.target.value)
                    }
                    placeholder="Parameter description..."
                    className="input text-sm mt-2"
                  />
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Authentication */}
        <Section title="Authentication">
          <Field label="Auth Type">
            <select
              value={authType}
              onChange={(e) => setAuthType(e.target.value as AuthType)}
              className="input"
            >
              {AUTH_TYPES.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </Field>
          {authType !== "none" && (
            <div className="grid grid-cols-2 gap-4">
              <Field label="Token Environment Variable">
                <input
                  type="text"
                  value={tokenEnvVar}
                  onChange={(e) => setTokenEnvVar(e.target.value)}
                  placeholder="e.g. API_TOKEN"
                  className="input"
                />
              </Field>
              {authType === "api_key" && (
                <Field label="Header Name">
                  <input
                    type="text"
                    value={headerName}
                    onChange={(e) => setHeaderName(e.target.value)}
                    placeholder="X-API-Key"
                    className="input"
                  />
                </Field>
              )}
              {authType === "bearer" && (
                <Field label="Prefix">
                  <input
                    type="text"
                    value={authPrefix}
                    onChange={(e) => setAuthPrefix(e.target.value)}
                    placeholder="Bearer"
                    className="input"
                  />
                </Field>
              )}
            </div>
          )}
        </Section>

        {/* Advanced */}
        <Section
          title="Advanced"
          action={
            <button
              onClick={addHeader}
              className="text-sm text-blue-600 hover:underline"
            >
              + Add header
            </button>
          }
        >
          <div className="grid grid-cols-2 gap-4">
            <Field label="Timeout (seconds)">
              <input
                type="number"
                value={timeout}
                onChange={(e) => setTimeout_(parseInt(e.target.value) || 30)}
                min={1}
                max={300}
                className="input"
              />
            </Field>
          </div>

          {customHeaders.length > 0 && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Custom Headers
              </label>
              {customHeaders.map((h, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="text"
                    value={h.key}
                    onChange={(e) => {
                      const updated = [...customHeaders];
                      updated[i] = { ...updated[i], key: e.target.value };
                      setCustomHeaders(updated);
                    }}
                    placeholder="Header name"
                    className="input flex-1 text-sm"
                  />
                  <input
                    type="text"
                    value={h.value}
                    onChange={(e) => {
                      const updated = [...customHeaders];
                      updated[i] = { ...updated[i], value: e.target.value };
                      setCustomHeaders(updated);
                    }}
                    placeholder="Value"
                    className="input flex-1 text-sm"
                  />
                  <button
                    onClick={() => removeHeader(i)}
                    className="text-red-500 hover:text-red-700 text-sm px-2"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}

          <Field label="Response Template (Jinja2, optional)">
            <textarea
              value={responseTemplate}
              onChange={(e) => setResponseTemplate(e.target.value)}
              placeholder="Optional Jinja2 template to format the response..."
              className="input font-mono text-sm"
              rows={3}
            />
          </Field>
        </Section>
      </div>
    </div>
  );
}

function Section({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-900">{title}</h2>
        {action}
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}
