import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from "react";
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
} from "lucide-react";
import api from "../../api";
import "./Dashboard.css";
import PdfAnalyzer from "./PdfAnalyzer";

// ==================================================================================
// [Component 1] LeftPanel: 세션 및 라이브러리 관리
// ==================================================================================
const LeftPanel = React.memo(
  ({
    sessions,
    currentSessionId,
    leftTab,
    setLeftTab,
    references,
    viewingRef,
    onSelectSession,
    onCreateSessionTrigger,
    onToggleRef,
    onRemoveRef,
    onSelectRef,
    onUploadTrigger,
    onRetrievalTrigger,
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
                {tab}
              </button>
            ))}
          </div>
        </div>
        <div className="list-area custom-scrollbar">
          {leftTab === "session" && (
            <>
              <button
                className="btn-secondary"
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
                title={!currentSessionId ? "세션을 먼저 선택하세요" : undefined}
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
                  title={
                    !currentSessionId ? "세션을 먼저 선택하세요" : undefined
                  }
                >
                  <FileUp size={14} /> Local File Upload
                </button>
                <input
                  type="file"
                  multiple
                  hidden
                  ref={fileInputRef}
                  onChange={(e) => {
                    const files = e.target.files;
                    if (files && files.length) onUploadTrigger(files);
                    // allow selecting same file again
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
            <div className="empty-state">
              <ClipboardCheck
                size={32}
                style={{ opacity: 0.3, marginBottom: "12px" }}
              />
              <p style={{ fontSize: "12px" }}>Reports will be archived here.</p>
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
// [Component 2] CenterPanel: PDF 뷰어 및 요약 표시 (핵심 수정)
// ==================================================================================
const CenterPanel = React.memo(
  ({
    viewingRef,
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
          {["original", "analysis", "summary"].map((tab) => (
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
          {!viewingRef ? (
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
                            "이 파일에 대해 생성된 요약 정보가 아직 없습니다. 분석이 완료될 때까지 기다려 주세요."}
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
// [Component 3] RightPanel: 채팅 에이전트
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
                  {m.evidence && (
                    <button
                      className="mini-btn"
                      style={{ marginTop: "8px" }}
                      onClick={() => onExecuteHighlight(m.evidence)}
                    >
                      <ExternalLink size={12} /> 본문 근거 확인
                    </button>
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
// [Main] Dashboard: 로직 통합
// ==================================================================================
const Dashboard = ({ onLogout }) => {
  const [highlightText, setHighlightText] = useState("");
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [references, setReferences] = useState([]);
  const [leftTab, setLeftTab] = useState("library");
  const [centerTab, setCenterTab] = useState("analysis");
  const [viewingRef, setViewingRef] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const [summaryContent, setSummaryContent] = useState("");
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);
  const [showRetrievalModal, setShowRetrievalModal] = useState(false);
  const [retrievalQuery, setRetrievalQuery] = useState("");

  // 세션 데이터 로드
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
      const selectedIds = new Set(
        (selectionsRes.data || []).map((s) => s.item_id)
      );
      const process = (items, type) =>
        items.map((item) => ({
          id: item.id || item.file_id,
          title: type === "file" ? item.original_name : item.title,
          itemType: type,
          status: item.status,
          abstract: item.abstract,
          checked: selectedIds.has(item.id || item.file_id),
        }));
      setReferences([
        ...process(filesRes.data || [], "file"),
        ...process(candidatesRes.data || [], "paper"),
      ]);
    } catch (e) {
      console.error("Data fetch error:", e);
    }
  }, []);

  // PDF 및 요약본 로드 (핵심: viewingRef가 바뀔 때마다 실행)
  // Dashboard.jsx 내부 loadFileData 함수 부분
  const loadFileData = useCallback(
    async (ref) => {
      if (!ref || !currentSessionId) return;

      // 1. PDF 로드 부분 (기존과 동일)
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
        console.error("PDF Load Error:", e);
        setPdfUrl(null);
      } finally {
        setIsPdfLoading(false);
      }

      // 2. Summary 로드 부분 (명세서 대응 수정)
      setIsSummaryLoading(true);
      try {
        const summaryUrl =
          ref.itemType === "file"
            ? `/sessions/${currentSessionId}/files/${ref.id}/summary`
            : `/sessions/${currentSessionId}/papers/${ref.id}/summary`;
        const sRes = await api.get(summaryUrl);

        // 백엔드 extract.py 로직 상 'content' 필드로 올 가능성이 높으므로 둘 다 체크
        const summaryText = sRes.data.content || sRes.data.summary || "";
        setSummaryContent(summaryText);
      } catch (e) {
        console.error("Summary Load Error:", e);
        setSummaryContent("");
      } finally {
        setIsSummaryLoading(false);
      }
    },
    [currentSessionId, pdfUrl]
  );
  // Ensure API Authorization header is set once on mount
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    else delete api.defaults.headers.common["Authorization"];
  }, []);

  useEffect(() => {
    api.get("/sessions").then((res) => setSessions(res.data || []));
  }, []);
  useEffect(() => {
    if (viewingRef) loadFileData(viewingRef);
  }, [viewingRef]);

  // ----------------------------------------------------------------------------------
  // Retrieval Agent (streaming): proposal -> confirm/cancel -> indexing
  // ----------------------------------------------------------------------------------
  const processStreamResponse = useCallback(
    async (response) => {
      if (!response?.ok) {
        const text = await response.text().catch(() => "");
        setMessages((prev) => [
          ...prev,
          {
            role: "ai",
            content: text || `요청 실패 (HTTP ${response?.status ?? "?"})`,
          },
        ]);
        return;
      }

      const reader = response.body?.getReader?.();
      if (!reader) {
        setMessages((prev) => [
          ...prev,
          { role: "ai", content: "스트리밍 응답을 읽을 수 없습니다." },
        ]);
        return;
      }

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
              const t = data.type;

              if (t === "log") {
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last && last.isLog) {
                    return [
                      ...prev.slice(0, -1),
                      { role: "ai", content: data.content, isLog: true },
                    ];
                  }
                  return [
                    ...prev,
                    { role: "ai", content: data.content, isLog: true },
                  ];
                });
              } else if (t === "proposal") {
                setMessages((prev) => [
                  ...prev,
                  {
                    role: "ai",
                    content: data.content,
                    isProposal: true,
                    agentType: "retrieval",
                    analysisData: data.analysis,
                  },
                ]);
              } else if (t === "result" || t === "message" || t === "error") {
                setMessages((prev) => [
                  ...prev,
                  { role: "ai", content: data.content },
                ]);
                if (t === "result") {
                  // 결과가 DB에 반영될 시간을 조금 준 뒤 목록 갱신
                  setTimeout(() => {
                    if (currentSessionId) fetchSessionData(currentSessionId);
                  }, 800);
                }
              } else {
                // unknown event
                if (data?.content) {
                  setMessages((prev) => [
                    ...prev,
                    { role: "ai", content: data.content },
                  ]);
                }
              }
            } catch (e) {
              console.error("Stream Parse Error", e);
            }
          }
        }
      } catch (err) {
        console.error("Stream Read Error", err);
        setMessages((prev) => [
          ...prev,
          { role: "ai", content: "스트리밍 중 오류가 발생했습니다." },
        ]);
      }
    },
    [currentSessionId, fetchSessionData]
  );

  const handleRetrieval = useCallback(async () => {
    if (!currentSessionId) return;
    const q = (retrievalQuery || "").trim();
    if (!q) return;

    setShowRetrievalModal(false);
    setRetrievalQuery("");
    setLeftTab("library");

    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setIsWaiting(true);

    try {
      const token = localStorage.getItem("token");
      const baseUrl = api.defaults?.baseURL || "";
      const res = await fetch(
        `${baseUrl}/sessions/${currentSessionId}/research`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ query: q, is_confirmed: false }),
        }
      );
      await processStreamResponse(res);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: `검색 요청 실패: ${e?.message || e}` },
      ]);
    } finally {
      setIsWaiting(false);
    }
  }, [currentSessionId, retrievalQuery, processStreamResponse]);

  const handleConfirmAction = useCallback(
    async (agentType, analysisData) => {
      if (agentType !== "retrieval" || !currentSessionId) return;

      // (UI) 마지막 proposal 메시지에서 버튼 제거
      setMessages((prev) => {
        const msgs = [...prev];
        const last = msgs[msgs.length - 1];
        if (last && last.isProposal)
          msgs[msgs.length - 1] = { ...last, isProposal: false };
        return [...msgs, { role: "user", content: "진행해 주세요." }];
      });

      setIsWaiting(true);
      try {
        const token = localStorage.getItem("token");
        const baseUrl = api.defaults?.baseURL || "";
        const res = await fetch(
          `${baseUrl}/sessions/${currentSessionId}/research`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
              query: "confirmed",
              is_confirmed: true,
              confirmed_intent: analysisData,
            }),
          }
        );
        await processStreamResponse(res);
      } catch (e) {
        setMessages((prev) => [
          ...prev,
          { role: "ai", content: `실행 오류: ${e?.message || e}` },
        ]);
      } finally {
        setIsWaiting(false);
      }
    },
    [currentSessionId, processStreamResponse]
  );

  const handleCancelAction = useCallback(() => {
    setMessages((prev) => {
      const msgs = [...prev];
      const last = msgs[msgs.length - 1];
      if (last && last.isProposal) {
        msgs[msgs.length - 1] = {
          ...last,
          isProposal: false,
          content: `${last.content}\n\n*(취소됨)*`,
        };
      }
      return msgs;
    });
    setIsWaiting(false);
  }, []);
  const handleSendMessage = async (text) => {
    if (!text.trim() || isWaiting || !currentSessionId) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsWaiting(true);
    try {
      const selectedRefs = references.filter((r) => r.checked);
      const contextItems = selectedRefs.map((r) => ({
        id: r.id,
        type: r.itemType === "file" ? "uploaded_file" : "staged_paper",
        status: r.status || "uploaded",
        title: r.title,
      }));

      const res = await api.post(`/sessions/${currentSessionId}/chat`, {
        message: text,
        context_items: contextItems,
      });
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: res.data.reply, evidence: res.data.evidence },
      ]);
    } catch (e) {
      console.log("[CHAT] failed:", e);
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "채팅 요청 실패. 콘솔 로그를 확인해 주세요." },
      ]);
    } finally {
      setIsWaiting(false);
      fetchSessionData(currentSessionId);
    }
  };
  const uploadFiles = useCallback(
    async (files) => {
      if (!currentSessionId) {
        alert("세션을 먼저 선택하세요.");
        return;
      }
      if (!files || files.length === 0) return;

      // optimistic UI
      const tempRefs = Array.from(files).map((file, i) => ({
        id: `temp-${Date.now()}-${i}`,
        title: file.name,
        type: "FILE",
        status: "uploading",
        checked: true,
        isLocal: true,
        itemType: "file",
      }));
      setReferences((prev) => [...tempRefs, ...prev]);

      const fd = new FormData();
      Array.from(files).forEach((f) => fd.append("files", f));

      try {
        const res = await api.post(`/sessions/${currentSessionId}/files`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        // 서버가 업로드 즉시 선택/분석을 트리거하지 않는 경우를 대비해 자동 선택
        const uploaded = Array.isArray(res.data) ? res.data : [];
        for (const item of uploaded) {
          const fileId = item.file_id ?? item.id ?? item.uploaded_file_id;
          if (!fileId) continue;
          await api.post(`/sessions/${currentSessionId}/selections/toggle`, {
            item_type: "uploaded_file",
            item_id: fileId,
          });
        }

        await fetchSessionData(currentSessionId);
      } catch (e) {
        console.log("[UPLOAD] failed:", e);
        alert("업로드 실패. 콘솔 로그를 확인해 주세요.");
        setReferences((prev) =>
          prev.filter((r) => !String(r.id).startsWith("temp-"))
        );
      }
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
      } catch (e) {
        console.log("[TOGGLE] failed:", e);
        // revert
        setReferences((prev) =>
          prev.map((r) => (r.id === ref.id ? { ...r, checked: !r.checked } : r))
        );
      }
    },
    [currentSessionId]
  );

  const removeReference = useCallback(
    async (ref) => {
      if (!currentSessionId) return;
      if (!window.confirm("파일을 삭제하시겠습니까?")) return;
      try {
        if (ref.itemType === "file") {
          await api.delete(`/sessions/${currentSessionId}/files/${ref.id}`);
        }
        await fetchSessionData(currentSessionId);
      } catch (e) {
        console.log("[DELETE] failed:", e);
        alert("삭제 실패.");
      }
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
        viewingRef={viewingRef}
        onSelectSession={(id) => {
          setCurrentSessionId(id);
          fetchSessionData(id);
        }}
        onSelectRef={setViewingRef}
        onRetrievalTrigger={() => setShowRetrievalModal(true)}
        onUploadTrigger={uploadFiles}
        onLogout={onLogout}
        onToggleRef={toggleReference}
        onRemoveRef={removeReference}
        onCreateSessionTrigger={async () => {
          const title = prompt("New Session Name:");
          if (title) {
            const res = await api.post("/sessions", { title });
            setSessions((prev) => [res.data, ...prev]);
            setCurrentSessionId(res.data.id);
          }
        }}
      />
      <CenterPanel
        viewingRef={viewingRef}
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
        onExecuteHighlight={(txt) => {
          setCenterTab("analysis");
          setHighlightText(txt);
        }}
        onConfirmAction={handleConfirmAction}
        onCancelAction={handleCancelAction}
      />

      {showRetrievalModal && (
        <div
          className="modal-overlay"
          onMouseDown={(e) => {
            // overlay 클릭 시 닫기 (box 클릭은 무시)
            if (e.target === e.currentTarget) setShowRetrievalModal(false);
          }}
        >
          <div className="modal-box" role="dialog" aria-modal="true">
            <div className="modal-header">
              <h3>Retrieval Agent</h3>
              <button
                className="icon-btn"
                onClick={() => setShowRetrievalModal(false)}
                aria-label="close"
              >
                <X size={16} />
              </button>
            </div>
            <p className="modal-desc">
              찾고 싶은 연구 주제/질문을 입력하면, 후보 논문을 검색해
              라이브러리에 추가합니다.
            </p>
            <textarea
              className="modal-textarea"
              placeholder="예: 운동이 알츠하이머 진행에 미치는 영향 (2020~)"
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
              <button
                className="btn-primary"
                onClick={handleRetrieval}
                disabled={
                  !retrievalQuery.trim() || !currentSessionId || isWaiting
                }
              >
                <Play size={14} /> Run
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
