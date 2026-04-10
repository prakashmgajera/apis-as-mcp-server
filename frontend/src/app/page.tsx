"use client";

import { useState } from "react";
import ConfigPanel, { type ModelConfig } from "@/components/ConfigPanel";
import ChatAgent from "@/components/ChatAgent";

type View = "config" | "chat" | "manage";

export default function Home() {
  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [view, setView] = useState<View>("config");

  if (!config || view === "config") {
    return (
      <ConfigPanel
        onSubmit={(c) => {
          setConfig(c);
          setView("chat");
        }}
      />
    );
  }

  if (view === "manage") {
    // Lazy-load the ApiConfigManager (will be created in Step 6)
    const ApiConfigManager =
      require("@/components/ApiConfigManager").default;
    return (
      <ApiConfigManager onBack={() => setView("chat")} config={config} />
    );
  }

  return (
    <ChatAgent
      config={config}
      onReset={() => {
        setConfig(null);
        setView("config");
      }}
      onManageApis={() => setView("manage")}
    />
  );
}
