import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { API_BASE_URL, LOCAL_VERIFY_URL } from "../config";
import DocumentViewer from "../components/DocumentViewer";
import {
  AlertTriangle,
  Download,
  Check,
  X,
  MoreHorizontal,
  ArrowUpRight,
  MessageSquare,
  Copy,
  Info,
  Shield,
  ChevronDown,
  ChevronRight,
  FileText,
  PenLine,
} from "lucide-react";

const STAGE_LABELS = {
  uploading_source: "Saving document…",
  parsing_document: "Reading contract…",
  building_context: "Building contract context…",
  analysing_contract: "Extracting clauses and risks…",
  saving_results: "Saving results…",
  completed: "Analysis complete",
  failed: "Analysis failed",
  reconnecting: "Reconnecting to saved analysis state…",
};

const FETCH_TIMEOUT_MS = 20000;

const DocumentAnalysis = () => {
  const { id } = useParams();
  const document_id = decodeURIComponent(id);

  const [result, setResult] = useState(null);
  const [contractProfile, setContractProfile] = useState(null);
  const [contractClauses, setContractClauses] = useState([]);
  const [contractFindings, setContractFindings] = useState([]);
  const [contractReviewAudit, setContractReviewAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analysisStatus, setAnalysisStatus] = useState("loading");
  const [analysisStage, setAnalysisStage] = useState(null);
  const [error, setError] = useState(null);

  const [query, setQuery] = useState("");
  const [queryResult, setQueryResult] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [showAiNotes, setShowAiNotes] = useState(false);
  const [updatingFindingIndex, setUpdatingFindingIndex] = useState(null);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [localVerifyAvailable, setLocalVerifyAvailable] = useState(false);
  const [findingFilter, setFindingFilter] = useState("all");
  const [reviewerNotes, setReviewerNotes] = useState({});
  const [savingNoteIndex, setSavingNoteIndex] = useState(null);
  const [expandedFindings, setExpandedFindings] = useState({});
  const [overflowOpen, setOverflowOpen] = useState(null);
  const [expandedClauses, setExpandedClauses] = useState({});
  // Track which finding cards have the note area open
  const [openNoteIndices, setOpenNoteIndices] = useState({});

  const [rawText, setRawText] = useState("");
  const [activeQuote, setActiveQuote] = useState(null);
  const statusFailureCountRef = useRef(0);

  useEffect(() => {
    let pollHandle;

    setResult(null);
    setContractProfile(null);
    setContractClauses([]);
    setContractFindings([]);
    setContractReviewAudit(null);
    setReviewerNotes({});
    setRawText("");
    setActiveQuote(null);
    setError(null);
    setLoading(true);
    setAnalysisStatus("loading");
    setAnalysisStage(null);
    statusFailureCountRef.current = 0;

    const bootstrap = async () => {
      const shouldPoll = await loadDocumentState();
      if (shouldPoll) {
        pollHandle = window.setInterval(async () => {
          const keepPolling = await loadDocumentState();
          if (!keepPolling && pollHandle) {
            window.clearInterval(pollHandle);
          }
        }, 3000);
      }
    };

    bootstrap();
    setQueryResult(null);
    setQuery("");
    return () => {
      if (pollHandle) {
        window.clearInterval(pollHandle);
      }
    };
  }, [id]);

  // Close overflow on outside click
  useEffect(() => {
    const handler = () => setOverflowOpen(null);
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const checkLocalVerifier = async () => {
      try {
        const res = await fetch(`${LOCAL_VERIFY_URL}/health`);
        if (!cancelled) {
          setLocalVerifyAvailable(res.ok);
        }
      } catch {
        if (!cancelled) {
          setLocalVerifyAvailable(false);
        }
      }
    };

    checkLocalVerifier();
    return () => {
      cancelled = true;
    };
  }, []);

  const normalizeResult = (data) => {
    const realData = data.insights || data;
    const overall_confidence = realData.overall_confidence ?? realData.confidence_score ?? 0;
    const key_insights = (realData.key_insights || []).map((item) => {
      if (typeof item === "string") {
        return { insight: item, source: "Legacy analysis - no source quote available", confidence: overall_confidence };
      }
      return item;
    }).filter((item) => {
      const text = String(item?.insight || "").toLowerCase();
      if (!text) return false;
      const lowSignalPatterns = [
        "statement of work",
        "master services agreement",
        "effective date",
        "governing law",
        "the agreement is between",
        "the contract is between",
        "the contract contains",
        "the document identifies",
        "the agreement sets out",
      ];
      return !lowSignalPatterns.some((pattern) => text.includes(pattern));
    });
    const risks = (realData.risks || []).map((r) => ({
      ...r,
      source: r.source || "Legacy analysis",
      confidence: r.confidence ?? overall_confidence,
    }));
    const recommended_actions = (realData.recommended_actions || []).map((a) => ({
      ...a,
      source: a.source || "Legacy analysis",
      confidence: a.confidence ?? overall_confidence,
    }));
    return {
      ...realData,
      overall_confidence,
      key_insights,
      risks,
      recommended_actions,
      reasoning: realData.reasoning || "Reasoning not available for legacy analysis.",
      context_quality: realData.context_quality || "full",
      evaluation: data.evaluation || null,
    };
  };

  const fetchWithTimeout = async (url, options = {}) => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    try {
      return await fetch(url, {
        ...options,
        signal: controller.signal,
      });
    } finally {
      window.clearTimeout(timeoutId);
    }
  };

  const loadDocumentInsights = async () => {
    setLoading(true);
    try {
      await fetchCompletedDocument({ background: false });
      setAnalysisStatus("completed");
      setAnalysisStage("completed");
      return false;
    } finally {
      setLoading(false);
    }
  };

  const fetchCompletedDocument = async ({ background = false } = {}) => {
    if (!background) {
      setLoading(true);
    }
    setError(null);
    try {
      const [insightsRes, overviewRes, clausesRes, risksRes, auditRes] = await Promise.all([
        fetchWithTimeout(`${API_BASE_URL}/insights/${encodeURIComponent(document_id)}`),
        fetchWithTimeout(`${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/overview`),
        fetchWithTimeout(`${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/clauses`),
        fetchWithTimeout(`${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/risks`),
        fetchWithTimeout(`${API_BASE_URL}/contracts/${encodeURIComponent(document_id)}/review-audit`),
      ]);

      if (!insightsRes.ok) throw new Error("Document analysis not found");
      const data = await insightsRes.json();
      if (!data || data.error) throw new Error("Document analysis not found");

      if (overviewRes.ok) {
        setContractProfile(await overviewRes.json());
      } else {
        setContractProfile(null);
      }

      if (clausesRes.ok) {
        const clausesData = await clausesRes.json();
        setContractClauses(clausesData.clauses || []);
      } else {
        setContractClauses([]);
      }

      if (risksRes.ok) {
        const risksData = await risksRes.json();
        setContractFindings(risksData.findings || []);
        setReviewerNotes(
          Object.fromEntries(
            (risksData.findings || []).map((finding, idx) => [idx, finding.reviewer_note || ""])
          )
        );
      } else {
        setContractFindings([]);
        setReviewerNotes({});
      }

      if (auditRes.ok) {
        setContractReviewAudit(await auditRes.json());
      } else {
        setContractReviewAudit(null);
      }

      setResult(normalizeResult(data));
      setRawText(data.raw_text || "");
    } catch (err) {
      console.error("Failed to load insights", err);
      if (!background) {
        setContractProfile(null);
        setContractClauses([]);
        setContractFindings([]);
        setReviewerNotes({});
        setContractReviewAudit(null);
        setError("Failed to load document insights. Please make sure the file exists.");
      } else {
        setError("Deep Verify finished locally, but refreshing the hosted document took too long. Please refresh once.");
      }
    } finally {
      if (!background) {
        setLoading(false);
      }
    }
  };

  const loadDocumentState = async () => {
    try {
      const statusRes = await fetch(
        `${API_BASE_URL}/documents/${encodeURIComponent(document_id)}/status`
      );

      if (statusRes.ok) {
        statusFailureCountRef.current = 0;
        setError(null);
        const statusData = await statusRes.json();
        setAnalysisStatus(statusData.status || "processing");
        setAnalysisStage(statusData.stage || null);

        if (statusData.status === "queued" || statusData.status === "processing") {
          setLoading(false);
          return true;
        }

        if (statusData.status === "failed") {
          setLoading(false);
          setError(statusData.job?.error || "Document analysis failed.");
          return false;
        }
      }

      return await loadDocumentInsights();
    } catch (err) {
      console.error("Failed to load document state", err);
      statusFailureCountRef.current += 1;
      if (statusFailureCountRef.current < 5) {
        setAnalysisStatus((current) =>
          current === "completed" ? current : "processing"
        );
        setAnalysisStage("reconnecting");
        setLoading(false);
        return true;
      }

      setError("Failed to load document insights. Please make sure the file exists.");
      setLoading(false);
      return false;
    }
  };

  const handleQuery = async () => {
    if (!query || queryLoading) return;
    setQueryLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, document_id }),
      });
      if (!res.ok) throw new Error("Query failed");
      setQueryResult(await res.json());
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
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        }
      );
      if (!res.ok) throw new Error("Failed to update finding status");
      const data = await res.json();
      setContractFindings((current) =>
        current.map((finding, idx) => (idx === findingIndex ? data.finding : finding))
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
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reviewer_note: reviewerNotes[findingIndex] || "" }),
        }
      );
      if (!res.ok) throw new Error("Failed to save reviewer note");
      const data = await res.json();
      setContractFindings((current) =>
        current.map((finding, idx) => (idx === findingIndex ? data.finding : finding))
      );
    } catch (err) {
      console.error(err);
      setError("Failed to save reviewer note.");
    } finally {
      setSavingNoteIndex(null);
    }
  };

  const handleExportReport = () => {
    window.open(`${API_BASE_URL}/export/${encodeURIComponent(document_id)}`, "_blank");
  };

  const handleRunVerify = async () => {
    if (verifyLoading) return;
    setVerifyLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${LOCAL_VERIFY_URL}/verify`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            backend_url: API_BASE_URL,
            document_id,
          }),
        }
      );
      if (!res.ok) {
        let message = "Verify request failed";
        try {
          const data = await res.json();
          message = data.detail || message;
        } catch {
          // Ignore parse failures and use the default message.
        }
        throw new Error(message);
      }
      setLocalVerifyAvailable(true);
      await fetchCompletedDocument({ background: true });
    } catch (err) {
      console.error(err);
      setLocalVerifyAvailable(false);
      setError(
        "Deep Verify needs the local verifier running on your machine at 127.0.0.1:11435 with Ollama available."
      );
    } finally {
      setVerifyLoading(false);
    }
  };

  const getSeverityLabel = (severity) => {
    const s = severity?.toLowerCase();
    if (s === "high") return "Critical Risk";
    if (s === "medium") return "Moderate Risk";
    return "Minor Risk";
  };

  const getSeverityClass = (severity) => {
    const s = severity?.toLowerCase();
    if (s === "high") return "high";
    if (s === "medium") return "medium";
    return "low";
  };

  const formatDocumentType = (value) => {
    if (!value) return "Unknown";
    return value.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
  };

  const formatClauseType = (value) => {
    if (!value) return "Unclassified";
    return value.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
  };

  const formatFindingType = (value) => {
    if (!value) return "Finding";
    return value.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
  };

  const isContractReview = Boolean(contractProfile);
  const filteredFindings = contractFindings.filter((finding) =>
    findingFilter === "all" ? true : (finding.status || "open") === findingFilter
  );
  const riskFindings = filteredFindings.filter((f) => f.finding_type !== "missing_protection");
  const missingProtections = filteredFindings.filter((f) => f.finding_type === "missing_protection");

  const findingCounts = {
    all: contractFindings.length,
    open: contractFindings.filter((f) => (f.status || "open") === "open").length,
    accepted: contractFindings.filter((f) => f.status === "accepted").length,
    dismissed: contractFindings.filter((f) => f.status === "dismissed").length,
    escalated: contractFindings.filter((f) => f.status === "escalated").length,
  };

  const clauseStatusCounts = {
    present: contractClauses.filter((c) => c.clause_text || c.text_preview).length,
    missing: contractClauses.filter((c) => !c.clause_text && !c.text_preview).length,
  };

  // Derived counts for stats
  const criticalCount = contractFindings.filter(
    (f) => f.severity?.toLowerCase() === "high"
  ).length;

  // Review audit score
  const auditScore = contractReviewAudit?.score ?? (result?.evaluation?.score || 0);
  const auditStatus = contractReviewAudit?.status || result?.evaluation?.status || "pass";
  const verificationMode = result?.verification_mode || "fast_review";
  const verificationSummary = result?.verification_summary || null;

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner spinner-lg" style={{ marginBottom: "16px" }} />
        <div className="empty-state-title">Analyzing "{document_id}"</div>
        <div className="empty-state-desc">Running deep intelligence extraction…</div>
      </div>
    );
  }

  if ((analysisStatus === "queued" || analysisStatus === "processing") && !result) {
    return (
      <div className="empty-state">
        <span className="spinner spinner-lg" style={{ marginBottom: "16px" }} />
        <div className="empty-state-title">Analysis in progress</div>
        <div className="empty-state-desc">
          {analysisStage
            ? `Current stage: ${STAGE_LABELS[analysisStage] || analysisStage.replaceAll("_", " ")}`
            : "Your document is being processed and saved."}
        </div>
      </div>
    );
  }

  if (error && !result) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon"><AlertTriangle /></div>
        <div className="empty-state-title">Something went wrong</div>
        <div className="empty-state-desc">{error}</div>
        <button className="btn btn-primary" onClick={loadDocumentState} style={{ marginTop: "16px" }}>
          Retry Analysis
        </button>
      </div>
    );
  }

  /* ============================
     RENDER: Progress Ring
     ============================ */
  const renderProgressRing = (value, size = 64, stroke = 5) => {
    const radius = (size - stroke) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (value / 100) * circumference;
    const color = value >= 80 ? "var(--success)" : value >= 50 ? "var(--warning)" : "var(--danger)";

    return (
      <div className="progress-ring" style={{ width: size, height: size }}>
        <svg width={size} height={size}>
          <circle className="progress-ring-bg" cx={size / 2} cy={size / 2} r={radius} strokeWidth={stroke} />
          <circle
            className="progress-ring-fill"
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={stroke}
            stroke={color}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <span className="progress-ring-text" style={{ fontSize: "16px" }}>{value}%</span>
      </div>
    );
  };

  /* ============================
     RENDER: Finding Card
     ============================ */
  const renderFindingCard = (finding, idx, isMissing = false) => {
    const sev = getSeverityClass(finding.severity);
    const isExpanded = expandedFindings[idx];
    const isNoteOpen = openNoteIndices[idx];

    return (
      <div key={`${finding.title}-${idx}`} className={`finding-card severity-${sev}`}>
        {/* Header */}
        <div className="finding-header">
          <div className="finding-title-group">
            <span className={`badge badge-${sev}`}>{getSeverityLabel(finding.severity)}</span>
            <span className="finding-title">{finding.title}</span>
          </div>
          <div className="finding-badges">
            <span className="badge badge-neutral">{formatFindingType(finding.finding_type)}</span>
            {finding.status && finding.status !== "open" && (
              <span className="badge badge-info">{formatDocumentType(finding.status)}</span>
            )}
          </div>
        </div>

        {/* Description */}
        <div
          className={`finding-description ${isExpanded ? "expanded" : ""}`}
          onClick={() => setExpandedFindings((prev) => ({ ...prev, [idx]: !prev[idx] }))}
          style={{ cursor: "pointer" }}
          title={isExpanded ? "Click to collapse" : "Click to expand"}
        >
          {finding.explanation}
        </div>

        {/* Clause type badge */}
        {finding.clause_type && (
          <div style={{ marginBottom: "8px" }}>
            <span className="badge badge-neutral" style={{ fontSize: "11px" }}>
              {formatClauseType(finding.clause_type)}
            </span>
          </div>
        )}

        {/* Source quotes — strip internal prefixes before display */}
        {finding.source_quotes?.map((quote, quoteIdx) => (
          <div
            key={quoteIdx}
            className="source-quote"
            onClick={() => setActiveQuote(quote)}
            title="Click to verify in source document"
          >
            "{cleanQuote(quote)}"
          </div>
        ))}

        {/* Mitigation */}
        {finding.mitigation_fix && (
          <div className={`mitigation-box ${isMissing ? "warning" : ""}`}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className={`mitigation-label ${isMissing ? "warning" : "success"}`}>
                {isMissing ? "Suggested Mitigation Language" : "Suggested Drafting Fix"}
              </span>
              <button
                className="mitigation-copy"
                onClick={() => {
                  navigator.clipboard.writeText(finding.mitigation_fix);
                }}
              >
                <Copy /> Copy
              </button>
            </div>
            <p className="mitigation-text">{finding.mitigation_fix}</p>
          </div>
        )}

        {/* Actions Row */}
        <div className="finding-actions">
          <button
            className="btn btn-primary btn-sm"
            disabled={updatingFindingIndex === idx}
            onClick={() => handleFindingStatusUpdate(idx, "accepted")}
          >
            <Check /> Accept
          </button>
          <button
            className="btn btn-ghost btn-sm"
            disabled={updatingFindingIndex === idx}
            onClick={() => handleFindingStatusUpdate(idx, "dismissed")}
          >
            Dismiss
          </button>
          <div className="overflow-menu" onClick={(e) => e.stopPropagation()}>
            <button
              className="overflow-trigger"
              onClick={() => setOverflowOpen(overflowOpen === idx ? null : idx)}
            >
              ···
            </button>
            {overflowOpen === idx && (
              <div className="overflow-dropdown">
                <button onClick={() => { handleFindingStatusUpdate(idx, "negotiate"); setOverflowOpen(null); }}>
                  <MessageSquare /> Negotiate
                </button>
                <button onClick={() => { handleFindingStatusUpdate(idx, "escalated"); setOverflowOpen(null); }}>
                  <ArrowUpRight /> Escalate
                </button>
              </div>
            )}
          </div>
          <div style={{ flex: 1 }} />
          <span className="finding-confidence">
            Grounded: {(finding.confidence * 100).toFixed(0)}%
          </span>
        </div>

        {/* Reviewer Note — collapsed behind "Add Note" toggle */}
        <button
          className="reviewer-note-toggle"
          onClick={() =>
            setOpenNoteIndices((prev) => ({ ...prev, [idx]: !prev[idx] }))
          }
        >
          <PenLine />
          {isNoteOpen
            ? "Hide Note"
            : reviewerNotes[idx]
              ? "Edit Note"
              : "Add Note"}
        </button>

        {isNoteOpen && (
          <div className="reviewer-note-area reviewer-note-area-expanded">
            <textarea
              value={reviewerNotes[idx] || ""}
              onChange={(e) =>
                setReviewerNotes((current) => ({ ...current, [idx]: e.target.value }))
              }
              placeholder="Add review note…"
              rows={2}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "6px" }}>
              <button
                className="btn btn-secondary btn-sm"
                disabled={savingNoteIndex === idx}
                onClick={() => handleReviewerNoteSave(idx)}
              >
                {savingNoteIndex === idx ? "…" : "Save Note"}
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Strip internal data prefixes from source quotes before display
  const cleanQuote = (text) => {
    if (!text) return text;
    return String(text)
      .replace(/^DERIVED_FROM_MISSING:\s*/i, "")
      .replace(/^MISSING_CLAUSE:\s*/i, "")
      .trim();
  };

  return (
    <div
      className="analysis-page"
      style={{
        marginRight: chatOpen ? "420px" : "0",
        transition: "margin-right 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
      }}
    >

      {/* ===== STICKY ANALYSIS HEADER ===== */}
      <div className="analysis-header">
        <div className="analysis-header-doc">
          <div className="analysis-header-doc-icon">
            <FileText />
          </div>
          <div style={{ minWidth: 0 }}>
            <div
              className="analysis-header-filename"
              title={document_id}
            >
              {document_id}
            </div>
            <div className="analysis-header-meta">
              {contractProfile?.document_type && (
                <span className="badge badge-neutral" style={{ fontSize: "11px" }}>
                  {formatDocumentType(contractProfile.document_type)}
                </span>
              )}
              {contractProfile?.governing_law && (
                <span style={{ fontSize: "11px", color: "var(--text-faint)" }}>
                  {contractProfile.governing_law}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Audit score as a small pill badge in header — not the hero */}
        {auditStatus !== "deferred" ? (
          <span
            className={`badge ${auditScore >= 80 ? "badge-low" : auditScore >= 50 ? "badge-medium" : "badge-high"}`}
            style={{ fontSize: "12px", flexShrink: 0 }}
            title={`Analysis Quality Score: ${auditScore}/100`}
          >
            <Shield size={11} /> {auditScore}/100
          </span>
        ) : (
          <span className="badge badge-neutral" style={{ fontSize: "12px", flexShrink: 0 }}>
            Fast Review
          </span>
        )}

        {/* Action buttons — always visible in header */}
        <div className="analysis-header-actions">
          {isContractReview && result && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setChatOpen((prev) => !prev)}
              title="Open document-specific assistant"
            >
              <MessageSquare />
              <span>{chatOpen ? "Close Chat" : "Document Chat"}</span>
            </button>
          )}
          <button
            className="btn btn-ghost btn-sm"
            onClick={handleRunVerify}
            disabled={verifyLoading}
            title={
              localVerifyAvailable
                ? "Use your local Ollama setup to enrich the audit."
                : "Start the local verifier service on your machine to enable Deep Verify."
            }
          >
            <Shield />
            <span>{verifyLoading ? "Verifying…" : "Deep Verify"}</span>
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleExportReport}>
            <Download />
            <span>Export Report</span>
          </button>
        </div>
      </div>

      {/* ===== ERROR BANNER ===== */}
      {error && (
        <div className="error-banner">
          <AlertTriangle /> {error}
        </div>
      )}

      {/* Context warning shown ONCE — inside Contract Overview card only. Removed from here. */}

      {/* ===== REJECTION UI (Non-Legal Document) ===== */}
      {contractProfile?.is_legal_document === false && (
        <div className="card" style={{ border: '2px solid var(--danger)', background: 'rgba(239, 68, 68, 0.05)', marginBottom: 'var(--section-gap)' }}>
          <div className="card-body" style={{ textAlign: 'center', padding: '48px 24px' }}>
            <div style={{ color: 'var(--danger)', marginBottom: '16px' }}>
              <AlertTriangle size={48} />
            </div>
            <div className="empty-state-title" style={{ fontSize: '20px', color: 'var(--danger)', fontWeight: 600 }}>
              Non-Legal Document Detected
            </div>
            <p className="empty-state-desc" style={{ maxWidth: '600px', margin: '12px auto 24px', fontSize: '15px' }}>
              JuriSight is a specialized legal intelligence platform optimized for formal legal agreements (NDAs, MSAs, SOWs, etc.).
              <br /><br />
              This document does not appear to contain a standard contractual structure or binding legal relationship. To protect the accuracy of your audits, we have skipped the legal analysis for this file.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                className="btn btn-secondary"
                onClick={() => window.history.back()}
              >
                Go Back
              </button>
              <button
                className="btn btn-primary"
                onClick={() => window.location.href = '/'}
              >
                Return to Dashboard
              </button>
            </div>

            {result?.summary && (
              <div style={{ marginTop: '32px', textAlign: 'left', borderTop: '1px solid var(--border-default)', paddingTop: '24px' }}>
                <div className="card-title" style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-primary)' }}>General Summary (Informational Only)</div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: '1.6' }}>{result.summary}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== KPI STATS ROW — 3 cards, findings are the hero ===== */}
      {contractProfile?.is_legal_document !== false && (
        <div className="stats-row" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          <div className="stat-card stat-card-findings">
            <div className="stat-label">
              {isContractReview ? "Review Findings" : "Grounded Insights"}
            </div>
            <div className="stat-value">
              {isContractReview ? contractFindings.length : (result.key_insights?.length || 0)}
            </div>
          </div>
          <div className="stat-card stat-card-critical">
            <div className="stat-label">Critical Risks</div>
            <div
              className="stat-value"
              style={{ color: criticalCount > 0 ? "var(--danger)" : "var(--text-primary)" }}
            >
              {criticalCount}
            </div>
          </div>
          <div className="stat-card stat-card-clauses">
            <div className="stat-label">Avg Confidence</div>
            <div className="stat-value">
              {`${(result.overall_confidence * 100).toFixed(0)}%`}
            </div>
          </div>
        </div>
      )}

      {/* ===== CONTRACT OVERVIEW ===== */}
      {contractProfile && (
        <div className="card" style={{ marginBottom: "var(--section-gap)" }}>
          <div className="card-header">
            <div className="card-title">Contract Overview</div>
          </div>
          <div className="card-body">

            {/* Parties Banner — prominent at top */}
            {contractProfile.parties?.length > 0 && (
              <div className="parties-banner">
                <span className="parties-banner-label">Parties</span>
                {contractProfile.parties.map((party, idx) => (
                  <span key={`${party}-${idx}`} className="party-tag">{party}</span>
                ))}
              </div>
            )}

            {/* Context warning — shown ONCE, here only */}
            {result.context_quality && result.context_quality !== "full" && (
              <div className="context-notice" style={{ marginBottom: "16px" }}>
                <Info />
                <span className="context-notice-text">
                  <strong>Partial context:</strong>{" "}
                  {result.context_gap || "The document context may be incomplete."}
                </span>
              </div>
            )}

            <div className="overview-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
              <div>
                <div className="overview-field-label">Document Type</div>
                <div className="overview-field-value">{formatDocumentType(contractProfile.document_type)}</div>
              </div>
              <div>
                <div className="overview-field-label">Classification Confidence</div>
                <div className="overview-field-value">{((contractProfile.classification_confidence || 0) * 100).toFixed(0)}%</div>
              </div>
              <div>
                <div className="overview-field-label">Effective Date</div>
                <div className="overview-field-value">{contractProfile.effective_date || "Not detected"}</div>
              </div>
              <div>
                <div className="overview-field-label">Governing Law</div>
                <div className="overview-field-value">{contractProfile.governing_law || "Not detected"}</div>
              </div>
              <div>
                <div className="overview-field-label">Term Length</div>
                <div className="overview-field-value">{contractProfile.term_length || "Not detected"}</div>
              </div>
              <div>
                <div className="overview-field-label">Renewal Mechanics</div>
                <div className="overview-field-value">{contractProfile.renewal_mechanics || "Not detected"}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===== EXECUTIVE SUMMARY ===== */}
      {result?.summary && (
        <div className="card" style={{ marginBottom: "var(--section-gap)" }}>
          <div className="card-header">
            <div className="card-title">
              {isContractReview ? "AI Research: Summary" : "Executive Summary"}
            </div>
          </div>
          <div className="card-body">
            <p style={{ fontSize: "14px", color: "var(--text-body)", lineHeight: "1.7" }}>
              {result.summary}
            </p>
          </div>
        </div>
      )}

      {/* ===== CONTRACT REVIEW FINDINGS ===== */}
      {contractFindings.length > 0 && (
        <div className="card" style={{ marginBottom: "var(--section-gap)" }}>
          <div className="card-header">
            <div className="card-title">Contract Review Findings</div>
            <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              {contractFindings.length} total
            </span>
          </div>
          <div className="card-body">
            <div className="filter-bar">
              {[
                ["all", "All"],
                ["open", "Open"],
                ["accepted", "Accepted"],
                ["dismissed", "Dismissed"],
                ["escalated", "Escalated"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  className={`filter-btn ${findingFilter === value ? "active" : ""}`}
                  onClick={() => setFindingFilter(value)}
                >
                  {label} ({findingCounts[value]})
                </button>
              ))}
            </div>

            {riskFindings.length > 0 && (
              <div style={{ marginBottom: "20px" }}>
                <div style={{
                  fontSize: "13px",
                  fontWeight: 500,
                  color: "var(--text-muted)",
                  marginBottom: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px"
                }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--danger)", flexShrink: 0 }} />
                  Risk Findings ({riskFindings.length})
                </div>
                {riskFindings.map((finding) => {
                  const idx = contractFindings.indexOf(finding);
                  return renderFindingCard(finding, idx, false);
                })}
              </div>
            )}

            {missingProtections.length > 0 && (
              <div>
                <div style={{
                  fontSize: "13px",
                  fontWeight: 500,
                  color: "var(--text-muted)",
                  marginBottom: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px"
                }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--warning)", flexShrink: 0 }} />
                  Missing Protections ({missingProtections.length})
                </div>
                {missingProtections.map((finding) => {
                  const idx = contractFindings.indexOf(finding);
                  return renderFindingCard(finding, idx, true);
                })}
              </div>
            )}

            {filteredFindings.length === 0 && (
              <p style={{ fontSize: "13px", color: "var(--text-muted)", padding: "12px 0" }}>
                No findings match this filter.
              </p>
            )}
          </div>
        </div>
      )}

      {/* ===== CLAUSE INVENTORY ===== */}

      {contractClauses.length > 0 && (
        <div className="card" style={{ marginBottom: "var(--section-gap)" }}>
          <div className="card-header">
            <div className="card-title">Clause Inventory</div>
            <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              <span style={{ color: "var(--success)", fontWeight: 500 }}>{clauseStatusCounts.present}</span> present ·{" "}
              <span style={{ color: "var(--danger)", fontWeight: 500 }}>{clauseStatusCounts.missing}</span> missing
            </span>
          </div>
          <div className="card-body">
            {contractClauses.map((clause, idx) => {
              const hasContent = clause.clause_text || clause.text_preview;
              const status = hasContent ? "present" : "missing";
              const isOpen = expandedClauses[idx];
              return (
                <div key={`${idx}-${clause.title}`}>
                  <div
                    className="clause-row"
                    onClick={() => setExpandedClauses((prev) => ({ ...prev, [idx]: !prev[idx] }))}
                  >
                    <span style={{ color: "var(--text-muted)", width: "16px", display: "flex", alignItems: "center" }}>
                      {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </span>
                    <span className="clause-name">{clause.title}</span>
                    <span className={`badge badge-${status}`}>
                      {status === "present" ? "Present" : "Missing"}
                    </span>
                    <span className="clause-ref">Page {clause.page_number}</span>
                  </div>
                  {isOpen && hasContent && (
                    <div className="clause-expanded">
                      {clause.text_preview || clause.clause_text}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ===== ANALYSIS QUALITY CHECK ===== */}
      {(contractReviewAudit || result.evaluation) && (
        <div className={`quality-card ${auditStatus === "pass" ? "pass" : "fail"}`}>
          <div className="quality-header">
            <div>
              <div className="card-title" style={{ marginBottom: "4px" }}>
                <Shield size={16} />
                Analysis Quality
              </div>
              <span className={`badge ${auditStatus === "pass" ? "badge-low" : auditStatus === "deferred" ? "badge-neutral" : "badge-high"}`} style={{ textTransform: "uppercase" }}>
                {auditStatus === "pass" ? "Verified" : auditStatus === "deferred" ? "Fast Review" : "Review Required"}
              </span>
            </div>
            <div className="quality-score">
              {auditStatus === "deferred" ? "Deferred" : `${auditScore}/100`}
            </div>
          </div>

          <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "8px", lineHeight: "1.5" }}>
            {verificationMode === "local_ollama"
              ? "Deep Verify was completed with your local Ollama setup."
              : "This document currently shows the hosted Fast Review pass. Run Deep Verify from a machine with the local verifier and Ollama to enrich the audit."}
          </p>

          {verificationSummary && (
            <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "12px", lineHeight: "1.5" }}>
              {verificationSummary}
            </p>
          )}

          {contractReviewAudit?.grounding_score !== undefined && (
            <div className="quality-metrics">
              <div className="quality-metric">
                <div className="quality-metric-value">{((contractReviewAudit.grounding_score || 0) * 100).toFixed(0)}%</div>
                <div className="quality-metric-label">Grounding</div>
              </div>
              <div className="quality-metric">
                <div className="quality-metric-value">{((contractReviewAudit.structure_score || 0) * 100).toFixed(0)}%</div>
                <div className="quality-metric-label">Structure</div>
              </div>
              <div className="quality-metric">
                <div className="quality-metric-value">{((contractReviewAudit.coverage_score || 0) * 100).toFixed(0)}%</div>
                <div className="quality-metric-label">Coverage</div>
              </div>
            </div>
          )}

          {(contractReviewAudit?.recommendation || result.evaluation?.recommendation) && (
            <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "12px", lineHeight: "1.5" }}>
              {contractReviewAudit?.recommendation || result.evaluation?.recommendation}
            </p>
          )}
        </div>
      )}

      {/* ===== AI RESEARCH NOTES (always visible, collapsible) ===== */}
      {result && (
        <div style={{ marginBottom: "var(--section-gap)" }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: showAiNotes ? "16px" : "0"
          }}>
            <div style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-primary)" }}>
              {isContractReview ? "AI Research Notes" : "Key Insights & Actions"}
            </div>
            <button
              className={`section-collapse-btn ${showAiNotes ? "" : "collapsed"}`}
              onClick={() => setShowAiNotes((prev) => !prev)}
            >
              <ChevronDown />
              {showAiNotes ? "Collapse" : "Expand"}
            </button>
          </div>

          {showAiNotes && (
            <div className="two-col-grid">
              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    {isContractReview ? "Strategic Insights" : "Key Insights"}
                  </div>
                </div>
                <div className="card-body">
                  {result.key_insights?.length ? (
                    result.key_insights.map((i, idx) => (
                      <div key={idx} className="insight-feed-item">
                        <span className="insight-severity-dot low" />
                        <div>
                          <div className="insight-feed-text">{i.insight}</div>
                          <div className="source-quote" style={{ margin: "6px 0 0", cursor: "default" }}>
                            "{i.source}"
                          </div>
                          <div style={{ fontSize: "12px", color: "var(--text-faint)", marginTop: "4px" }}>
                            Grounded: {(i.confidence * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.6" }}>
                      No distinct strategic insights were generated beyond the contract overview and review findings.
                    </p>
                  )}
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">
                    {isContractReview ? "Recommended Actions" : "Recommended Actions"}
                  </div>
                </div>
                <div className="card-body">
                  {result.recommended_actions?.map((a, idx) => (
                    <div key={idx} className="insight-feed-item">
                      <span className="insight-severity-dot medium" />
                      <div style={{ flex: 1 }}>
                        <span className="insight-feed-text" style={{ fontWeight: 500 }}>{a.action}</span>
                        <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: "4px 0" }}>{a.rationale}</p>
                        <div className="source-quote" style={{ margin: "4px 0 0", cursor: "default" }}>"{a.source}"</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ===== LEGAL DISCLAIMER ===== */}
      <div className="legal-disclaimer">
        <p>
          <strong>IMPORTANT NOTICE:</strong> This report is generated by the JuriSight Legal Intelligence Engine exclusively to assist attorneys in their review process.
          It does <strong>NOT</strong> constitute legal advice, form an attorney-client relationship, or substitute human legal judgment.
          Artificial Intelligence can hallucinate, omit critical context, or misinterpret drafting intent.
          You must verify all findings, missing protections, and source quotes manually against the primary document before advising clients.
        </p>
      </div>

      {/* ===== DOCUMENT VIEWER (source verification modal) ===== */}
      <DocumentViewer
        rawText={rawText}
        highlightQuote={activeQuote}
        onClose={() => setActiveQuote(null)}
      />

      {/* ===== DOCUMENT CHAT DRAWER ===== */}
      <div className={`chat-drawer ${chatOpen ? "open" : ""}`}>
        <div className="chat-drawer-header">
          <div>
            <div className="qa-title">Document Chat</div>
            <div className="qa-subtitle" style={{ marginBottom: 0 }}>
              Ask focused questions about this specific agreement.
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => setChatOpen(false)}>
            <X size={16} />
          </button>
        </div>

        <div className="chat-drawer-body">
          {queryResult && queryResult.reasoning && (
            <div className="reasoning-block">
              <strong>Thought Process</strong>
              <p>{queryResult.reasoning}</p>
            </div>
          )}

          {queryResult && queryResult.context_quality !== "full" && (
            <div className="context-notice">
              <AlertTriangle />
              <span className="context-notice-text">
                <strong>Partial Context:</strong> {queryResult.context_gap}
              </span>
            </div>
          )}

          {!queryResult && (
            <div className="qa-chips">
              {[
                "What is the liability cap?",
                "Is there a non-compete clause?",
                "What are the termination rights?",
              ].map((q) => (
                <button
                  key={q}
                  className="qa-chip"
                  onClick={() => { setQuery(q); }}
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {queryResult && (
            <div className="qa-response">
              <div className="qa-response-header">
                <Shield size={14} /> Grounded Intelligence Answer
              </div>
              <div className="qa-response-text">
                {queryResult.answer || queryResult.summary}
              </div>

              {queryResult.citations?.length > 0 && (
                <div className="qa-citations">
                  <div className="qa-citations-label">Supporting Evidence (Verbatim)</div>
                  {queryResult.citations.map((cite, i) => (
                    <div key={i} style={{ marginBottom: "12px" }}>
                      <div
                        className="source-quote"
                        onClick={() => setActiveQuote(cite.quote)}
                        title="Click to verify in source"
                      >
                        "{cite.quote}"
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic", paddingLeft: "14px", marginTop: "2px" }}>
                        — {cite.relevance}
                      </div>
                    </div>
                  ))}
                  <div style={{ textAlign: "right" }}>
                    <span className="finding-confidence">
                      Grounded: {(queryResult.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              )}

              {!queryResult.citations && queryResult.key_insights?.length > 0 && (
                <div className="qa-citations">
                  <div className="qa-citations-label">Supporting Evidence</div>
                  {queryResult.key_insights.map((ins, i) => (
                    <div key={i} style={{ marginBottom: "8px" }}>
                      <div className="source-quote" style={{ cursor: "default" }}>"{ins.source}"</div>
                      <div style={{ textAlign: "right", fontSize: "12px", color: "var(--text-faint)", marginTop: "2px" }}>
                        Grounded: {(ins.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="chat-drawer-input-area">
          <div className="qa-input-row">
            <input
              className="qa-input"
              placeholder={
                contractProfile
                  ? "e.g., What is the governing law? Is there a termination right?"
                  : "e.g., Extract the implementation plan from section 4."
              }
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleQuery()}
              disabled={queryLoading}
            />
            <button
              className="btn btn-primary"
              onClick={handleQuery}
              disabled={queryLoading}
            >
              {queryLoading ? <span className="spinner" /> : "Ask"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentAnalysis;
