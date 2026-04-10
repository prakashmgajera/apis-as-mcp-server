"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { fetchConfigs, deleteConfig } from "@/lib/api";
import type { ApiEndpointConfig } from "@/types/api-config";
import type { ModelConfig } from "./ConfigPanel";

const ApiConfigBuilder = dynamic(
  () => import("@/components/ApiConfigBuilder"),
  { loading: () => <p className="p-8 text-gray-500">Loading form...</p> }
);

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-green-100 text-green-700",
  POST: "bg-blue-100 text-blue-700",
  PUT: "bg-yellow-100 text-yellow-700",
  PATCH: "bg-orange-100 text-orange-700",
  DELETE: "bg-red-100 text-red-700",
};

interface Props {
  onBack: () => void;
  config: ModelConfig;
}

export default function ApiConfigManager({ onBack, config }: Props) {
  const [configs, setConfigs] = useState<ApiEndpointConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showBuilder, setShowBuilder] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ApiEndpointConfig | null>(
    null
  );

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await fetchConfigs();
      setConfigs(data.configs);
    } catch {
      setError("Failed to load configs. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete API "${name}"? This cannot be undone.`)) return;
    try {
      await deleteConfig(id);
      await loadConfigs();
    } catch {
      setError("Failed to delete config");
    }
  };

  if (showBuilder || editingConfig) {
    return (
      <ApiConfigBuilder
        existingConfig={editingConfig}
        onSave={() => {
          setShowBuilder(false);
          setEditingConfig(null);
          loadConfigs();
        }}
        onCancel={() => {
          setShowBuilder(false);
          setEditingConfig(null);
        }}
      />
    );
  }

  const builtinConfigs = configs.filter((c) => c.source === "builtin");
  const userConfigs = configs.filter((c) => c.source === "user");

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onBack}
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
            <div>
              <h1 className="text-xl font-semibold text-gray-900">
                Manage API Configurations
              </h1>
              <p className="text-sm text-gray-500">
                Configure REST APIs as MCP tools
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowBuilder(true)}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            + Add New API
          </button>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-6">
        {loading ? (
          <p className="text-gray-500">Loading configurations...</p>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={loadConfigs}
              className="mt-2 text-sm text-red-600 hover:underline"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="space-y-8">
            {/* User APIs */}
            {userConfigs.length > 0 && (
              <section>
                <h2 className="text-lg font-medium text-gray-900 mb-3">
                  Your APIs ({userConfigs.length})
                </h2>
                <div className="grid gap-3">
                  {userConfigs.map((cfg) => (
                    <ConfigCard
                      key={cfg.id}
                      config={cfg}
                      onEdit={() => setEditingConfig(cfg)}
                      onDelete={() => handleDelete(cfg.id, cfg.name)}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* Built-in APIs */}
            <section>
              <h2 className="text-lg font-medium text-gray-900 mb-3">
                Built-in APIs ({builtinConfigs.length})
              </h2>
              <div className="grid gap-3">
                {builtinConfigs.map((cfg) => (
                  <ConfigCard key={cfg.id} config={cfg} />
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

function ConfigCard({
  config,
  onEdit,
  onDelete,
}: {
  config: ApiEndpointConfig;
  onEdit?: () => void;
  onDelete?: () => void;
}) {
  const methodColor =
    METHOD_COLORS[config.method] || "bg-gray-100 text-gray-700";

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={`px-2 py-0.5 text-xs font-mono font-semibold rounded ${methodColor}`}
          >
            {config.method}
          </span>
          <span className="font-medium text-gray-900 truncate">
            {config.name}
          </span>
          {config.source === "builtin" && (
            <span className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-500 rounded">
              built-in
            </span>
          )}
          {config.group_name && (
            <span className="px-1.5 py-0.5 text-xs bg-purple-50 text-purple-600 rounded">
              {config.group_name}
            </span>
          )}
        </div>
        {config.source === "user" && (
          <div className="flex items-center gap-1 ml-2">
            {onEdit && (
              <button
                onClick={onEdit}
                className="px-2 py-1 text-xs text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
              >
                Edit
              </button>
            )}
            {onDelete && (
              <button
                onClick={onDelete}
                className="px-2 py-1 text-xs text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
              >
                Delete
              </button>
            )}
          </div>
        )}
      </div>
      <p className="text-sm text-gray-600 mt-1">{config.description}</p>
      <p className="text-xs text-gray-400 mt-1 font-mono">
        {config.base_url}
        {config.path}
      </p>
    </div>
  );
}
