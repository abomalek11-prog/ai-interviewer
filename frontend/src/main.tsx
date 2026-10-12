import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { API_BASE_URL } from "./api/client";
import App from "./App";
import "./index.css";

// The API host's free tier sleeps after 15 idle minutes and needs ~a minute to wake. Start
// waking it the moment the site opens, so it is up by the time an interview begins.
void fetch(`${API_BASE_URL.replace(/\/api\/v1\/?$/, "")}/health`).catch(() => {});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
