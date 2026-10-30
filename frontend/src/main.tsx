import React, { lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";
import { Skeleton } from "./components/ui/Skeleton";

// Public
const Landing       = lazy(() => import("./pages/Landing"));
const DesignPreview = lazy(() => import("./pages/DesignPreview"));
// App
const Dashboard      = lazy(() => import("./pages/Dashboard"));
const Inventory      = lazy(() => import("./pages/Inventory"));
const InventoryDetail = lazy(() => import("./pages/InventoryDetail"));
const Alerts         = lazy(() => import("./pages/Alerts"));
const AlertDetail    = lazy(() => import("./pages/AlertDetail"));
const Matches        = lazy(() => import("./pages/Matches"));
const MatchDetail    = lazy(() => import("./pages/MatchDetail"));
const Activity       = lazy(() => import("./pages/Activity"));
const NotFound       = lazy(() => import("./pages/NotFound"));

function PageShell() {
  return <div className="flex h-screen items-center justify-center"><Skeleton className="h-10 w-48" /></div>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={<PageShell />}>
          <Routes>
            <Route path="/"                    element={<Landing />} />
            <Route path="/design"              element={<DesignPreview />} />
            <Route path="/dashboard"           element={<Dashboard />} />
            <Route path="/inventory"           element={<Inventory />} />
            <Route path="/inventory/:id"       element={<InventoryDetail />} />
            <Route path="/alerts"              element={<Alerts />} />
            <Route path="/alerts/:id"          element={<AlertDetail />} />
            <Route path="/matches"             element={<Matches />} />
            <Route path="/matches/:id"         element={<MatchDetail />} />
            <Route path="/activity"            element={<Activity />} />
            <Route path="*"                    element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
);
