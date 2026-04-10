"use client";

import { useEffect, useState } from "react";
import { fetchTools } from "@/lib/api";
import type { ToolSummary } from "@/types/api-config";

const METHOD_COLORS: Record<string, string> = {
  GET: "bg-green-100 text-green-700",
  POST: "bg-blue-100 text-blue-700",
  PUT: "bg-yellow-100 text-yellow-700",
  PATCH: "bg-orange-100 text-orange-700",
  DELETE: "bg-red-100 text-red-700",
};

interface Props {
  selectedTools: Set<string>;
  onSelectionChange: (tools: Set<string>) => void;
}

export default function ToolSelector({
  selectedTools,
  onSelectionChange,
}: Props) {
  const [tools, setTools] = useState<ToolSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    loadTools();
  }, []);

  const loadTools = async () => {
    try {
      setLoading(true);
      const data = await fetchTools();
      setTools(data.tools);
      // Select all tools by default
      if (selectedTools.size === 0 && data.tools.length > 0) {
        onSelectionChange(new Set(data.tools.map((t) => t.name)));
      }
    } catch (e) {
      setError("Failed to load tools. Is the MCP server running?");
    } finally {
      setLoading(false);
    }
  };

  const toggleTool = (name: string) => {
    const next = new Set(selectedTools);
    if (next.has(name)) {
      next.delete(name);
    } else {
      next.add(name);
    }
    onSelectionChange(next);
  };

  const selectAll = () => {
    onSelectionChange(new Set(tools.map((t) => t.name)));
  };

  const deselectAll = () => {
    onSelectionChange(new Set());
  };

  const filtered = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="p-4 text-sm text-gray-500">Loading tools...</div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <p className="text-sm text-red-600 mb-2">{error}</p>
        <button
          onClick={loadTools}
          className="text-sm text-blue-600 hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-900">
            MCP Tools
          </h3>
          <span className="text-xs text-gray-500">
            {selectedTools.size}/{tools.length}
          </span>
        </div>

        {/* Search */}
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tools..."
          className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none"
        />

        {/* Quick actions */}
        <div className="flex gap-2 mt-2">
          <button
            onClick={selectAll}
            className="text-xs text-blue-600 hover:underline"
          >
            Select all
          </button>
          <button
            onClick={deselectAll}
            className="text-xs text-blue-600 hover:underline"
          >
            Deselect all
          </button>
        </div>
      </div>

      {/* Tool list */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <p className="p-3 text-sm text-gray-500">No tools found</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {filtered.map((tool) => (
              <label
                key={tool.name}
                className="flex items-start gap-2 p-3 hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedTools.has(tool.name)}
                  onChange={() => toggleTool(tool.name)}
                  className="mt-0.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {tool.name}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                    {tool.description}
                  </p>
                </div>
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
