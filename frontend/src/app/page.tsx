"use client";

import { useState } from "react";
import ConfigPanel, { type ModelConfig } from "@/components/ConfigPanel";
import ChatAgent from "@/components/ChatAgent";

export default function Home() {
  const [config, setConfig] = useState<ModelConfig | null>(null);

  if (!config) {
    return <ConfigPanel onSubmit={setConfig} />;
  }

  return <ChatAgent config={config} onReset={() => setConfig(null)} />;
}
