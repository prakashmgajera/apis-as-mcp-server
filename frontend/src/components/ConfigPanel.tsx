"use client";

import { useState } from "react";

const PROVIDERS = [
  {
    id: "openai",
    name: "OpenAI",
    defaultModel: "gpt-4o",
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    placeholder: "sk-...",
  },
  {
    id: "anthropic",
    name: "Anthropic",
    defaultModel: "claude-sonnet-4-20250514",
    models: [
      "claude-sonnet-4-20250514",
      "claude-haiku-4-20250414",
    ],
    placeholder: "sk-ant-...",
  },
  {
    id: "google",
    name: "Google",
    defaultModel: "gemini-2.0-flash",
    models: ["gemini-2.0-flash", "gemini-2.5-pro"],
    placeholder: "AI...",
  },
];

export interface ModelConfig {
  provider: string;
  modelName: string;
  apiKey: string;
}

interface Props {
  onSubmit: (config: ModelConfig) => void;
}

export default function ConfigPanel({ onSubmit }: Props) {
  const [selectedProvider, setSelectedProvider] = useState(PROVIDERS[0]);
  const [modelName, setModelName] = useState(PROVIDERS[0].defaultModel);
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");

  const handleProviderChange = (id: string) => {
    const provider = PROVIDERS.find((p) => p.id === id)!;
    setSelectedProvider(provider);
    setModelName(provider.defaultModel);
    setError("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      setError("API key is required");
      return;
    }
    onSubmit({
      provider: selectedProvider.id,
      modelName,
      apiKey: apiKey.trim(),
    });
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">API</span>
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              APIs as MCP Server
            </h1>
            <p className="text-sm text-gray-500">
              Configure your model to start chatting
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Provider */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Model Provider
            </label>
            <select
              value={selectedProvider.id}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Model Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Model
            </label>
            <select
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            >
              {selectedProvider.models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => {
                setApiKey(e.target.value);
                setError("");
              }}
              placeholder={selectedProvider.placeholder}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
            {error && (
              <p className="mt-1.5 text-sm text-red-600">{error}</p>
            )}
            <p className="mt-1.5 text-xs text-gray-400">
              Your key is only held in memory for this session and is never
              stored.
            </p>
          </div>

          {/* Submit */}
          <button
            type="submit"
            className="w-full py-2.5 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            Start Chatting
          </button>
        </form>
      </div>
    </div>
  );
}
