"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import type { ModelConfig } from "./ConfigPanel";

interface Props {
  config: ModelConfig;
  onReset: () => void;
}

export default function ChatAgent({ config, onReset }: Props) {
  const runtimeUrl =
    process.env.NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL ||
    "http://localhost:8000/copilotkit";

  return (
    <CopilotKit
      runtimeUrl={runtimeUrl}
      agent="api_agent"
      headers={{
        "X-Model-Provider": config.provider,
        "X-Model-Name": config.modelName,
        "X-Api-Key": config.apiKey,
      }}
    >
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
          <button
            onClick={onReset}
            className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Change Model
          </button>
        </header>

        {/* Chat Area */}
        <main className="flex-1 overflow-hidden">
          <CopilotChat
            className="h-full"
            instructions="You are a helpful assistant that interacts with REST APIs on behalf of the user. Present information clearly and ask for confirmation before making changes."
            labels={{
              title: "API Assistant",
              initial:
                "Hi! I can help you interact with your configured REST APIs. Try asking me to list posts, get user details, create content, or any other operation your APIs support.",
              placeholder: "Ask me to call an API...",
            }}
          />
        </main>
      </div>
    </CopilotKit>
  );
}
