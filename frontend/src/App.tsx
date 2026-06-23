import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { EventsPage } from "./pages/Events";
import { HistoryPage } from "./pages/History";
import { LogsPage } from "./pages/Logs";
import { OverviewPage } from "./pages/Overview";
import { ScreenerPage } from "./pages/Screener";
import { SignalsPage } from "./pages/Signals";
import { TradesPage } from "./pages/Trades";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<OverviewPage />} />
          <Route path="trades" element={<TradesPage />} />
          <Route path="signals" element={<SignalsPage />} />
          <Route path="screener" element={<ScreenerPage />} />
          <Route path="events" element={<EventsPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
