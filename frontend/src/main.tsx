import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import Landing from "./pages/Landing";
import DesignPreview from "./pages/DesignPreview";
import AppPlaceholder from "./pages/AppPlaceholder";
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/design" element={<DesignPreview />} />
        <Route path="/*" element={<AppPlaceholder />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
