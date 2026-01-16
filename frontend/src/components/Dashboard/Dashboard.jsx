import React, { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Microscope,
  Plus,
  Zap,
  FileUp,
  CheckCircle2,
  X,
  Send,
  Sparkles,
  Cpu,
  Play,
  ExternalLink,
  Loader2,
  LogOut,
  ClipboardCheck,
  FileText,
} from "lucide-react";
import api from "../../api";
import "./Dashboard.css";
import PdfAnalyzer from "./PdfAnalyzer";

// ==================================================================================
// [Component 1] LeftPanel: 세션, 라이브러리 및 리포트 목록 관리
// ==================================================================================
const LeftPanel = React.memo(
  ({
    sessions,
    currentSessionId,
    leftTab,
    setLeftTab,
    references,
    viewingRef,
    reports,
    viewingReport,
    onSelectSession,
    onCreateSessionTrigger,
    onRemoveSession,
    onToggleRef,
    onRemoveRef,
    onSelectRef,
    onSelectReport,
    onUploadTrigger,
    onRetrievalTrigger,
    onReportTrigger,
    onLogout,
  }) => {
    const fileInputRef = useRef(null);

    return (
      <section className="left-panel">
        <div className="brand-header">
          <div className="logo-box">
            <Microscope size={22} color="white" />
          </div>
          <div className="brand-text">
            <h1>TV-A</h1>
            <p>Bio-Terminal</p>
          </div>
        </div>
        <div className="session-info">
          <p className="session-label">Current Session</p>
          <p className="session-value">
            {sessions.find((s) => s.id === currentSessionId)?.title ||
              "Select Session"}
          </p>
        </div>
        <div className="tab-container">
          <div className="tab-group">
            {["session", "library", "report"].map((tab) => (
              <button
                key={tab}
                onClick={() => setLeftTab(tab)}
                className={`tab-btn ${leftTab === tab ? "active" : ""}`}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <div className="list-area custom-scrollbar">
          {leftTab === "session" && (
            <>
              <button
                className="btn-primary"
                style={{ width: "100%", marginBottom: "16px" }}
                onClick={onCreateSessionTrigger}
              >
                <Plus size={14} /> New Session
              </button>
              {sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => onSelectSession(s.id)}
                  className={`item-card ${
                    currentSessionId === s.id ? "active" : ""
                  }`}
                >
                  <button
                    className="delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveSession(s.id);
                    }}
                  >
                    <X size={12} />
                  </button>
                  <div className="card-content">
                    <div className="item-info">
                      <div className="item-title">{s.title}</div>
                      <div className="item-meta">
                        <span className="badge">
                          {new Date(s.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
          {leftTab === "library" && (
            <>
              <button
                className="btn-primary"
                style={{ width: "100%", marginBottom: "10px" }}
                onClick={onRetrievalTrigger}
                disabled={!currentSessionId}
              >
                <Zap size={14} /> Retrieval Agent
              </button>
              <div className="upload-group">
                <button
                  className="btn-secondary"
                  style={{ width: "100%" }}
                  onClick={() =>
                    currentSessionId && fileInputRef.current.click()
                  }
                  disabled={!currentSessionId}
                >
                  <FileUp size={14} /> Local File Upload
                </button>
                <input
                  type="file"
                  multiple
                  hidden
                  ref={fileInputRef}
                  onChange={(e) => {
                    if (e.target.files?.length) onUploadTrigger(e.target.files);
                    e.target.value = "";
                  }}
                />
              </div>
              {references.map((ref) => (
                <div
                  key={ref.id}
                  className={`item-card ${
                    viewingRef?.id === ref.id ? "active" : ""
                  }`}
                  onClick={() => onSelectRef(ref)}
                >
                  <button
                    className="delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveRef(ref);
                    }}
                  >
                    <X size={12} />
                  </button>
                  <div className="card-content">
                    <div
                      className={`checkbox-icon ${
                        ref.checked ? "checked" : ""
                      }`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleRef(ref);
                      }}
                    >
                      {ref.checked ? (
                        <CheckCircle2 size={18} />
                      ) : (
                        <div
                          style={{
                            width: "16px",
                            height: "16px",
                            border: "2px solid #cbd5e1",
                            borderRadius: "50%",
                          }}
                        ></div>
                      )}
                    </div>
                    <div className="item-info">
                      <div className="item-title">{ref.title}</div>
                      <div className="item-meta">
                        <span className="badge">{ref.itemType}</span>
                        {ref.status === "indexed" && (
                          <span className="badge analyzed">Analyzed</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
          {leftTab === "report" && (
            <div
              className="report-container"
              style={{ display: "flex", flexDirection: "column", gap: "12px" }}
            >
              <button
                className="btn-primary"
                onClick={onReportTrigger}
                disabled={!currentSessionId}
              >
                <Sparkles size={14} /> Synthesizer Agent
              </button>
              <div className="report-list">
                {reports.length === 0 ? (
                  <div className="empty-state" style={{ marginTop: "20px" }}>
                    <ClipboardCheck
                      size={32}
                      style={{ opacity: 0.3, marginBottom: "12px" }}
                    />
                    <p style={{ fontSize: "12px" }}>
                      Reports will be archived here.
                    </p>
                  </div>
                ) : (
                  reports.map((rpt) => (
                    <div
                      key={rpt.id}
                      className={`item-card ${
                        viewingReport?.id === rpt.id ? "active" : ""
                      }`}
                      onClick={() => onSelectReport(rpt)}
                    >
                      <div className="card-content">
                        <FileText
                          size={18}
                          color={
                            viewingReport?.id === rpt.id
                              ? "var(--primary)"
                              : "#cbd5e1"
                          }
                        />
                        <div className="item-info">
                          <div className="item-title">
                            {rpt.user_context.slice(0, 20)}...
                          </div>
                          <div className="item-meta">
                            <span className="badge">
                              {new Date(rpt.created_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
        <div className="panel-footer">
          <button className="logout-btn" onClick={onLogout}>
            <LogOut size={14} /> Logout
          </button>
        </div>
      </section>
    );
  }
);

// ==================================================================================
// [Component 2] CenterPanel: 리포트 탭 뷰어 포함
// ==================================================================================
const CenterPanel = React.memo(
  ({
    viewingRef,
    viewingReport,
    centerTab,
    setCenterTab,
    pdfUrl,
    isPdfLoading,
    summaryContent,
    isSummaryLoading,
    highlightText,
  }) => {
    return (
      <section className="center-panel">
        <div className="center-header">
          {["original", "analysis", "summary", "report"].map((tab) => (
            <button
              key={tab}
              onClick={() => setCenterTab(tab)}
              className={`nav-tab ${centerTab === tab ? "active" : ""}`}
            >
              {tab.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="content-area custom-scrollbar">
          {centerTab === "report" ? (
            !viewingReport ? (
              <div className="empty-state">
                목록에서 리포트를 선택해 주세요.
              </div>
            ) : (
              <div className="doc-paper">
                <div className="doc-header-meta">
                  Synthesized Research Report
                </div>
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {viewingReport.final_report}
                  </ReactMarkdown>
                </div>
              </div>
            )
          ) : !viewingRef ? (
            <div className="empty-state">문서를 선택해 주세요.</div>
          ) : (
            <div style={{ height: "100%" }}>
              {centerTab === "original" && (
                <div
                  className="pdf-viewer-container"
                  style={{ height: "100%" }}
                >
                  {isPdfLoading ? (
                    <div className="loading-state">
                      <Loader2 className="animate-spin" size={32} />
                    </div>
                  ) : pdfUrl ? (
                    <iframe
                      src={pdfUrl}
                      className="pdf-frame"
                      title="PDF-Original"
                    />
                  ) : (
                    <div className="doc-paper">
                      <h1>{viewingRef.title}</h1>
                      <p>
                        {viewingRef.abstract || "PDF를 불러올 수 없습니다."}
                      </p>
                    </div>
                  )}
                </div>
              )}
              {centerTab === "analysis" && (
                <div
                  className="pdf-viewer-container"
                  style={{ height: "100%" }}
                >
                  {isPdfLoading ? (
                    <div className="loading-state">
                      <Loader2 className="animate-spin" size={32} />
                    </div>
                  ) : pdfUrl ? (
                    <PdfAnalyzer
                      fileUrl={pdfUrl}
                      highlightText={highlightText}
                    />
                  ) : (
                    <div className="doc-paper">
                      <h1>{viewingRef.title}</h1>
                      <p>분석 가능한 본문 데이터가 없습니다.</p>
                    </div>
                  )}
                </div>
              )}
              {centerTab === "summary" && (
                <div className="summary-view" style={{ height: "100%" }}>
                  {isSummaryLoading ? (
                    <div className="loading-state">
                      <Loader2 className="animate-spin" size={32} />
                    </div>
                  ) : (
                    <div className="doc-paper">
                      <div className="doc-header-meta">
                        AI Generated Summary
                      </div>
                      <div
                        className="markdown-body"
                        style={{ marginTop: "20px" }}
                      >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {summaryContent ||
                            "이 파일에 대해 생성된 요약 정보가 아직 없습니다."}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    );
  }
);

// ==================================================================================
// [Component 3] RightPanel: 로직 유지
// ==================================================================================
const RightPanel = React.memo(
  ({
    messages,
    isWaiting,
    onSendMessage,
    onExecuteHighlight,
    onConfirmAction,
    onCancelAction,
  }) => {
    const scrollRef = useRef(null);
    useEffect(() => {
      if (scrollRef.current)
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }, [messages]);

    return (
      <section className="right-panel">
        <div className="agent-header">
          <div className="agent-info">
            <Sparkles size={16} />
            <span className="agent-name">Bio-Insight Agent</span>
          </div>
        </div>
        <div className="chat-area custom-scrollbar" ref={scrollRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg-row ${m.role}`}>
              {m.role === "ai" && (
                <div className="ai-avatar">
                  <Cpu size={18} />
                </div>
              )}
              <div className={`msg-bubble ${m.role}`}>
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content}
                  </ReactMarkdown>
                  {m.isProposal && (
                    <div
                      style={{ display: "flex", gap: "8px", marginTop: "10px" }}
                    >
                      <button
                        className="mini-btn"
                        onClick={() =>
                          onConfirmAction?.(m.agentType, m.analysisData)
                        }
                        disabled={isWaiting}
                      >
                        <Play size={12} /> Confirm
                      </button>
                      <button
                        className="mini-btn"
                        onClick={() => onCancelAction?.()}
                        disabled={isWaiting}
                      >
                        <X size={12} /> Cancel
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {isWaiting && (
            <div className="msg-row ai">
              <div className="ai-avatar">
                <Loader2 className="animate-spin" size={18} />
              </div>
              <div className="msg-bubble ai">생각 중...</div>
            </div>
          )}
        </div>
        <div className="input-area">
          <div className={`input-wrapper ${isWaiting ? "disabled" : ""}`}>
            <textarea
              className="chat-textarea"
              placeholder="연구 데이터에 대해 질문하세요..."
              rows={1}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSendMessage(e.target.value);
                  e.target.value = "";
                }
              }}
              disabled={isWaiting}
            />
            <button className="send-icon-btn" disabled={isWaiting}>
              <Send size={16} />
            </button>
          </div>
        </div>
      </section>
    );
  }
);

// ==================================================================================
// [Main] Dashboard: 로직 통합 및 에러 방지
// ==================================================================================
const Dashboard = ({ onLogout }) => {
  const [highlightText, setHighlightText] = useState("");
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [references, setReferences] = useState([]);
  const [reports, setReports] = useState([]);
  const [viewingReport, setViewingReport] = useState(null);
  const [leftTab, setLeftTab] = useState("library");
  const [centerTab, setCenterTab] = useState("analysis");
  const [viewingRef, setViewingRef] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const [summaryContent, setSummaryContent] = useState("");
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);

  // Modals State
  const [showRetrievalModal, setShowRetrievalModal] = useState(false);
  const [retrievalQuery, setRetrievalQuery] = useState("");
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [newSessionTitle, setNewSessionTitle] = useState("");
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportInstruction, setReportInstruction] = useState("");

  const fetchSessionData = useCallback(async (sessionId) => {
    if (!sessionId) return;
    try {
      const [msgRes, filesRes, candidatesRes, selectionsRes] =
        await Promise.all([
          api.get(`/sessions/${sessionId}/messages`),
          api.get(`/sessions/${sessionId}/files`),
          api.get(`/sessions/${sessionId}/research/candidates`),
          api.get(`/sessions/${sessionId}/selections`),
        ]);
      setMessages(msgRes.data || []);

      // 리포트 API는 별도로 호출하여 에러 시 라이브러리 목록에 영향을 주지 않도록 함
      try {
        const reportsRes = await api.get(`/sessions/${sessionId}/reports`);
        setReports(reportsRes.data || []);
      } catch (err) {
        setReports([]);
      }

      const selectedIds = new Set(
        (selectionsRes.data || []).map((s) => s.item_id)
      );
      const processItems = (items, type) =>
        items.map((item) => ({
          id: item.id || item.file_id,
          title: type === "file" ? item.original_name : item.title,
          itemType: type,
          status: item.status,
          abstract: item.abstract,
          checked: selectedIds.has(item.id || item.file_id),
        }));
      setReferences([
        ...processItems(filesRes.data || [], "file"),
        ...processItems(candidatesRes.data || [], "paper"),
      ]);
    } catch (e) {
      console.error("Data fetch error:", e);
    }
  }, []);

  const loadFileData = useCallback(
    async (ref) => {
      if (!ref || !currentSessionId) return;
      setIsPdfLoading(true);
      try {
        const downloadUrl =
          ref.itemType === "file"
            ? `/sessions/${currentSessionId}/files/${ref.id}/download`
            : `/sessions/${currentSessionId}/papers/${ref.id}/download`;
        const res = await api.get(downloadUrl, { responseType: "blob" });
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        setPdfUrl(
          URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }))
        );
      } catch (e) {
        setPdfUrl(null);
      } finally {
        setIsPdfLoading(false);
      }

      setIsSummaryLoading(true);
      try {
        const summaryUrl =
          ref.itemType === "file"
            ? `/sessions/${currentSessionId}/files/${ref.id}/summary`
            : `/sessions/${currentSessionId}/papers/${ref.id}/summary`;
        const sRes = await api.get(summaryUrl);
        setSummaryContent(sRes.data.content || sRes.data.summary || "");
      } catch (e) {
        setSummaryContent("");
      } finally {
        setIsSummaryLoading(false);
      }
    },
    [currentSessionId, pdfUrl]
  );

  useEffect(() => {
    api.get("/sessions").then((res) => {
      setSessions(res.data || []);
      if (res.data?.length > 0 && !currentSessionId) {
        setCurrentSessionId(res.data[0].id);
        fetchSessionData(res.data[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (viewingRef) loadFileData(viewingRef);
  }, [viewingRef]);

  const handleCreateSession = async () => {
    if (!newSessionTitle.trim()) return;
    try {
      const res = await api.post("/sessions", { title: newSessionTitle });
      setSessions((prev) => [res.data, ...prev]);
      setCurrentSessionId(res.data.id);
      fetchSessionData(res.data.id);
      setShowSessionModal(false);
      setNewSessionTitle("");
    } catch (e) {
      console.error(e);
    }
  };

  const handleRemoveSession = async (sessionId) => {
    if (!window.confirm("세션을 삭제하시겠습니까?")) return;
    try {
      await api.delete(`/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
        setReferences([]);
        setViewingRef(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const processStreamResponse = useCallback(
    async (response) => {
      if (!response?.ok) return;
      const reader = response.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const raw of lines) {
            const line = raw.trim();
            if (!line) continue;
            try {
              const data = JSON.parse(line);
              if (data.type === "log") {
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last?.isLog)
                    return [
                      ...prev.slice(0, -1),
                      { role: "ai", content: data.content, isLog: true },
                    ];
                  return [
                    ...prev,
                    { role: "ai", content: data.content, isLog: true },
                  ];
                });
              } else if (data.type === "proposal") {
                setMessages((prev) => [
                  ...prev,
                  {
                    role: "ai",
                    content: data.content,
                    isProposal: true,
                    agentType: data.analysis?.agent_type || "retrieval",
                    analysisData: data.analysis,
                  },
                ]);
              } else if (data.type === "result" || data.type === "message") {
                const content =
                  data.content || (data.data ? data.data.content : "");
                if (content)
                  setMessages((prev) => [
                    ...prev,
                    { role: "ai", content: content },
                  ]);
                if (data.type === "result")
                  setTimeout(
                    () =>
                      currentSessionId && fetchSessionData(currentSessionId),
                    800
                  );
              }
            } catch (e) {}
          }
        }
      } catch (err) {}
    },
    [currentSessionId, fetchSessionData]
  );

  const handleRetrieval = useCallback(async () => {
    if (!currentSessionId || !retrievalQuery.trim()) return;
    setShowRetrievalModal(false);
    setLeftTab("library");
    setMessages((prev) => [...prev, { role: "user", content: retrievalQuery }]);
    setIsWaiting(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `${api.defaults.baseURL}/sessions/${currentSessionId}/research`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ query: retrievalQuery, is_confirmed: false }),
        }
      );
      await processStreamResponse(res);
      setRetrievalQuery("");
    } catch (e) {
    } finally {
      setIsWaiting(false);
    }
  }, [currentSessionId, retrievalQuery, processStreamResponse]);

  const handleGenerateReport = async () => {
    if (!currentSessionId || !reportInstruction.trim()) return;
    const selectedIds = references.filter((r) => r.checked).map((r) => r.id);
    setShowReportModal(false);
    setLeftTab("report");
    setIsWaiting(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `${api.defaults.baseURL}/sessions/${currentSessionId}/report`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            prompt: reportInstruction,
            is_confirmed: false,
            selected_ids: selectedIds,
          }),
        }
      );
      await processStreamResponse(res);
      setReportInstruction("");
    } catch (e) {
    } finally {
      setIsWaiting(false);
    }
  };

  const handleConfirmAction = useCallback(
    async (agentType, analysisData) => {
      if (!currentSessionId) return;
      setMessages((prev) => {
        const msgs = [...prev];
        if (msgs[msgs.length - 1]?.isProposal)
          msgs[msgs.length - 1].isProposal = false;
        return [...msgs, { role: "user", content: "진행해 주세요." }];
      });
      setIsWaiting(true);
      try {
        const token = localStorage.getItem("token");
        const endpoint = agentType === "synthesizer" ? "report" : "research";
        const body =
          agentType === "synthesizer"
            ? { is_confirmed: true }
            : {
                query: "confirmed",
                is_confirmed: true,
                confirmed_intent: analysisData,
              };
        const res = await fetch(
          `${api.defaults.baseURL}/sessions/${currentSessionId}/${endpoint}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(body),
          }
        );
        await processStreamResponse(res);
      } catch (e) {
      } finally {
        setIsWaiting(false);
      }
    },
    [currentSessionId, processStreamResponse]
  );

  const handleSendMessage = async (text) => {
    if (!text.trim() || isWaiting || !currentSessionId) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsWaiting(true);
    try {
      const res = await api.post(`/sessions/${currentSessionId}/chat`, {
        message: text,
        context_items: references
          .filter((r) => r.checked)
          .map((r) => ({
            id: r.id,
            type: r.itemType === "file" ? "uploaded_file" : "staged_paper",
            status: r.status,
            title: r.title,
          })),
      });
      setMessages((prev) => [...prev, { role: "ai", content: res.data.reply }]);
    } catch (e) {
    } finally {
      setIsWaiting(false);
      fetchSessionData(currentSessionId);
    }
  };

  const uploadFiles = useCallback(
    async (files) => {
      if (!currentSessionId || !files?.length) return;
      const fd = new FormData();
      Array.from(files).forEach((f) => fd.append("files", f));
      try {
        const res = await api.post(`/sessions/${currentSessionId}/files`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        await Promise.all(
          (res.data || []).map((item) =>
            api.post(`/sessions/${currentSessionId}/selections/toggle`, {
              item_type: "uploaded_file",
              item_id: item.file_id || item.id,
            })
          )
        );
        await fetchSessionData(currentSessionId);
      } catch (e) {}
    },
    [currentSessionId, fetchSessionData]
  );

  const toggleReference = useCallback(
    async (ref) => {
      if (!currentSessionId) return;
      setReferences((prev) =>
        prev.map((r) => (r.id === ref.id ? { ...r, checked: !r.checked } : r))
      );
      try {
        await api.post(`/sessions/${currentSessionId}/selections/toggle`, {
          item_type: ref.itemType === "file" ? "uploaded_file" : "staged_paper",
          item_id: ref.id,
        });
      } catch (e) {}
    },
    [currentSessionId]
  );

  const removeReference = useCallback(
    async (ref) => {
      if (!currentSessionId || !window.confirm("삭제하시겠습니까?")) return;
      try {
        if (ref.itemType === "file")
          await api.delete(`/sessions/${currentSessionId}/files/${ref.id}`);
        await fetchSessionData(currentSessionId);
      } catch (e) {}
    },
    [currentSessionId, fetchSessionData]
  );

  return (
    <div className="dashboard-layout">
      <LeftPanel
        sessions={sessions}
        currentSessionId={currentSessionId}
        leftTab={leftTab}
        setLeftTab={setLeftTab}
        references={references}
        reports={reports}
        viewingReport={viewingReport}
        onSelectSession={(id) => {
          setCurrentSessionId(id);
          fetchSessionData(id);
        }}
        onSelectRef={setViewingRef}
        onSelectReport={(rpt) => {
          setViewingReport(rpt);
          setCenterTab("report");
        }}
        onRetrievalTrigger={() => setShowRetrievalModal(true)}
        onUploadTrigger={uploadFiles}
        onLogout={onLogout}
        onToggleRef={toggleReference}
        onRemoveRef={removeReference}
        onRemoveSession={handleRemoveSession}
        onCreateSessionTrigger={() => setShowSessionModal(true)}
        onReportTrigger={() => setShowReportModal(true)}
      />
      <CenterPanel
        viewingRef={viewingRef}
        viewingReport={viewingReport}
        centerTab={centerTab}
        setCenterTab={setCenterTab}
        pdfUrl={pdfUrl}
        isPdfLoading={isPdfLoading}
        summaryContent={summaryContent}
        isSummaryLoading={isSummaryLoading}
        highlightText={highlightText}
      />
      <RightPanel
        messages={messages}
        isWaiting={isWaiting}
        onSendMessage={handleSendMessage}
        onConfirmAction={handleConfirmAction}
        onCancelAction={() => setIsWaiting(false)}
      />

      {/* --- Modals --- */}
      {showSessionModal && (
        <div
          className="modal-overlay"
          onMouseDown={(e) =>
            e.target === e.currentTarget && setShowSessionModal(false)
          }
        >
          <div className="modal-box">
            <div className="modal-header">
              <h3>New Session</h3>
              <button onClick={() => setShowSessionModal(false)}>
                <X size={16} />
              </button>
            </div>
            <input
              className="modal-input"
              value={newSessionTitle}
              onChange={(e) => setNewSessionTitle(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreateSession()}
              autoFocus
            />
            <div className="modal-actions">
              <button
                className="btn-secondary"
                onClick={() => setShowSessionModal(false)}
              >
                Cancel
              </button>
              <button className="btn-primary" onClick={handleCreateSession}>
                Create
              </button>
            </div>
          </div>
        </div>
      )}
      {showRetrievalModal && (
        <div
          className="modal-overlay"
          onMouseDown={(e) =>
            e.target === e.currentTarget && setShowRetrievalModal(false)
          }
        >
          <div className="modal-box">
            <div className="modal-header">
              <h3>Retrieval Agent</h3>
              <button onClick={() => setShowRetrievalModal(false)}>
                <X size={16} />
              </button>
            </div>
            <textarea
              className="modal-textarea"
              value={retrievalQuery}
              onChange={(e) => setRetrievalQuery(e.target.value)}
              rows={4}
            />
            <div className="modal-actions">
              <button
                className="btn-secondary"
                onClick={() => setShowRetrievalModal(false)}
              >
                Cancel
              </button>
              <button className="btn-primary" onClick={handleRetrieval}>
                Run
              </button>
            </div>
          </div>
        </div>
      )}
      {showReportModal && (
        <div
          className="modal-overlay"
          onMouseDown={(e) =>
            e.target === e.currentTarget && setShowReportModal(false)
          }
        >
          <div className="modal-box">
            <div className="modal-header">
              <h3>Synthesizer Agent</h3>
              <button onClick={() => setShowReportModal(false)}>
                <X size={16} />
              </button>
            </div>
            <textarea
              className="modal-textarea"
              value={reportInstruction}
              onChange={(e) => setReportInstruction(e.target.value)}
              rows={3}
            />
            <div style={{ padding: "0 24px 16px" }}>
              <p
                style={{
                  fontSize: "11px",
                  fontWeight: "700",
                  color: "#94a3b8",
                  marginBottom: "8px",
                }}
              >
                Selected Documents
              </p>
              <div
                style={{
                  maxHeight: "120px",
                  overflowY: "auto",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  background: "#f8fafc",
                  padding: "8px",
                }}
              >
                {references
                  .filter((r) => r.checked)
                  .map((ref) => (
                    <div
                      key={ref.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        fontSize: "12px",
                      }}
                    >
                      <FileText size={14} color="var(--primary)" />
                      <span>{ref.title}</span>
                    </div>
                  ))}
              </div>
            </div>
            <div className="modal-actions">
              <button
                className="btn-secondary"
                onClick={() => setShowReportModal(false)}
              >
                Cancel
              </button>
              <button className="btn-primary" onClick={handleGenerateReport}>
                Generate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
