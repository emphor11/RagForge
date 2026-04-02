import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";

const API_BASE_URL = "http://127.0.0.1:8000";

const DocumentAnalysis = () => {
  const { id } = useParams();
  const document_id = decodeURIComponent(id);

  const [result, setResult] = useState(null);
  const [contractProfile, setContractProfile] = useState(null);
  const [contractClauses, setContractClauses] = useState([]);
  const [contractFindings, setContractFindings] = useState([]);
  const [contractReviewAudit, setContractReviewAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [query, setQuery] = useState("");
  const [queryResult, setQueryResult] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [showReasoning, setShowReasoning] = useState(false);

  useEffect(() => {
    loadDocumentInsights();
    setQueryResult(null);
    setQuery("");
  }, [id]);

  const normalizeResult = (data) => {
    // If the backend returns the nested format: { insights: {...}, evaluation: {...} }
    // we extract the insights first, and could optionally use evaluation elsewhere.
    const realData = data.insights || data;
    
    // Handle legacy confidence score field name
    const overall_confidence = realData.overall_confidence ?? realData.confidence_score ?? 0;
    
    // Normalize key_insights (from strings to objects)
    const key_insights = (realData.key_insights || []).map(item => {
      if (typeof item === 'string') {
        return { insight: item, source: "Legacy analysis - no source quote available", confidence: overall_confidence };
      }
      return item;
    });

    // Normalize risks
    const risks = (realData.risks || []).map(r => ({
      ...r,
      source: r.source || "Legacy analysis",
      confidence: r.confidence ?? overall_confidence
    }));

    // Normalize actions
    const recommended_actions = (realData.recommended_actions || []).map(a => ({
      ...a,
      source: a.source || "Legacy analysis",
      confidence: a.confidence ?? overall_confidence
    }));

    return {
      ...realData,
      overall_confidence,
      key_insights,
      risks,
      recommended_actions,
      reasoning: realData.reasoning || "Reasoning not available for legacy analysis.",
      context_quality: realData.context_quality || "full",
      evaluation: data.evaluation || null // Pass the evaluation if it exists
    };
  };

  const loadDocumentInsights = async () => {
    setLoading(true);
    setError(null);
    try {
      const [insightsRes, overviewRes, clausesRes, risksRes, auditRes] = await Promise.all([
        fetch(`${API_BASE_URL}/insights/${encodeURIComponent(document_id)}`),
        fetch(`${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/overview`),
        fetch(`${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/clauses`),
        fetch(`${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/risks`),
        fetch(`${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/review-audit`)
      ]);

      if (!insightsRes.ok) throw new Error("Document analysis not found");

      const data = await insightsRes.json();
      if (!data || data.error) throw new Error("Document analysis not found");

      if (overviewRes.ok) {
        const overviewData = await overviewRes.json();
        setContractProfile(overviewData);
      } else if (overviewRes.status === 404) {
        setContractProfile(null);
      } else {
        throw new Error("Failed to load contract overview");
      }

      if (clausesRes.ok) {
        const clausesData = await clausesRes.json();
        setContractClauses(clausesData.clauses || []);
      } else if (clausesRes.status === 404) {
        setContractClauses([]);
      } else {
        throw new Error("Failed to load contract clauses");
      }

      if (risksRes.ok) {
        const risksData = await risksRes.json();
        setContractFindings(risksData.findings || []);
      } else if (risksRes.status === 404) {
        setContractFindings([]);
      } else {
        throw new Error("Failed to load contract findings");
      }

      if (auditRes.ok) {
        const auditData = await auditRes.json();
        setContractReviewAudit(auditData);
      } else if (auditRes.status === 404) {
        setContractReviewAudit(null);
      } else {
        throw new Error("Failed to load contract review audit");
      }

      setResult(normalizeResult(data));
    } catch (err) {
      console.error("Failed to load insights", err);
      setContractProfile(null);
      setContractClauses([]);
      setContractFindings([]);
      setContractReviewAudit(null);
      setError("Failed to load document insights. Please make sure the file exists.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuery = async () => {
    if (!query || queryLoading) return;

    setQueryLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
          document_id: document_id, 
        }),
      });

      if (!res.ok) throw new Error("Query failed");

      const data = await res.json();
      setQueryResult(data);
    } catch (err) {
      console.error(err);
      setError("Failed to get answer from AI");
    } finally {
      setQueryLoading(false);
    }
  };

  const getSeverityLabel = (severity) => {
    const s = severity?.toLowerCase();
    if (s === "high") return "High Risk";
    if (s === "medium") return "Medium Risk";
    return "Low Risk";
  };

  const renderConfidence = (val) => {
    const pct = (val * 100).toFixed(0);
    let color = "var(--success)";
    if (val < 0.7) color = "var(--warning)";
    if (val < 0.4) color = "var(--danger)";
    return <span style={{ color, fontSize: '11px', fontWeight: '600' }}>{pct}% Match</span>;
  };

  const formatDocumentType = (value) => {
    if (!value) return "Unknown";
    return value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  };

  const formatClauseType = (value) => {
    if (!value) return "Unclassified";
    return value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  };

  const formatFindingType = (value) => {
    if (!value) return "Finding";
    return value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  };

  const queryPlaceholder = contractProfile
    ? "e.g., What is the governing law? Is there a termination right? What does the confidentiality clause allow?"
    : "e.g., Extract the step-by-step implementation plan from section 4.";

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" style={{ marginBottom: '20px' }}></span>
        <div className="empty-state-title">Analyzing "{document_id}"</div>
        <div className="empty-state-desc">Running deep intelligence extraction...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠️</div>
        <div className="empty-state-title">Something went wrong</div>
        <div className="empty-state-desc">{error}</div>
        <button className="sidebar-upgrade-btn" onClick={loadDocumentInsights} style={{ marginTop: '20px' }}>Retry Analysis</button>
      </div>
    );
  }

  return (
    <div className="analysis-page">
      {/* ===== SYSTEM STATUS & QUALITY ===== */}
      {result.context_quality && result.context_quality !== "full" && (
        <div className={`quality-banner ${result.context_quality}`}>
          <div className="quality-banner-icon">⚠️</div>
          <div className="quality-banner-content">
            <strong>Context Warning: {result.context_quality.toUpperCase()}</strong>
            <p>{result.context_gap || "The document context may not fully support all generated insights."}</p>
          </div>
        </div>
      )}

      {/* ===== STATS ROW ===== */}
      <div className="stats-row" style={{ marginBottom: '20px', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        <div className="stat-card">
          <div className="stat-icon icon-bg-blue">📄</div>
          <div className="stat-value" style={{ fontSize: '14px', maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}>{document_id}</div>
          <div className="stat-label">Analyzing File</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon icon-bg-green">📈</div>
          <div className="stat-value">{result.key_insights?.length || 0}</div>
          <div className="stat-label">Grounded Insights</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon icon-bg-orange">⏱️</div>
          <div className="stat-value">{(result.overall_confidence * 100).toFixed(0)}%</div>
          <div className="stat-label">Avg Match Score</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon icon-bg-purple">🛡️</div>
          <div className="stat-value">{result.evaluation?.score || 0}%</div>
          <div className="stat-label">Intelligence Quality</div>
        </div>
      </div>

      {/* ===== EVALUATION REPORT (NEW) ===== */}
      {result.evaluation && (
        <div className="card" style={{ marginBottom: '20px', borderLeft: `4px solid ${result.evaluation.status === 'pass' ? 'var(--success)' : 'var(--danger)'}` }}>
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon" style={{ background: result.evaluation.status === 'pass' ? 'var(--success-bg)' : 'var(--danger-bg)', color: result.evaluation.status === 'pass' ? 'var(--success)' : 'var(--danger)' }}>
                {result.evaluation.status === 'pass' ? '✅' : '⚠️'}
              </div>
              Automated Evaluation Report
            </div>
            <div className={`risk-badge ${result.evaluation.status === 'pass' ? 'low' : 'high'}`} style={{ textTransform: 'uppercase' }}>
              {result.evaluation.status === 'pass' ? 'Audit Passed' : 'Audit Failed'}
            </div>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', marginBottom: '20px' }}>
               <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', fontWeight: '700' }}>{result.evaluation.metrics?.grounding}%</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Grounding</div>
               </div>
               <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', fontWeight: '700' }}>{result.evaluation.metrics?.quality}%</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Richness</div>
               </div>
               <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', fontWeight: '700' }}>{result.evaluation.metrics?.structure}%</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Structure</div>
               </div>
               <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '18px', fontWeight: '700' }}>{result.evaluation.metrics?.coverage ?? 0}%</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Coverage</div>
               </div>
            </div>

            {/* Recommendation Alert */}
            {result.evaluation.recommendation && (
              <div style={{ 
                padding: '12px', 
                borderRadius: '8px', 
                marginBottom: '16px',
                background: result.evaluation.status === 'pass' ? 'var(--success-bg)' : 'var(--danger-bg)',
                border: `1px solid ${result.evaluation.status === 'pass' ? 'var(--success)' : 'var(--danger)'}`,
                color: result.evaluation.status === 'pass' ? 'var(--success-dark)' : 'var(--danger-dark)',
                fontSize: '14px',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}>
                <span style={{ fontSize: '18px' }}>{result.evaluation.status === 'pass' ? '🛡️' : '🚫'}</span>
                {result.evaluation.recommendation}
              </div>
            )}
            
            {result.evaluation.issues?.length > 0 && (
              <div style={{ padding: '12px', background: 'rgba(0,0,0,0.03)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <strong style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'block', marginBottom: '8px' }}>Audit Log ({result.evaluation.issue_count} items):</strong>
                <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                  {result.evaluation.issues.map((issue, idx) => (
                    <li key={idx} style={{ marginBottom: '4px' }}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== REASONING SECTION (COLLAPSIBLE) ===== */}
      <div className="card reasoning-card" style={{ marginBottom: '20px' }}>
        <div className="card-header" onClick={() => setShowReasoning(!showReasoning)} style={{ cursor: 'pointer', paddingBottom: showReasoning ? '16px' : '20px' }}>
          <div className="card-title">
            <div className="card-title-icon icon-bg-purple">🧠</div>
            AI Reasoning Engine
          </div>
          <span className="toggle-icon">{showReasoning ? '−' : '+'}</span>
        </div>
        {showReasoning && (
          <div className="card-body reasoning-body">
            <p className="reasoning-text">{result.reasoning}</p>
          </div>
        )}
      </div>

      {/* ===== CONTRACT OVERVIEW ===== */}
      {contractProfile && (
        <div className="card" style={{ marginBottom: '20px' }}>
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-blue">⚖️</div>
              Contract Overview
            </div>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Document Type</div>
                <div style={{ fontWeight: '600' }}>{formatDocumentType(contractProfile.document_type)}</div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Classification Confidence</div>
                <div style={{ fontWeight: '600' }}>{((contractProfile.classification_confidence || 0) * 100).toFixed(0)}%</div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Effective Date</div>
                <div style={{ fontWeight: '600' }}>{contractProfile.effective_date || "Not detected"}</div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Governing Law</div>
                <div style={{ fontWeight: '600' }}>{contractProfile.governing_law || "Not detected"}</div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Term Length</div>
                <div style={{ fontWeight: '600' }}>{contractProfile.term_length || "Not detected"}</div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Renewal Mechanics</div>
                <div style={{ fontWeight: '600' }}>{contractProfile.renewal_mechanics || "Not detected"}</div>
              </div>
            </div>

            <div style={{ marginTop: '18px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>Parties</div>
              {contractProfile.parties?.length ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                  {contractProfile.parties.map((party, idx) => (
                    <span
                      key={`${party}-${idx}`}
                      style={{
                        padding: '8px 12px',
                        borderRadius: '999px',
                        background: 'rgba(37, 99, 235, 0.12)',
                        border: '1px solid rgba(37, 99, 235, 0.2)',
                        color: 'var(--text-primary)',
                        fontSize: '13px',
                        fontWeight: '500'
                      }}
                    >
                      {party}
                    </span>
                  ))}
                </div>
              ) : (
                <div style={{ fontWeight: '600' }}>Not detected</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ===== CLAUSE INVENTORY ===== */}
      {contractClauses.length > 0 && (
        <div className="card" style={{ marginBottom: '20px' }}>
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-green">🧾</div>
              Clause Inventory
            </div>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' }}>
              {contractClauses.map((clause) => (
                <div
                  key={`${clause.chunk_id}-${clause.title}`}
                  style={{
                    border: '1px solid var(--border-color)',
                    borderRadius: '12px',
                    padding: '14px',
                    background: 'rgba(255,255,255,0.02)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', gap: '10px', marginBottom: '8px' }}>
                    <strong style={{ lineHeight: 1.4 }}>{clause.title}</strong>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: '600',
                        padding: '4px 8px',
                        borderRadius: '999px',
                        background: 'rgba(16, 185, 129, 0.12)',
                        border: '1px solid rgba(16, 185, 129, 0.2)',
                        color: 'var(--text-primary)',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {formatClauseType(clause.type)}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Page {clause.page_number} · {clause.chunk_ids?.length ? `${clause.chunk_ids.length} chunk${clause.chunk_ids.length > 1 ? 's' : ''}` : `Chunk ${clause.chunk_id}`}
                  </div>
                  {clause.text_preview && (
                    <p style={{ margin: '10px 0 0 0', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      {clause.text_preview}
                      {clause.clause_text && clause.clause_text.length > clause.text_preview.length ? "..." : ""}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {contractFindings.length > 0 && (
        <div className="card" style={{ marginBottom: '20px' }}>
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-red">⚠️</div>
              Contract Review Findings
            </div>
          </div>
          <div className="card-body">
            <ul className="risk-list">
              {contractFindings.map((finding, idx) => (
                <li key={`${finding.title}-${idx}`} className="risk-item-complex">
                  <div className="risk-header">
                    <div className="risk-title-row">
                      <span className={`risk-dot ${finding.severity?.toLowerCase()}`}></span>
                      <strong>{finding.title}</strong>
                    </div>
                    <span className={`risk-badge ${finding.severity?.toLowerCase()}`}>
                      {getSeverityLabel(finding.severity)}
                    </span>
                  </div>
                  <p className="risk-reason">{finding.explanation}</p>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: '600',
                        padding: '4px 8px',
                        borderRadius: '999px',
                        background: 'rgba(239, 68, 68, 0.12)',
                        border: '1px solid rgba(239, 68, 68, 0.2)',
                        color: 'var(--text-primary)'
                      }}
                    >
                      {formatFindingType(finding.finding_type)}
                    </span>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: '600',
                        padding: '4px 8px',
                        borderRadius: '999px',
                        background: 'rgba(59, 130, 246, 0.12)',
                        border: '1px solid rgba(59, 130, 246, 0.2)',
                        color: 'var(--text-primary)'
                      }}
                    >
                      {formatClauseType(finding.clause_type)}
                    </span>
                    {finding.status && (
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: '600',
                          padding: '4px 8px',
                          borderRadius: '999px',
                          background: 'rgba(16, 185, 129, 0.12)',
                          border: '1px solid rgba(16, 185, 129, 0.2)',
                          color: 'var(--text-primary)'
                        }}
                      >
                        {formatDocumentType(finding.status)}
                      </span>
                    )}
                  </div>
                  {finding.source_quotes?.map((quote, quoteIdx) => (
                    <blockquote key={quoteIdx} className="source-quote">"{quote}"</blockquote>
                  ))}
                  <div style={{ textAlign: 'right', marginTop: '4px' }}>
                    {renderConfidence(finding.confidence)}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {contractReviewAudit && (
        <div
          className="card"
          style={{
            marginBottom: '20px',
            borderLeft: `4px solid ${
              contractReviewAudit.status === 'pass'
                ? 'var(--success)'
                : contractReviewAudit.status === 'needs_review'
                  ? 'var(--warning)'
                  : 'var(--danger)'
            }`
          }}
        >
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-orange">🏛️</div>
              Contract Review Audit
            </div>
            <div
              className={`risk-badge ${
                contractReviewAudit.status === 'pass'
                  ? 'low'
                  : contractReviewAudit.status === 'needs_review'
                    ? 'medium'
                    : 'high'
              }`}
              style={{ textTransform: 'uppercase' }}
            >
              {formatDocumentType(contractReviewAudit.status)}
            </div>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', marginBottom: '20px' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '18px', fontWeight: '700' }}>{contractReviewAudit.metrics?.grounding ?? 0}%</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Grounding</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '18px', fontWeight: '700' }}>{contractReviewAudit.metrics?.severity_calibration ?? 0}%</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Severity</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '18px', fontWeight: '700' }}>{contractReviewAudit.metrics?.structure ?? 0}%</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Structure</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '18px', fontWeight: '700' }}>{contractReviewAudit.metrics?.completeness ?? 0}%</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Completeness</div>
              </div>
            </div>

            {contractReviewAudit.recommendation && (
              <div style={{
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '16px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                fontSize: '14px',
                fontWeight: '500'
              }}>
                {contractReviewAudit.recommendation}
              </div>
            )}

            {contractReviewAudit.issues?.length > 0 && (
              <div style={{ padding: '12px', background: 'rgba(0,0,0,0.03)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <strong style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'block', marginBottom: '8px' }}>
                  Audit Log ({contractReviewAudit.issue_count} items):
                </strong>
                <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                  {contractReviewAudit.issues.map((issue, idx) => (
                    <li key={idx} style={{ marginBottom: '4px' }}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== RESULTS GRID ===== */}
      <div className="two-col-grid">
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-blue">📋</div>
              Executive Summary
            </div>
          </div>
          <div className="card-body">
            <p className="summary-text">{result.summary}</p>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-green">💡</div>
              Key Insights
            </div>
          </div>
          <div className="card-body">
            <ul className="insight-list">
              {result.key_insights?.map((i, idx) => (
                <li key={idx} className="insight-item-complex">
                  <div className="insight-main">
                    <span className="insight-bullet">✓</span>
                    <div className="insight-content">
                      <div className="insight-header">
                        <span className="insight-text">{i.insight}</span>
                        {renderConfidence(i.confidence)}
                      </div>
                      <blockquote className="source-quote">"{i.source}"</blockquote>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="two-col-grid">
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-red">🛡️</div>
              Risks Identified
            </div>
          </div>
          <div className="card-body">
            <ul className="risk-list">
              {result.risks?.map((r, idx) => (
                <li key={idx} className="risk-item-complex">
                  <div className="risk-header">
                    <div className="risk-title-row">
                      <span className={`risk-dot ${r.severity?.toLowerCase()}`}></span>
                      <strong>{r.finding}</strong>
                    </div>
                    <span className={`risk-badge ${r.severity?.toLowerCase()}`}>
                      {getSeverityLabel(r.severity)}
                    </span>
                  </div>
                  <p className="risk-reason">{r.reason}</p>
                  <blockquote className="source-quote">"{r.source}"</blockquote>
                  <div style={{ textAlign: 'right', marginTop: '4px' }}>
                    {renderConfidence(r.confidence)}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-purple">🚀</div>
              Recommended Actions
            </div>
          </div>
          <div className="card-body">
            <ul className="action-list">
              {result.recommended_actions?.map((a, idx) => (
                <li key={idx} className="action-item-complex">
                  <div className="action-main">
                    <span className="action-dot"></span>
                    <div className="action-content">
                      <div className="action-header">
                        <strong>{a.action}</strong>
                        {renderConfidence(a.confidence)}
                      </div>
                      <p className="action-rationale">{a.rationale}</p>
                      <blockquote className="source-quote">"{a.source}"</blockquote>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* ===== Q&A SECTION ===== */}
      <div className="query-card full-width" style={{ marginTop: '20px' }}>
        {queryResult && queryResult.reasoning && (
           <div className="ai-reasoning-mini">
              <strong>Thought Process:</strong>
              <p>{queryResult.reasoning}</p>
           </div>
        )}

        <div className="query-card-header">
          <div className="query-card-icon">💬</div>
          <h2 className="query-card-title">Strategic Q&A</h2>
        </div>
        <p className="query-card-subtitle">Answers are strictly grounded in <strong>{document_id}</strong> citations.</p>
        
        {queryResult && queryResult.context_quality !== "full" && (
           <div className="inline-gap-warning">
              ⚠️ <strong>Partial Context:</strong> {queryResult.context_gap}
           </div>
        )}

        <div className="query-input-row" style={{ marginTop: '10px' }}>
          <input
            type="text"
            className="query-input"
            placeholder={queryPlaceholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleQuery()}
            disabled={queryLoading}
          />
          <button className={`query-btn ${queryLoading ? 'loading' : ''}`} onClick={handleQuery} disabled={queryLoading}>
            {queryLoading ? <span className="spinner"></span> : "Analyze →"}
          </button>
        </div>

        {queryResult && (
          <div className="ai-response">
            <div className="ai-response-header">✨ Intelligence Report</div>
            <div className="ai-response-text" style={{ whiteSpace: 'pre-wrap' }}>{queryResult.summary}</div>
            
            {queryResult.key_insights?.length > 0 && (
              <div className="response-citations">
                <strong>Supporting Evidence:</strong>
                {queryResult.key_insights.map((ins, i) => (
                   <div key={i} className="citation-item">
                      <blockquote className="source-quote">"{ins.source}"</blockquote>
                      <div className="citation-meta">
                        {renderConfidence(ins.confidence)}
                      </div>
                   </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentAnalysis;
