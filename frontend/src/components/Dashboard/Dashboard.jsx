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
  // --- 상태 관리 ---
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isWaiting, setIsWaiting] = useState(false);

  // References: { id, title, type(ext), checked, isLocal, isLoading, file }
  const [references, setReferences] = useState([]);

  const [activeAgent, setActiveAgent] = useState("general");
  const [isRefPanelOpen, setIsRefPanelOpen] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth > 1024);
  const [dragActive, setDragActive] = useState(false);

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const isInitializing = useRef(false);

  // --- 초기화 로직 ---
  useEffect(() => {
    const init = async () => {
      if (isInitializing.current) return;
      isInitializing.current = true;
      try {
        const res = await api.get("/chat/sessions");
        setSessions(res.data);
      } catch (err) {
        console.error("세션 목록 로드 실패", err);
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

  // 스크롤 자동 조정
  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isWaiting, input]);

  // --- 핸들러 ---

  const handleSelectSession = async (id) => {
    setCurrentSessionId(id);
    try {
      const msgRes = await api.get(`/chat/sessions/${id}/messages`);
      setMessages(msgRes.data);
      // TODO: 서버에서 저장된 Reference 불러오는 API 연동 필요
      setReferences([]);
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
    if (window.innerWidth <= 768) setIsSidebarOpen(false);
    if (textareaRef.current) textareaRef.current.focus();
  };

  const handleDeleteSession = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("이 대화를 삭제하시겠습니까?")) return;
    try {
      await api.delete(`/chat/sessions/${id}`);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (currentSessionId === id) handleResetChat();
    } catch (err) {
      alert("삭제 실패");
    }
  };

  // [수정됨] 파일 선택 핸들러 (확장자 추출 + 로딩 시뮬레이션)
  const handleFileSelection = (files) => {
    const newFiles = Array.from(files);

    // 중복 체크
    const uniqueFiles = newFiles.filter((file) => {
      return !references.some((ref) => ref.title === file.name);
    });

    if (uniqueFiles.length === 0 && newFiles.length > 0) {
      alert("이미 추가된 파일입니다.");
      return;
    }

    // 1. 초기 상태: 로딩 중 (isLoading: true)
    const newRefs = uniqueFiles.map((file, index) => {
      const ext = file.name.split(".").pop().toUpperCase() || "FILE";
      return {
        id: `local-${Date.now()}-${index}`,
        title: file.name,
        type: ext, // 확장자
        checked: true,
        isLocal: true,
        isLoading: true, // 로딩 상태 시작
        file: file,
      };
    });

    setReferences((prev) => [...prev, ...newRefs]);
    if (!isRefPanelOpen) setIsRefPanelOpen(true);

    // 2. 로딩 완료 시뮬레이션 (0.8초 후 스피너 -> 체크박스)
    setTimeout(() => {
      setReferences((prev) =>
        prev.map((ref) => (ref.isLoading ? { ...ref, isLoading: false } : ref))
      );
    }, 800);
  };

  const removeReference = (id) => {
    setReferences((prev) => prev.filter((ref) => ref.id !== id));
  };

  const toggleReference = (id) => {
    setReferences((prev) =>
      prev.map((ref) =>
        ref.id === id ? { ...ref, checked: !ref.checked } : ref
      )
    );
  };

  // 드래그 앤 드롭
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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files);
    }
  };

  const handleInputResize = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  // 메시지 전송
  const handleSendMessage = async () => {
    const localFilesToSend = references.filter((r) => r.isLocal && r.checked);

    if ((!input.trim() && localFilesToSend.length === 0) || isWaiting) return;

    const userContent = input.trim();
    setMessages((prev) => [
      ...prev,
      { role: "user", content: userContent || "파일 분석 요청" },
    ]);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setIsWaiting(true);

    try {
      let targetId = currentSessionId;

      if (!targetId) {
        const createRes = await api.post("/chat/sessions");
        targetId = createRes.data.id;
        const newTitle = userContent
          ? userContent.substring(0, 15) +
            (userContent.length > 15 ? "..." : "")
          : "새로운 대화";
        await api.patch(`/chat/sessions/${targetId}`, { title: newTitle });
        setSessions((prev) => [
          { ...createRes.data, title: newTitle },
          ...prev,
        ]);
        setCurrentSessionId(targetId);
      }

      const formData = new FormData();
      formData.append("message", userContent || "파일을 분석해줘.");
      formData.append("agent_mode", activeAgent);

      // 이미 서버에 있는 파일 ID
      const serverRefIds = references
        .filter((r) => !r.isLocal && r.checked)
        .map((r) => r.id);
      formData.append("context_ids", JSON.stringify(serverRefIds));

      // 새로 업로드할 파일
      localFilesToSend.forEach((ref) => {
        formData.append("files", ref.file);
      });

      const res = await api.post(`/chat/sessions/${targetId}/chat`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setMessages((prev) => [...prev, { role: "ai", content: res.data.reply }]);

      // 업로드 성공 처리 (로컬 -> 서버 파일로 전환 가정)
      if (res.data.uploaded_files) {
        setReferences((prev) => {
          const existingServerFiles = prev.filter((r) => !r.isLocal);
          // 편의상 로컬 파일을 서버 파일로 간주하여 플래그 변경
          const newlyUploaded = localFilesToSend.map((localFile) => ({
            ...localFile,
            isLocal: false,
          }));
          const remainingLocal = prev.filter((r) => r.isLocal && !r.checked);
          return [...existingServerFiles, ...newlyUploaded, ...remainingLocal];
        });
      }

      // 검색 결과 추가
      if (res.data.found_documents) {
        const newDocs = res.data.found_documents.map((doc) => ({
          ...doc,
          checked: false,
          isLocal: false,
        }));
        setReferences((prev) => [...prev, ...newDocs]);
        if (!isRefPanelOpen) setIsRefPanelOpen(true);
      }
    } catch (err) {
      console.error(err);
      alert("전송 중 오류가 발생했습니다.");
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

      {/* 1. Left Sidebar (History) */}
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

      {/* 2. Main Chat Area */}
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
            <div key={i} className={`msg-bubble ${m.role}`}>
              {m.role === "ai" ? (
                <ReactMarkdown
                  className="markdown-body"
                  remarkPlugins={[remarkGfm]}
                >
                  {m.content}
                </ReactMarkdown>
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

        {/* Floating Input Area */}
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

      {/* 3. Right Sidebar (Reference & Upload) */}
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
              title="Upload Files"
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
            references.map((ref) => (
              <div
                key={ref.id}
                className={`ref-item ${ref.checked ? "selected" : ""}`}
              >
                {/* 로딩 중이면 스피너, 아니면 체크박스 */}
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
                      onChange={() => toggleReference(ref.id)}
                    />
                  )}
                </div>

                <div className="ref-info">
                  <div className="ref-meta">
                    {/* 확장자 배지 */}
                    <span className="ref-ext-badge">{ref.type}</span>
                  </div>
                  <p className="ref-title" title={ref.title}>
                    {ref.title}
                  </p>
                </div>

                <button
                  className="ref-delete-btn"
                  onClick={() => removeReference(ref.id)}
                >
                  <X size={12} />
                </button>
              </div>
            ))
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
