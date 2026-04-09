import type { Metadata } from "next";
import { CopilotKit } from "@copilotkit/react-core";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

export const metadata: Metadata = {
  title: "APIs as MCP Server",
  description:
    "Chat with your REST APIs using CopilotKit and MCP tools",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const runtimeUrl =
    process.env.NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL ||
    "http://localhost:8000/copilotkit";

  return (
    <html lang="en">
      <body>
        <CopilotKit runtimeUrl={runtimeUrl} agent="api_agent">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
