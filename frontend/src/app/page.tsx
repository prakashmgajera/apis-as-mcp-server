"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import ConfigPanel, { type ModelConfig } from "@/components/ConfigPanel";
import ChatAgent from "@/components/ChatAgent";

const ApiConfigManager = dynamic(
  () => import("@/components/ApiConfigManager"),
  { loading: () => <p className="p-8 text-gray-500">Loading...</p> }
);

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
