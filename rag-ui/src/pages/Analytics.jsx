import { useState, useEffect } from "react";
import { API_BASE_URL } from "../config";
import { AlertTriangle, TrendingUp, TrendingDown, Minus } from "lucide-react";

const Analytics = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/analytics`);
      if (!res.ok) throw new Error("Failed to load analytics");
      setData(await res.json());
    } catch (err) {
      console.error(err);
      setError("Failed to retrieve system performance analytics.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner spinner-lg" style={{ marginBottom: "16px" }} />
        <div className="empty-state-title">Calculating Metrics</div>
        <div className="empty-state-desc">Aggregating system performance and trend data…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon"><AlertTriangle /></div>
        <div className="empty-state-title">Analytics Unavailable</div>
        <div className="empty-state-desc">{error}</div>
        <button className="btn btn-primary" onClick={fetchAnalytics} style={{ marginTop: "16px" }}>
          Retry Analysis
        </button>
      </div>
    );
  }

  // Compute max doc count for bar widths
  const docEntries = Object.entries(data.docs_over_time || {}).sort((a, b) => b[0].localeCompare(a[0]));
  const maxDocCount = Math.max(...docEntries.map(([, c]) => c), 1);

  // Risk trend
  const lastWeek = data.risk_trend?.last_week || 0;
  const thisWeek = data.risk_trend?.this_week || 0;
  const trendDelta = thisWeek - lastWeek;
  const trendPct = lastWeek > 0 ? ((trendDelta / lastWeek) * 100).toFixed(0) : 0;
  const direction = data.risk_trend?.direction || "stable";

  return (
    <div className="analytics-page">
      <div className="two-col-grid">
        {/* Document Activity with inline bars */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Document Activity</div>
          </div>
          <div className="card-body">
            {docEntries.length > 0 ? (
              docEntries.map(([date, count]) => (
                <div key={date} className="activity-row">
                  <span className="activity-date">{date}</span>
                  <div className="activity-bar">
                    <div
                      className="activity-bar-fill"
                      style={{ width: `${(count / maxDocCount) * 100}%` }}
                    />
                  </div>
                  <span className="activity-count">{count} docs</span>
                </div>
              ))
            ) : (
              <div className="empty-state-desc">No activity recorded.</div>
            )}
          </div>
        </div>

        {/* Risk Trend — neutral presentation */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Risk Trend</div>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", alignItems: "center", gap: "16px", padding: "8px 0 16px" }}>
              <div>
                <div className="stat-label">Last Week</div>
                <div className="stat-value" style={{ fontSize: "24px" }}>{lastWeek}</div>
              </div>
              <div style={{ color: "var(--text-faint)", fontSize: "20px" }}>→</div>
              <div>
                <div className="stat-label">This Week</div>
                <div className="stat-value" style={{ fontSize: "24px" }}>{thisWeek}</div>
              </div>
              <div style={{ flex: 1 }} />
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                padding: "6px 10px",
                borderRadius: "var(--radius-badge)",
                background: direction === "down" ? "var(--success-bg)" : direction === "up" ? "var(--danger-bg)" : "var(--bg-surface-alt)",
                color: direction === "down" ? "var(--success)" : direction === "up" ? "var(--danger)" : "var(--text-muted)",
                fontSize: "13px",
                fontWeight: 500
              }}>
                {direction === "up" && <TrendingUp size={14} />}
                {direction === "down" && <TrendingDown size={14} />}
                {direction === "stable" && <Minus size={14} />}
                {trendDelta > 0 ? "+" : ""}{trendPct}%
              </div>
            </div>

            <div style={{ borderTop: "1px solid var(--border-default)", paddingTop: "12px" }}>
              <div className="stat-label" style={{ marginBottom: "4px" }}>Status</div>
              <div style={{ fontSize: "14px", color: "var(--text-body)" }}>
                {direction === "down"
                  ? "Risks are decreasing — trending favorably."
                  : direction === "up"
                  ? "Risks are increasing — review new documents."
                  : "Risk levels are holding steady."}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="two-col-grid">
        {/* Performance Metrics */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Performance</div>
          </div>
          <div className="card-body">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div>
                <div className="stat-label">Avg Confidence</div>
                <div className="stat-value" style={{ fontSize: "20px" }}>
                  {(data.performance.avg_confidence * 100).toFixed(0)}%
                </div>
              </div>
              <div>
                <div className="stat-label">Response Time</div>
                <div className="stat-value" style={{ fontSize: "20px" }}>
                  {data.performance.avg_response_time}s
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Usage Stats */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Usage</div>
          </div>
          <div className="card-body">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div>
                <div className="stat-label">Queries Asked</div>
                <div className="stat-value" style={{ fontSize: "20px" }}>
                  {data.usage.total_queries}
                </div>
              </div>
              <div>
                <div className="stat-label">Analyses Done</div>
                <div className="stat-value" style={{ fontSize: "20px" }}>
                  {data.usage.total_analyses}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Common Risks */}
      <div className="card full-width">
        <div className="card-header">
          <div className="card-title">Common System Risks</div>
        </div>
        <div className="card-body">
          {[
            { name: "Identity & Access Misconfiguration", level: "high", label: "High Probability" },
            { name: "API Response Latency Spikes", level: "medium", label: "Medium Probability" },
            { name: "Context Window Overflows", level: "low", label: "Low Probability" },
          ].map((risk, idx) => (
            <div
              key={idx}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "10px 0",
                borderBottom: idx < 2 ? "1px solid var(--border-default)" : "none",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span
                  className={`insight-severity-dot ${risk.level}`}
                  style={{ marginTop: 0 }}
                />
                <span style={{ fontSize: "14px", color: "var(--text-body)" }}>{risk.name}</span>
              </div>
              <span className={`badge badge-${risk.level}`}>{risk.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Analytics;
