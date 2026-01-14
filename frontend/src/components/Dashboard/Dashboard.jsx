import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Microscope,
  MessageSquare,
  Plus,
  Send,
  LogOut,
  X,
  Loader2,
  Trash2,
  UploadCloud,
  Menu,
  ChevronLeft,
  Database,
  Search,
  PenTool,
  BookOpen,
  CheckSquare,
  Layers,
  FileUp,
  CheckCircle2,
  Download,
  ExternalLink,
  Play, // ✅ 실행 아이콘 추가
} from "lucide-react";
import api from "../../api";
import "./Dashboard.css";

const AGENTS = [
  { id: "general", name: "General Chat", icon: Layers, color: "#64748b" },
  { id: "retrieval", name: "Paper Search", icon: Search, color: "#0ea5e9" },
  { id: "extractor", name: "Extractor", icon: Database, color: "#a855f7" },
  { id: "synthesizer", name: "Report Writer", icon: PenTool, color: "#f59e0b" },
];

const Dashboard = ({ onLogout }) => {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isWaiting, setIsWaiting] = useState(false);
  const [references, setReferences] = useState([]);
  const [activeAgent, setActiveAgent] = useState("general");
  const [isRefPanelOpen, setIsRefPanelOpen] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth > 1024);
  const [dragActive, setDragActive] = useState(false);

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const isInitializing = useRef(false);

  useEffect(() => {
    const init = async () => {
      if (isInitializing.current) return;
      isInitializing.current = true;
      try {
        const res = await api.get("/sessions");
        setSessions(res.data);
      } catch (err) {
        console.error("세션 로드 실패", err);
      }
    };
    init();

    const handleResize = () => {
      if (window.innerWidth <= 1024) {
        setIsSidebarOpen(false);
        setIsRefPanelOpen(false);
      } else {
        setIsSidebarOpen(true);
        setIsRefPanelOpen(true);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isWaiting, input]);

  // --- 헬퍼 함수 ---
  const fetchAndMergeReferences = async (sessionId) => {
    try {
      const [filesRes, candidatesRes, selectionsRes] = await Promise.all([
        api.get(`/sessions/${sessionId}/files`),
        api.get(`/sessions/${sessionId}/research/candidates`),
        api.get(`/sessions/${sessionId}/selections`),
      ]);

      const uploadedFiles = filesRes.data || [];
      const stagedPapers = candidatesRes.data || [];
      const selections = selectionsRes.data || [];
      const selectedIds = new Set(selections.map((s) => s.item_id));

      const mappedFiles = uploadedFiles.map((f) => {
        const ext = (
          f.original_name.split(".").pop() ||
          f.mime_type ||
          "FILE"
        ).toUpperCase();
        return {
          id: f.id,
          title: f.original_name,
          type: ext,
          status: f.status,
          checked: selectedIds.has(f.id),
          isLocal: false,
          isLoading: false,
          itemType: "file",
        };
      });

      const mappedPapers = stagedPapers.map((p) => {
        return {
          id: p.id,
          title: p.title,
          type: "PDF",
          status: "staged",
          checked: selectedIds.has(p.id),
          isLocal: false,
          isLoading: false,
          source: p.source,
          itemType: "paper",
          url: p.url,
        };
      });

      setReferences([...mappedFiles, ...mappedPapers]);
    } catch (err) {
      console.error("References 로드 실패", err);
    }
  };

  // --- 파일 즉시 업로드 ---
  const uploadFilesToSession = async (sessionId, files) => {
    if (!files || files.length === 0) return;

    const newRefs = Array.from(files).map((file, index) => ({
      id: `temp-${Date.now()}-${index}`,
      title: file.name,
      type: (file.name.split(".").pop() || "FILE").toUpperCase(),
      status: "uploading",
      checked: true,
      isLocal: true,
      isLoading: true,
      file: file,
      itemType: "file",
    }));
    setReferences((prev) => [...prev, ...newRefs]);
    if (!isRefPanelOpen) setIsRefPanelOpen(true);

    try {
      const fd = new FormData();
      Array.from(files).forEach((f) => fd.append("files", f));
      const res = await api.post(`/sessions/${sessionId}/files`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const uploadedItems = res.data || [];

      for (const item of uploadedItems) {
        await api.post(`/sessions/${sessionId}/selections/toggle`, {
          item_type: "uploaded_file",
          item_id: item.file_id,
        });
      }
      await fetchAndMergeReferences(sessionId);
    } catch (err) {
      console.error("Upload failed", err);
      alert("파일 업로드 실패");
      setReferences((prev) =>
        prev.filter((r) => !r.id.toString().startsWith("temp-"))
      );
    }
  };

  const handleFileSelection = async (files) => {
    if (!files || files.length === 0) return;
    let targetId = currentSessionId;
    if (!targetId) {
      try {
        const createRes = await api.post("/sessions", { title: "New Session" });
        targetId = createRes.data.id;
        setSessions((prev) => [createRes.data, ...prev]);
        setCurrentSessionId(targetId);
      } catch (err) {
        alert("세션 생성 실패");
        return;
      }
    }
    await uploadFilesToSession(targetId, files);
  };

  // --- 검색 확정 (Human-in-the-loop) ---
  const handleConfirmResearch = async (analysisData) => {
    setMessages((prev) => [
      ...prev,
      { role: "user", content: "네, 검색해 주세요." },
    ]);
    setIsWaiting(true);
    const token = localStorage.getItem("token");
    let targetId = currentSessionId;

    try {
      const response = await fetch(
        `${api.defaults.baseURL}/sessions/${targetId}/research`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            query: "Confirmed Search",
            top_k: 5,
            is_confirmed: true, // ✅ 확정 플래그
            confirmed_intent: analysisData,
          }),
        }
      );

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const step = JSON.parse(line);
            if (step.type === "log") {
              setMessages((prev) => {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg && lastMsg.role === "ai" && lastMsg.isLog) {
                  return [
                    ...prev.slice(0, -1),
                    { ...lastMsg, content: step.content },
                  ];
                } else {
                  return [
                    ...prev,
                    { role: "ai", content: step.content, isLog: true },
                  ];
                }
              });
            } else if (step.type === "result") {
              fetchAndMergeReferences(targetId);
              const msgRes = await api.get(`/sessions/${targetId}/messages`);
              setMessages(msgRes.data);
            } else if (step.type === "error") {
              setMessages((prev) => [
                ...prev,
                { role: "ai", content: `오류: ${step.content}` },
              ]);
            }
          } catch (e) {
            console.error(e);
          }
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsWaiting(false);
    }
  };

  // --- 기타 핸들러 (세션, 드래그, 다운로드 등) ---
  const handleSelectSession = async (id) => {
    setCurrentSessionId(id);
    setReferences([]);
    try {
      const msgRes = await api.get(`/sessions/${id}/messages`);
      setMessages(msgRes.data);
      await fetchAndMergeReferences(id);
      if (window.innerWidth <= 768) setIsSidebarOpen(false);
    } catch (err) {
      console.error(err);
    }
  };
  const handleResetChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setReferences([]);
    setInput("");
    setActiveAgent("general");
    if (textareaRef.current) textareaRef.current.focus();
  };
  const handleDeleteSession = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("삭제하시겠습니까?")) return;
    try {
      await api.delete(`/sessions/${id}`);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (currentSessionId === id) handleResetChat();
    } catch (err) {
      alert("삭제 실패");
    }
  };
  const handleDownloadFile = async (e, ref) => {
    e.stopPropagation();
    if (!currentSessionId) return;
    if (ref.isLocal) {
      alert("업로드 중입니다.");
      return;
    }
    if (ref.itemType === "paper") {
      ref.url ? window.open(ref.url, "_blank") : alert("링크 없음");
    } else {
      try {
        const res = await api.get(
          `/sessions/${currentSessionId}/files/${ref.id}/download`,
          { responseType: "blob" }
        );
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", ref.title);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        alert("다운로드 실패");
      }
    }
  };
  const removeReference = async (id, isLocal) => {
    if (isLocal) setReferences((prev) => prev.filter((r) => r.id !== id));
    else {
      if (!currentSessionId || !window.confirm("삭제하시겠습니까?")) return;
      try {
        const target = references.find((r) => r.id === id);
        if (target?.itemType === "file")
          await api.delete(`/sessions/${currentSessionId}/files/${id}`);
        setReferences((prev) => prev.filter((r) => r.id !== id));
      } catch (err) {
        alert("삭제 오류");
      }
    }
  };
  const toggleReference = async (id) => {
    const target = references.find((r) => r.id === id);
    if (!target) return;
    setReferences((prev) =>
      prev.map((r) => (r.id === id ? { ...r, checked: !r.checked } : r))
    );
    if (target.isLocal) return;
    try {
      await api.post(`/sessions/${currentSessionId}/selections/toggle`, {
        item_type:
          target.itemType === "file" ? "uploaded_file" : "staged_paper",
        item_id: id,
      });
    } catch (err) {
      setReferences((prev) =>
        prev.map((r) => (r.id === id ? { ...r, checked: !r.checked } : r))
      );
    }
  };
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave" || e.type === "drop") setDragActive(false);
  };
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files[0]) handleFileSelection(e.dataTransfer.files);
  };
  const handleInputResize = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  // --- 메시지 전송 (메인) ---
  const handleSendMessage = async () => {
    if (!input.trim() || isWaiting) return;
    const userContent = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: userContent }]);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setIsWaiting(true);

    try {
      let targetId = currentSessionId;
      if (!targetId) {
        const res = await api.post("/sessions", {
          title: userContent.substring(0, 15) || "New Session",
        });
        targetId = res.data.id;
        setSessions((prev) => [res.data, ...prev]);
        setCurrentSessionId(targetId);
      }

      const serverRefIds = references
        .filter((r) => !r.isLocal && r.checked)
        .map((r) => r.id);

      if (activeAgent === "general") {
        const res = await api.post(`/sessions/${targetId}/chat`, {
          message: userContent,
          context_ids: serverRefIds,
        });
        setMessages((prev) => [
          ...prev,
          { role: "ai", content: res.data.reply },
        ]);
      } else if (activeAgent === "retrieval") {
        const token = localStorage.getItem("token");
        try {
          const response = await fetch(
            `${api.defaults.baseURL}/sessions/${targetId}/research`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({ query: userContent, top_k: 5 }),
            }
          );
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();
            for (const line of lines) {
              if (!line.trim()) continue;
              try {
                const step = JSON.parse(line);
                if (step.type === "log") {
                  setMessages((prev) => {
                    const lastMsg = prev[prev.length - 1];
                    if (lastMsg && lastMsg.role === "ai" && lastMsg.isLog)
                      return [
                        ...prev.slice(0, -1),
                        { ...lastMsg, content: step.content },
                      ];
                    else
                      return [
                        ...prev,
                        { role: "ai", content: step.content, isLog: true },
                      ];
                  });
                } else if (step.type === "proposal") {
                  // ✅ 제안 메시지 처리
                  setMessages((prev) => [
                    ...prev,
                    {
                      role: "ai",
                      content: step.content,
                      isProposal: true,
                      analysisData: step.analysis,
                    },
                  ]);
                } else if (step.type === "result") {
                  fetchAndMergeReferences(targetId);
                  const msgRes = await api.get(
                    `/sessions/${targetId}/messages`
                  );
                  setMessages(msgRes.data);
                } else if (step.type === "error") {
                  setMessages((prev) => [
                    ...prev,
                    { role: "ai", content: `오류: ${step.content}` },
                  ]);
                }
              } catch (e) {
                console.error(e);
              }
            }
          }
        } catch (e) {
          console.error(e);
          setMessages((prev) => [
            ...prev,
            { role: "ai", content: "네트워크 오류" },
          ]);
        }
      } else if (activeAgent === "extractor") {
        await api.post(`/sessions/${targetId}/extract?force=false`, {});
        const msgRes = await api.get(`/sessions/${targetId}/messages`);
        setMessages(msgRes.data);
        fetchAndMergeReferences(targetId);
      } else if (activeAgent === "synthesizer") {
        const res = await api.post(`/sessions/${targetId}/report`, {
          prompt: userContent,
        });
        setMessages((prev) => [
          ...prev,
          { role: "ai", content: res.data.content },
        ]);
      }

      if (activeAgent !== "retrieval") {
        const msgRes = await api.get(`/sessions/${targetId}/messages`);
        setMessages(msgRes.data);
        fetchAndMergeReferences(targetId);
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "오류가 발생했습니다." },
      ]);
    } finally {
      setIsWaiting(false);
    }
  };

  const activeAgentColor =
    AGENTS.find((a) => a.id === activeAgent)?.color || "#64748b";

  return (
    <div className="dashboard-container">
      {isSidebarOpen && window.innerWidth <= 768 && (
        <div
          className="mobile-overlay"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
      <aside className={`sidebar ${!isSidebarOpen ? "closed" : ""}`}>
        <div className="sidebar-header">
          <div className="sidebar-title">
            <Microscope size={26} /> <span>TV-A</span>
          </div>
          <button
            className="toggle-btn"
            onClick={() => setIsSidebarOpen(false)}
          >
            <ChevronLeft size={24} />
          </button>
        </div>
        <button className="new-chat-btn" onClick={handleResetChat}>
          <Plus size={20} /> New Chatting
        </button>
        <div className="chat-list">
          <p className="chat-list-header">RESEARCH HISTORY</p>
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`chat-item ${
                currentSessionId === s.id ? "active" : ""
              }`}
              onClick={() => handleSelectSession(s.id)}
            >
              <div className="chat-item-info">
                <MessageSquare size={18} />
                <span className="session-title">{s.title}</span>
              </div>
              <Trash2
                size={14}
                className="delete-session-icon"
                onClick={(e) => handleDeleteSession(e, s.id)}
              />
            </div>
          ))}
        </div>
        <button onClick={onLogout} className="logout-btn">
          <LogOut size={18} /> Logout
        </button>
      </aside>
      <main className="chat-main">
        {!isSidebarOpen && (
          <button
            className="sidebar-closed-toggle left"
            onClick={() => setIsSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>
        )}
        {!isRefPanelOpen && (
          <button
            className="sidebar-closed-toggle right"
            onClick={() => setIsRefPanelOpen(true)}
          >
            <BookOpen size={20} />
          </button>
        )}
        <div className="message-container" ref={scrollRef}>
          {messages.length === 0 && !currentSessionId && (
            <div className="empty-state">
              <Microscope
                size={56}
                style={{ marginBottom: 20, opacity: 0.2 }}
              />
              <h3>Target Validation Assistant</h3>
              <p>원하는 에이전트를 선택하고 연구를 시작하세요.</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`msg-bubble ${m.role} ${m.isLog ? "log-msg" : ""}`}
            >
              {m.role === "ai" && !m.isLog ? (
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content}
                  </ReactMarkdown>
                  {/* ✅ 제안 버튼 표시 */}
                  {m.isProposal && (
                    <div style={{ marginTop: "10px" }}>
                      <button
                        className="proposal-btn confirm"
                        onClick={() => handleConfirmResearch(m.analysisData)}
                        disabled={isWaiting}
                      >
                        <Play size={14} /> 검색 시작
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                m.content
              )}
            </div>
          ))}
          {isWaiting && (
            <div className="msg-bubble ai loading-msg">
              <Loader2 className="animate-spin" size={16} /> 분석 중...
            </div>
          )}
        </div>
        <div className="floating-input-wrapper">
          <div className="agent-selector-floating">
            {AGENTS.map((agent) => (
              <button
                key={agent.id}
                className={`agent-tab ${
                  activeAgent === agent.id ? "active" : ""
                }`}
                onClick={() => setActiveAgent(agent.id)}
                style={{
                  "--agent-color": agent.color,
                  color: activeAgent === agent.id ? agent.color : "#64748b",
                  borderColor:
                    activeAgent === agent.id ? agent.color : "transparent",
                }}
              >
                <agent.icon size={14} /> <span>{agent.name}</span>
              </button>
            ))}
          </div>
          <div
            className="input-box-container"
            style={{ boxShadow: `0 4px 20px ${activeAgentColor}15` }}
          >
            <textarea
              ref={textareaRef}
              className="main-text-input"
              value={input}
              onChange={handleInputResize}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder={`${
                AGENTS.find((a) => a.id === activeAgent).name
              }에게 질문하기...`}
              disabled={isWaiting}
              rows={1}
            />
            <button
              className="icon-send-btn"
              onClick={handleSendMessage}
              disabled={isWaiting}
            >
              {isWaiting ? (
                <Loader2 className="animate-spin" size={20} />
              ) : (
                <Send size={20} style={{ color: activeAgentColor }} />
              )}
            </button>
          </div>
        </div>
      </main>
      <aside
        className={`right-sidebar ${!isRefPanelOpen ? "closed" : ""} ${
          dragActive ? "drag-active" : ""
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div className="right-sidebar-header">
          <div className="header-left">
            <BookOpen size={18} />
            <h3>References</h3>
          </div>
          <div className="header-actions">
            <button
              className="icon-btn"
              onClick={() => fileInputRef.current?.click()}
            >
              <FileUp size={18} />
            </button>
            <input
              type="file"
              multiple
              hidden
              ref={fileInputRef}
              onChange={(e) => handleFileSelection(e.target.files)}
            />
            <button
              className="icon-btn"
              onClick={() => setIsRefPanelOpen(false)}
            >
              <X size={18} />
            </button>
          </div>
        </div>
        {dragActive && (
          <div className="sidebar-drag-overlay">
            <UploadCloud size={40} />
            <p>Drop files here</p>
          </div>
        )}
        <div className="reference-list">
          {references.length === 0 ? (
            <div className="empty-ref">
              <Search size={32} />
              <p>
                파일을 드래그하거나
                <br />
                업로드 버튼을 누르세요.
              </p>
            </div>
          ) : (
            references.map((ref) => {
              const isIndexed = ref.status === "indexed";
              const isPaper = ref.itemType === "paper";
              return (
                <div
                  key={ref.id}
                  className={`ref-item ${ref.checked ? "selected" : ""} ${
                    isIndexed ? "indexed" : ""
                  }`}
                  onClick={() => !ref.isLoading && toggleReference(ref.id)}
                >
                  <div className="ref-checkbox-area">
                    {ref.isLoading ? (
                      <Loader2
                        className="animate-spin"
                        size={14}
                        color="#94a3b8"
                      />
                    ) : (
                      <input
                        type="checkbox"
                        className="custom-checkbox"
                        checked={ref.checked}
                        readOnly
                      />
                    )}
                  </div>
                  <div className="ref-info">
                    <div className="ref-meta">
                      <span
                        className={`ref-ext-badge ${
                          isIndexed ? "indexed-badge" : ""
                        }`}
                      >
                        {ref.type}
                      </span>
                      {isIndexed && (
                        <span className="status-indexed">
                          <CheckCircle2 size={10} /> Analyzed
                        </span>
                      )}
                    </div>
                    <p className="ref-title" title={ref.title}>
                      {ref.title}
                    </p>
                  </div>
                  <div className="ref-actions">
                    <button
                      className="ref-action-btn download"
                      onClick={(e) => handleDownloadFile(e, ref)}
                      title={isPaper ? "Open Link" : "Download"}
                    >
                      {isPaper ? (
                        <ExternalLink size={14} />
                      ) : (
                        <Download size={14} />
                      )}
                    </button>
                    <button
                      className="ref-action-btn delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeReference(ref.id, ref.isLocal);
                      }}
                      title="Remove"
                    >
                      <X size={14} />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
        <div className="right-sidebar-footer">
          <div className="footer-info">
            <CheckSquare size={14} />
            <span>Selected: {references.filter((r) => r.checked).length}</span>
          </div>
        </div>
      </aside>
    </div>
  );
};

export default Dashboard;
