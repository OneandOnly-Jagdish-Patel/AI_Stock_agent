import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, clearAdminKey, getAdminKey, setAdminKey } from "../api/client";

type SettingsSnapshot = Record<string, unknown>;

export function AdminPage() {
  const [keyInput, setKeyInput] = useState("");
  const [authed, setAuthed] = useState(!!getAdminKey());
  const [settings, setSettings] = useState<SettingsSnapshot | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [newAnchor, setNewAnchor] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const s = await api.adminSettings();
      setSettings(s);
      setAuthed(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load settings");
      if (String(e).includes("401")) {
        clearAdminKey();
        setAuthed(false);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authed) load();
  }, [authed, load]);

  const onLogin = (e: FormEvent) => {
    e.preventDefault();
    setAdminKey(keyInput.trim());
    setAuthed(true);
  };

  const onLogout = () => {
    clearAdminKey();
    setAuthed(false);
    setSettings(null);
  };

  const saveField = async (updates: Record<string, unknown>) => {
    setMessage("");
    setError("");
    try {
      const res = await api.adminUpdateSettings(updates);
      setSettings(res.settings);
      setMessage(`Saved: ${res.applied?.join(", ") ?? "ok"}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  };

  const addAnchor = async () => {
    if (!newAnchor.trim()) return;
    setMessage("");
    setError("");
    try {
      await api.adminAddAnchor(newAnchor.trim());
      setNewAnchor("");
      setMessage("Added anchor symbol");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Add anchor failed");
    }
  };

  const removeAnchor = async (symbol: string) => {
    setMessage("");
    setError("");
    try {
      await api.adminRemoveAnchor(symbol);
      setMessage(`Removed ${symbol} from anchors`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Remove failed");
    }
  };

  if (!authed) {
    return (
      <>
        <div className="page-header">
          <h2>Admin</h2>
        </div>
        <div className="panel" style={{ maxWidth: 420 }}>
          <div className="panel-header">Sign in</div>
          <div className="panel-body">
            <p style={{ marginBottom: "1rem", color: "var(--text-muted)" }}>
              Enter the <code>ADMIN_API_KEY</code> from your server <code>.env</code>.
            </p>
            <form onSubmit={onLogin}>
              <div className="form-field">
                <label htmlFor="admin-key">Admin API key</label>
                <input
                  id="admin-key"
                  type="password"
                  placeholder="Admin API key"
                  value={keyInput}
                  onChange={(e) => setKeyInput(e.target.value)}
                />
              </div>
              <button type="submit" className="refresh-btn">
                Continue
              </button>
            </form>
            {error && <div className="error" style={{ marginTop: "0.75rem" }}>{error}</div>}
          </div>
        </div>
      </>
    );
  }

  const anchors = (settings?.["screener.anchor_symbols"] as string[]) ?? [];

  return (
    <>
      <div className="page-header">
        <h2>Admin Settings</h2>
        <div className="page-header-actions">
          <button type="button" className="refresh-btn" onClick={load}>
            Reload
          </button>
          <button
            type="button"
            className="refresh-btn refresh-btn--secondary"
            onClick={onLogout}
          >
            Log out
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {message && <div className="success-banner">{message}</div>}
      {loading && !settings && <div className="loading">Loading settings…</div>}

      {settings && (
        <>
          <div className="panel">
            <div className="panel-header">Anchor symbols (always on watchlist)</div>
            <div className="panel-body">
              <p style={{ color: "var(--text-muted)", marginBottom: "0.75rem" }}>
                Anchors are traded every day. Dynamic screener picks fill the remaining slots.
              </p>
              <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
                {anchors.map((sym) => (
                  <span key={sym} className="badge badge-anchor anchor-chip">
                    {sym}
                    <button
                      type="button"
                      onClick={() => removeAnchor(sym)}
                      aria-label={`Remove ${sym}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
                {anchors.length === 0 && <span className="empty">No anchors</span>}
              </div>
              <div className="form-field-row">
                <input
                  placeholder="e.g. NVDA"
                  value={newAnchor}
                  onChange={(e) => setNewAnchor(e.target.value.toUpperCase())}
                  maxLength={6}
                  aria-label="New anchor symbol"
                />
                <button type="button" className="refresh-btn" onClick={addAnchor}>
                  Add anchor
                </button>
              </div>
            </div>
          </div>

          <div className="grid-2">
            <AdminSection
              title="Strategy & screener"
              settings={settings}
              onSave={saveField}
              fields={[
                { key: "strategy.mode", label: "Strategy mode", type: "select", options: ["swing", "scalper"] },
                { key: "screener.mode", label: "Screener mode", type: "select", options: ["hybrid", "dynamic", "static"] },
                { key: "screener.dynamic_slots", label: "Dynamic slots", type: "number", min: 1, max: 10 },
                { key: "screener.candidate_pool_size", label: "Candidate pool size", type: "number", min: 10, max: 100 },
                { key: "screener.run_time", label: "Screener run time (CST)", type: "text" },
              ]}
            />
            <AdminSection
              title="Swing & risk"
              settings={settings}
              onSave={saveField}
              fields={[
                { key: "swing.take_profit_pct", label: "Swing take profit %", type: "number", step: 0.1 },
                { key: "swing.stop_loss_pct", label: "Swing stop loss %", type: "number", step: 0.1 },
                { key: "swing.max_hold_days", label: "Max hold days", type: "number", min: 1, max: 30 },
                { key: "swing.max_open_positions", label: "Swing max positions", type: "number", min: 1, max: 10 },
                { key: "risk.max_open_positions", label: "Risk max positions", type: "number", min: 1, max: 10 },
                { key: "risk.daily_max_loss_pct", label: "Daily max loss %", type: "number", step: 0.1 },
              ]}
            />
          </div>

          <div className="panel" style={{ marginTop: "1rem" }}>
            <div className="panel-body" style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              {String(settings.note ?? "")}
              <br />
              Config file: <code>{String(settings.settings_path ?? "")}</code>
            </div>
          </div>
        </>
      )}
    </>
  );
}

type FieldDef = {
  key: string;
  label: string;
  type: "number" | "text" | "select";
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
};

function AdminSection({
  title,
  settings,
  fields,
  onSave,
}: {
  title: string;
  settings: SettingsSnapshot;
  fields: FieldDef[];
  onSave: (updates: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <div className="panel">
      <div className="panel-header">{title}</div>
      <div className="panel-body">
        {fields.map((f) => (
          <AdminField key={f.key} field={f} value={settings[f.key]} onSave={onSave} />
        ))}
      </div>
    </div>
  );
}

function AdminField({
  field,
  value,
  onSave,
}: {
  field: FieldDef;
  value: unknown;
  onSave: (updates: Record<string, unknown>) => Promise<void>;
}) {
  const [local, setLocal] = useState(String(value ?? ""));

  useEffect(() => {
    setLocal(String(value ?? ""));
  }, [value]);

  const commit = () => {
    let parsed: unknown = local;
    if (field.type === "number") {
      parsed = Number(local);
      if (Number.isNaN(parsed)) return;
    }
    void onSave({ [field.key]: parsed });
  };

  const inputId = `admin-${field.key.replace(/\./g, "-")}`;

  return (
    <div className="form-field">
      <label htmlFor={inputId}>{field.label}</label>
      <div className="form-field-row">
        {field.type === "select" ? (
          <select
            id={inputId}
            value={local}
            onChange={(e) => setLocal(e.target.value)}
          >
            {field.options?.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        ) : (
          <input
            id={inputId}
            type={field.type}
            value={local}
            min={field.min}
            max={field.max}
            step={field.step}
            onChange={(e) => setLocal(e.target.value)}
          />
        )}
        <button type="button" className="refresh-btn refresh-btn--small" onClick={commit}>
          Save
        </button>
      </div>
    </div>
  );
}
