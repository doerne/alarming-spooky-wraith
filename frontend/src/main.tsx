import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/app/app";
import { Providers } from "@/app/providers";
import { applyInitialTheme } from "@/shared/hooks/use-theme";

import "./index.css";

applyInitialTheme();

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Element #root fehlt in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <Providers>
      <App />
    </Providers>
  </StrictMode>,
);
