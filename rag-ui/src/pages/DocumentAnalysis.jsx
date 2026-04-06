import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";

import { API_BASE_URL } from "../config";
import DocumentViewer from "../components/DocumentViewer";

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
  const [showSupplementalAnalysis, setShowSupplementalAnalysis] = useState(false);
  const [updatingFindingIndex, setUpdatingFindingIndex] = useState(null);
  const [findingFilter, setFindingFilter] = useState("all");
  const [reviewerNotes, setReviewerNotes] = useState({});
  const [savingNoteIndex, setSavingNoteIndex] = useState(null);
  
  const [rawText, setRawText] = useState("");
  const [activeQuote, setActiveQuote] = useState(null);

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
        setReviewerNotes(
          Object.fromEntries(
            (risksData.findings || []).map((finding, idx) => [idx, finding.reviewer_note || ""])
          )
        );
      } else if (risksRes.status === 404) {
        setContractFindings([]);
        setReviewerNotes({});
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
      setRawText(data.raw_text || "");
    } catch (err) {
      console.error("Failed to load insights", err);
      setContractProfile(null);
      setContractClauses([]);
      setContractFindings([]);
      setReviewerNotes({});
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

  const handleFindingStatusUpdate = async (findingIndex, status) => {
    if (updatingFindingIndex !== null) return;

    setUpdatingFindingIndex(findingIndex);
    try {
      const res = await fetch(
        `${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/findings/${findingIndex}/audit`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status }),
        }
      );

      if (!res.ok) throw new Error("Failed to update finding status");

      const data = await res.json();
      setContractFindings((current) =>
        current.map((finding, idx) =>
          idx === findingIndex ? data.finding : finding
        )
      );
    } catch (err) {
      console.error(err);
      setError("Failed to update review finding status.");
    } finally {
      setUpdatingFindingIndex(null);
    }
  };

  const handleReviewerNoteSave = async (findingIndex) => {
    if (savingNoteIndex !== null) return;

    setSavingNoteIndex(findingIndex);
    try {
      const res = await fetch(
        `${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/findings/${findingIndex}/audit`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ reviewer_note: reviewerNotes[findingIndex] || "" }),
        }
      );

      if (!res.ok) throw new Error("Failed to save reviewer note");

      const data = await res.json();
      setContractFindings((current) =>
        current.map((finding, idx) =>
          idx === findingIndex ? data.finding : finding
        )
      );
    } catch (err) {
      console.error(err);
      setError("Failed to save reviewer note.");
    } finally {
      setSavingNoteIndex(null);
    }
  };

  const handleExportReport = () => {
    // Direct link to download
    window.open(`${API_BASE_URL}/export/${encodeURIComponent(document_id)}`, '_blank');
  };

  const getSeverityLabel = (severity) => {
    const s = severity?.toLowerCase();
    if (s === "high") return "Critical Risk";
    if (s === "medium") return "Moderate Risk";
    return "Minor Risk";
  };

  const renderConfidence = (val) => {
    const pct = (val * 100).toFixed(0);
    let color = "var(--success)";
    if (val < 0.7) color = "var(--warning)";
    if (val < 0.4) color = "var(--danger)";
    return <span style={{ color, fontSize: '11px', fontWeight: '700', background: 'rgba(0,0,0,0.03)', padding: '2px 6px', borderRadius: '4px' }}>{pct}% Grounded</span>;
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
  const isContractReview = Boolean(contractProfile);
  const filteredFindings = contractFindings.filter((finding) => (
    findingFilter === "all" ? true : (finding.status || "open") === findingFilter
  ));

  const riskFindings = filteredFindings.filter(f => f.finding_type !== 'missing_protection');
  const missingProtections = filteredFindings.filter(f => f.finding_type === 'missing_protection');
  const findingCounts = {
    all: contractFindings.length,
    open: contractFindings.filter((finding) => (finding.status || "open") === "open").length,
    accepted: contractFindings.filter((finding) => finding.status === "accepted").length,
    dismissed: contractFindings.filter((finding) => finding.status === "dismissed").length,
    escalated: contractFindings.filter((finding) => finding.status === "escalated").length,
  };
  const severityCounts = {
    high: contractFindings.filter((finding) => finding.severity === "high").length,
    medium: contractFindings.filter((finding) => finding.severity === "medium").length,
    low: contractFindings.filter((finding) => finding.severity === "low").length,
  };
  const typeCounts = {
    risk: contractFindings.filter((finding) => finding.finding_type === "risk").length,
    missing_protection: contractFindings.filter((finding) => finding.finding_type === "missing_protection").length,
    negotiation_point: contractFindings.filter((finding) => finding.finding_type === "negotiation_point").length,
  };

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
          <div className="stat-label">{isContractReview ? "Analyzed Agreement" : "Analyzing File"}</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon icon-bg-green">📈</div>
          <div className="stat-value">{isContractReview ? contractFindings.length : (result.key_insights?.length || 0)}</div>
          <div className="stat-label">{isContractReview ? "Review Findings" : "Grounded Insights"}</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon icon-bg-orange">⏱️</div>
          <div className="stat-value">
            {isContractReview
              ? `${contractClauses.length}`
              : `${(result.overall_confidence * 100).toFixed(0)}%`}
          </div>
          <div className="stat-label">{isContractReview ? "Clauses Indexed" : "Avg Grounding Score"}</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon icon-bg-purple">🛡️</div>
          <div className="stat-value">
            {isContractReview
              ? `${contractReviewAudit?.score ?? 0}%`
              : `${result.evaluation?.score || 0}%`}
          </div>
          <div className="stat-label">{isContractReview ? "Review Audit" : "Intelligence Quality"}</div>
        </div>
      </div>

      {/* ===== ACTIONS ROW ===== */}
      {isContractReview && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '20px', gap: '12px' }}>
          <button
            onClick={handleExportReport}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 20px',
              borderRadius: '12px',
              background: 'var(--accent-primary)',
              color: 'white',
              border: 'none',
              fontWeight: '600',
              fontSize: '14px',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.2)'
            }}
          >
            <span>📥</span> Export Review Report (.docx)
          </button>
        </div>
      )}

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

      {/* ===== 1. CONTRACT REVIEW FINDINGS (PRIORITY 1) ===== */}
      {contractFindings.length > 0 && (
        <div className="card" style={{ marginBottom: '20px' }}>
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-red">⚠️</div>
              Contract Review Findings
            </div>
          </div>
          <div className="card-body">
            {/* Findings stats and list will go here - keeping it simple for now to move the block */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '12px', marginBottom: '16px' }}>
              <div style={{ border: '1px solid rgba(239, 68, 68, 0.2)', background: 'rgba(239, 68, 68, 0.08)', borderRadius: '12px', padding: '14px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Severity Mix</div>
                <div style={{ fontWeight: '600', lineHeight: 1.7 }}>
                  High: {severityCounts.high} · Medium: {severityCounts.medium} · Low: {severityCounts.low}
                </div>
              </div>
              <div style={{ border: '1px solid rgba(59, 130, 246, 0.2)', background: 'rgba(59, 130, 246, 0.08)', borderRadius: '12px', padding: '14px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Finding Types</div>
                <div style={{ fontWeight: '600', lineHeight: 1.7 }}>
                  Risks: {typeCounts.risk} · Missing: {typeCounts.missing_protection} · Negotiation: {typeCounts.negotiation_point}
                </div>
              </div>
              <div style={{ border: '1px solid rgba(16, 185, 129, 0.2)', background: 'rgba(16, 185, 129, 0.08)', borderRadius: '12px', padding: '14px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Reviewer Progress</div>
                <div style={{ fontWeight: '600', lineHeight: 1.7 }}>
                  Open: {findingCounts.open} · Accepted: {findingCounts.accepted} · Escalated: {findingCounts.escalated}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
              {[
                ["all", "All"],
                ["open", "Open"],
                ["accepted", "Accepted"],
                ["dismissed", "Dismissed"],
                ["escalated", "Escalated"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFindingFilter(value)}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '999px',
                    border: '1px solid var(--border-color)',
                    background: findingFilter === value ? 'rgba(59, 130, 246, 0.16)' : 'rgba(255,255,255,0.03)',
                    color: 'var(--text-primary)',
                    fontSize: '12px',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  {label} ({findingCounts[value]})
                </button>
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
              {/* --- RISK FINDINGS SUBSECTION --- */}
              <div>
                <h3 style={{ fontSize: '14px', marginBottom: '12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--danger)' }}></span>
                  Risk Findings ({riskFindings.length})
                </h3>
                {riskFindings.length > 0 ? (
                  <ul className="risk-list">
                    {riskFindings.map((finding) => {
                      const idx = contractFindings.indexOf(finding);
                      return (
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
                                color: 'var(--text-secondary)'
                              }}
                            >
                              {formatDocumentType(finding.status)}
                            </span>
                          )}
                        </div>
                        {finding.source_quotes?.map((quote, quoteIdx) => (
                          <blockquote 
                            key={quoteIdx} 
                            className="source-quote"
                            style={{ cursor: 'pointer' }}
                            onClick={() => setActiveQuote(quote)}
                            title="Click to locate and verify this exact wording in the source document"
                          >
                            "{quote}"
                          </blockquote>
                        ))}
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '12px' }}>
                          <button
                            className="query-btn"
                            style={{ padding: '8px 12px', minWidth: 'auto' }}
                            disabled={updatingFindingIndex === idx}
                            onClick={() => handleFindingStatusUpdate(idx, "accepted")}
                          >
                            Accept
                          </button>
                          <button
                            className="query-btn"
                            style={{ padding: '8px 12px', minWidth: 'auto', background: 'var(--warning)', color: '#000' }}
                            disabled={updatingFindingIndex === idx}
                            onClick={() => handleFindingStatusUpdate(idx, "negotiate")}
                          >
                            Negotiate
                          </button>
                          <button
                            className="query-btn"
                            style={{ padding: '8px 12px', minWidth: 'auto', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                            disabled={updatingFindingIndex === idx}
                            onClick={() => handleFindingStatusUpdate(idx, "dismissed")}
                          >
                            Dismiss
                          </button>
                          <button
                            className="query-btn"
                            style={{ padding: '8px 12px', minWidth: 'auto', background: 'var(--danger)' }}
                            disabled={updatingFindingIndex === idx}
                            onClick={() => handleFindingStatusUpdate(idx, "escalated")}
                          >
                            Escalate
                          </button>
                        </div>
                        <div style={{ marginTop: '12px' }}>
                          <textarea
                            value={reviewerNotes[idx] || ""}
                            onChange={(e) =>
                              setReviewerNotes((current) => ({
                                ...current,
                                [idx]: e.target.value,
                              }))
                            }
                            placeholder="Add review note..."
                            rows={2}
                            style={{
                              width: '100%',
                              borderRadius: '8px',
                              border: '1px solid var(--border-color)',
                              background: 'rgba(255,255,255,0.02)',
                              color: 'var(--text-primary)',
                              padding: '8px 10px',
                              fontSize: '12px',
                              resize: 'vertical',
                              boxSizing: 'border-box'
                            }}
                          />
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
                            <button
                              className="query-btn"
                              style={{ padding: '4px 10px', minWidth: 'auto', fontSize: '11px' }}
                              disabled={savingNoteIndex === idx}
                              onClick={() => handleReviewerNoteSave(idx)}
                            >
                              {savingNoteIndex === idx ? "..." : "Save Note"}
                            </button>
                          </div>
                        </div>
                        <div style={{ textAlign: 'right', marginTop: '4px' }}>
                          {renderConfidence(finding.confidence)}
                        </div>
                      </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', padding: '10px 0' }}>No active risk findings for this filter.</p>
                )}
              </div>

              {/* --- MISSING PROTECTIONS SUBSECTION --- */}
              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                <h3 style={{ fontSize: '14px', marginBottom: '12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--warning)' }}></span>
                  Missing Protections ({missingProtections.length})
                </h3>
                {missingProtections.length > 0 ? (
                  <ul className="risk-list">
                    {missingProtections.map((finding) => {
                      const idx = contractFindings.indexOf(finding);
                      return (
                      <li key={`${finding.title}-${idx}`} className="risk-item-complex" style={{ borderLeft: '4px solid var(--warning)' }}>
                        <div className="risk-header">
                          <div className="risk-title-row">
                            <strong>{finding.title}</strong>
                          </div>
                          <span className={`risk-badge ${finding.severity?.toLowerCase()}`}>
                            {getSeverityLabel(finding.severity)}
                          </span>
                        </div>
                        <p className="risk-reason">{finding.explanation}</p>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
                          <span style={{ fontSize: '11px', fontWeight: '600', padding: '4px 8px', borderRadius: '999px', background: 'rgba(217, 119, 6, 0.12)', border: '1px solid rgba(217, 119, 6, 0.2)', color: 'var(--text-primary)' }}>
                            {formatClauseType(finding.clause_type)}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '12px' }}>
                          <button className="query-btn" style={{ padding: '8px 12px', minWidth: 'auto' }} onClick={() => handleFindingStatusUpdate(idx, "accepted")}>Accept</button>
                          <button className="query-btn" style={{ padding: '8px 12px', minWidth: 'auto', background: 'var(--warning)', color: '#000' }} onClick={() => handleFindingStatusUpdate(idx, "negotiate")}>Add to Redline</button>
                          <button className="query-btn" style={{ padding: '8px 12px', minWidth: 'auto', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }} onClick={() => handleFindingStatusUpdate(idx, "dismissed")}>Dismiss</button>
                        </div>
                      </li>
                      );
                    })}
                  </ul>
                ) : (
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', padding: '10px 0' }}>No missing protections identified.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===== 2. CLAUSE INVENTORY (PRIORITY 2) ===== */}
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
              {contractClauses.map((clause, idx) => (
                <div
                  key={`${idx}-${clause.title}`}
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
                    Page {clause.page_number}
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

      {result.evaluation && (!isContractReview || showSupplementalAnalysis) && (
        <div className="card" style={{ marginBottom: '20px', borderLeft: `4px solid ${result.evaluation.status === 'pass' ? 'var(--success)' : 'var(--danger)'}` }}>
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon" style={{ background: result.evaluation.status === 'pass' ? 'var(--success-bg)' : 'var(--danger-bg)', color: result.evaluation.status === 'pass' ? 'var(--success)' : 'var(--danger)' }}>
                {result.evaluation.status === 'pass' ? '✅' : '⚠️'}
              </div>
              Analysis Quality Check
            </div>
            <div className={`risk-badge ${result.evaluation.status === 'pass' ? 'low' : 'high'}`} style={{ textTransform: 'uppercase' }}>
              {result.evaluation.status === 'pass' ? 'VERIFIED' : 'REVIEW REQUIRED'}
            </div>
          </div>
          <div className="card-body">
            {result.evaluation.recommendation && (
              <div style={{
                padding: '12px',
                borderRadius: '8px',
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
          </div>
        </div>
      )}



      {contractReviewAudit && (
        <div
          className="card"
          style={{
            marginBottom: '20px',
            borderLeft: `4px solid ${contractReviewAudit.status === 'pass' ? 'var(--success)' : 'var(--danger)'}`
          }}
        >
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-orange">🛡️</div>
              Analysis Quality Check
            </div>
            <div className={`risk-badge ${contractReviewAudit.status === 'pass' ? 'low' : 'high'}`} style={{ textTransform: 'uppercase' }}>
              {contractReviewAudit.status === 'pass' ? 'Verified' : 'Review Required'}
            </div>
          </div>
          <div className="card-body">
            <div style={{
              padding: '12px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              fontSize: '14px',
              fontWeight: '500'
            }}>
              {contractReviewAudit.recommendation || "The system has verified the findings against the document source text."}
            </div>
          </div>
        </div>
      )}

      {/* ===== RESULTS GRID ===== */}
      {(!isContractReview || showSupplementalAnalysis) && (
      <div className="two-col-grid">
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-blue">📋</div>
              {isContractReview ? "Supplemental Executive Summary" : "Executive Summary"}
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
              {isContractReview ? "Supplemental Key Insights" : "Key Insights"}
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
      )}

      {(!isContractReview || showSupplementalAnalysis) && (
      <div className="two-col-grid">
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-red">🛡️</div>
              {isContractReview ? "Supplemental Risks Identified" : "Risks Identified"}
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
              {isContractReview ? "Supplemental Recommended Actions" : "Recommended Actions"}
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
      )}

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
          <h2 className="query-card-title">{isContractReview ? "Contract Q&A" : "Strategic Q&A"}</h2>
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
      
      {/* ===== LEGAL DISCLAIMER (UPL Shield) ===== */}
      <div style={{
          marginTop: '40px',
          padding: '20px',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          color: 'rgba(255,255,255,0.4)',
          fontSize: '11px',
          lineHeight: '1.5',
          textAlign: 'center',
          maxWidth: '800px',
          margin: '40px auto 0'
      }}>
        <p>
          <strong>IMPORTANT NOTICE:</strong> This report is generated by the RAGForge Legal Intelligence Engine exclusively to assist attorneys in their review process. 
          It does <strong>NOT</strong> constitute legal advice, form an attorney-client relationship, or substitute human legal judgment. 
          Artificial Intelligence can hallucinate, omit critical context, or misinterpret drafting intent. 
          You must verify all findings, missing protections, and source quotes manually against the primary document before advising clients.
        </p>
      </div>

      <DocumentViewer 
        rawText={rawText} 
        highlightQuote={activeQuote} 
        onClose={() => setActiveQuote(null)} 
      />

    </div>
  );
};

export default DocumentAnalysis;
