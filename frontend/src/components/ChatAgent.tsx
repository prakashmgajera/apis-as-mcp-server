"use client";

import { useState, useMemo, useEffect } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { fetchTools } from "@/lib/api";
import type { ModelConfig } from "./ConfigPanel";
import ToolSelector from "./ToolSelector";

interface Props {
  config: ModelConfig;
  onReset: () => void;
  onManageApis: () => void;
}

export default function ChatAgent({ config, onReset, onManageApis }: Props) {
  const runtimeUrl = "/api/copilotkit";
  const [selectedTools, setSelectedTools] = useState<Set<string>>(new Set());
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Auto-load and select all tools on mount so the user can chat immediately
  useEffect(() => {
    fetchTools()
      .then((data) => {
        if (data.tools.length > 0) {
          setSelectedTools(new Set(data.tools.map((t) => t.name)));
        }
      })
      .catch(() => {
        // ToolSelector will show an error when sidebar is opened
      });
  }, []);

  const headers = useMemo(
    () => ({
      "X-Model-Provider": config.provider,
      "X-Model-Name": config.modelName,
      "X-Api-Key": config.apiKey,
      ...(selectedTools.size > 0
        ? { "X-Selected-Tools": Array.from(selectedTools).join(",") }
        : {}),
    }),
    [config, selectedTools]
  );

  return (
    <CopilotKit runtimeUrl={runtimeUrl} agent="api_agent" headers={headers}>
      <div className="flex flex-col h-screen">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">API</span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">
                APIs as MCP Server
              </h1>
              <p className="text-xs text-gray-500">
                {config.provider} / {config.modelName}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className={`px-3 py-1.5 text-sm border rounded-lg transition-colors ${
                sidebarOpen
                  ? "bg-blue-50 text-blue-700 border-blue-300"
                  : "text-gray-600 border-gray-300 hover:bg-gray-50"
              }`}
            >
              Tools ({selectedTools.size})
            </button>
            <button
              onClick={onManageApis}
              className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Manage APIs
            </button>
            <button
              onClick={onReset}
              className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Change Model
            </button>
          </div>
        </header>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Tool Selector Sidebar */}
          {sidebarOpen && (
            <aside className="w-72 border-r border-gray-200 bg-white flex-shrink-0">
              <ToolSelector
                selectedTools={selectedTools}
                onSelectionChange={setSelectedTools}
              />
            </aside>
          )}

          {/* Chat Area */}
          <main className="flex-1 overflow-hidden">
            {selectedTools.size === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center p-8">
                  <div className="w-12 h-12 rounded-full bg-yellow-100 flex items-center justify-center mx-auto mb-3">
                    <span className="text-yellow-600 text-xl">!</span>
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-1">
                    No tools selected
                  </h3>
                  <p className="text-sm text-gray-500 mb-4">
                    Select at least one tool from the sidebar to start chatting.
                  </p>
                  <button
                    onClick={() => setSidebarOpen(true)}
                    className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Open Tool Selector
                  </button>
                </div>
              </div>
            ) : (
              <CopilotChat
                className="h-full"
                instructions="You are a helpful assistant that interacts with REST APIs on behalf of the user. Present information clearly and ask for confirmation before making changes."
                labels={{
                  title: "API Assistant",
                  initial: `Hi! I can help you interact with your configured REST APIs. I have access to ${selectedTools.size} tool(s). Try asking me to list posts, get user details, create content, or any other operation your APIs support.`,
                  placeholder: "Ask me to call an API...",
                }}
              />
            )}
          </main>
        </div>
      </div>
    </CopilotKit>
  );
}
