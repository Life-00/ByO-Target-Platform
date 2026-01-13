import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Microscope,
  MessageSquare,
  Plus,
  Paperclip,
  Send,
  LogOut,
  X,
  FileText,
  Loader2,
  Trash2,
  UploadCloud,
  Menu,
  ChevronLeft,
  // [NEW] 추가된 아이콘
  Database, // Extractor
  Search, // Retrieval
  PenTool, // Synthesizer
  BookOpen, // Right Panel Toggle
  CheckSquare, // Checkbox Icon
  Layers, // General Chat
} from "lucide-react";
import api from "../../api";
import "./Dashboard.css";

// [NEW] 에이전트 설정 상수
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
  const [pendingFiles, setPendingFiles] = useState([]);
  const [isWaiting, setIsWaiting] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  // [NEW] 에이전트 및 참조 자료 상태
  const [activeAgent, setActiveAgent] = useState("general");
  const [references, setReferences] = useState([]); // { id, title, type: 'file'|'paper', checked: boolean }
  const [isRefPanelOpen, setIsRefPanelOpen] = useState(true); // 우측 패널 열림 상태

  // 반응형 사이드바 상태
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth > 1024);

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
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
        setIsRefPanelOpen(false); // 작은 화면에서는 우측 패널도 닫음
      } else {
        setIsSidebarOpen(true);
        setIsRefPanelOpen(true);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // 스크롤 조정
  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isWaiting, input]);

  // --- 기능 핸들러 ---

  // 세션 클릭
  const handleSelectSession = async (id) => {
    setCurrentSessionId(id);
    try {
      // 1. 메시지 로드
      const msgRes = await api.get(`/chat/sessions/${id}/messages`);
      setMessages(msgRes.data);

      // 2. [NEW] 해당 세션의 참조 자료(검색된 논문 등) 로드 (Backend API 구현 필요)
      // const docRes = await api.get(`/chat/sessions/${id}/documents`);
      // setReferences(docRes.data);

      // 임시: 세션을 바꾸면 참조 자료는 비운다고 가정 (혹은 서버에서 받아옴)
      setReferences([]);

      if (window.innerWidth <= 768) setIsSidebarOpen(false);
    } catch (err) {
      console.error(err);
    }
  };

  // New Chatting 클릭 -> [NEW] 모든 상태 초기화
  const handleResetChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setPendingFiles([]);
    setInput("");

    // [NEW] 에이전트 및 참조 자료 초기화
    setActiveAgent("general");
    setReferences([]);

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

  // [NEW] 참조 자료 체크박스 토글
  const toggleReference = (id) => {
    setReferences((prev) =>
      prev.map((ref) =>
        ref.id === id ? { ...ref, checked: !ref.checked } : ref
      )
    );
  };

  // 파일 핸들링
  const handleFileSelection = (files) => {
    setPendingFiles((prev) => [...prev, ...Array.from(files)]);
  };

  const removePendingFile = (index) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
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
    if ((!input.trim() && pendingFiles.length === 0) || isWaiting) return;

    const userContent = input.trim();

    // 1. 화면 업데이트
    setMessages((prev) => [
      ...prev,
      { role: "user", content: userContent || "파일 분석 요청" },
    ]);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setIsWaiting(true);

    try {
      let targetId = currentSessionId;

      // 2. 세션 없으면 생성
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

      // 3. 데이터 전송 준비
      const formData = new FormData();
      formData.append("message", userContent || "파일을 분석해줘.");

      // [NEW] 에이전트 모드 및 선택된 참조 자료 ID 전송
      formData.append("agent_mode", activeAgent);
      const selectedRefIds = references
        .filter((r) => r.checked)
        .map((r) => r.id);
      formData.append("context_ids", JSON.stringify(selectedRefIds));

      pendingFiles.forEach((file) => formData.append("files", file));

      // 4. API 호출
      const res = await api.post(`/chat/sessions/${targetId}/chat`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // 5. 응답 처리
      setMessages((prev) => [...prev, { role: "ai", content: res.data.reply }]);

      // [NEW] Retrieval 결과가 있다면 참조 목록에 추가 (Backend 응답 구조에 따름)
      if (res.data.found_documents) {
        // 예: found_documents = [{id: 101, title: 'Paper A', type: 'paper'}]
        const newDocs = res.data.found_documents.map((doc) => ({
          ...doc,
          checked: false,
        }));
        setReferences((prev) => [...prev, ...newDocs]);
        // 검색 결과가 있으면 패널 자동 열기
        if (!isRefPanelOpen) setIsRefPanelOpen(true);
      }

      // [NEW] 업로드한 파일도 참조 목록에 추가 (서버에서 ID 리턴받았다고 가정)
      if (res.data.uploaded_files) {
        const newFiles = res.data.uploaded_files.map((f) => ({
          ...f,
          checked: true,
        })); // 업로드 파일은 기본 선택
        setReferences((prev) => [...prev, ...newFiles]);
      }

      setPendingFiles([]);
    } catch (err) {
      console.error(err);
      alert("전송 중 오류가 발생했습니다.");
    } finally {
      setIsWaiting(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const activeAgentColor =
    AGENTS.find((a) => a.id === activeAgent)?.color || "#64748b";

  return (
    <div className="dashboard-container">
      {/* 모바일 오버레이 */}
      {isSidebarOpen && window.innerWidth <= 768 && (
        <div
          className="mobile-overlay"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* --- 1. Left Sidebar (History) --- */}
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

      {/* --- 2. Main Chat Area --- */}
      <main className="chat-main">
        {!isSidebarOpen && (
          <button
            className="sidebar-closed-toggle left"
            onClick={() => setIsSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>
        )}

        {/* [NEW] 우측 패널 토글 버튼 (헤더 영역) */}
        {!isRefPanelOpen && (
          <button
            className="sidebar-closed-toggle right"
            onClick={() => setIsRefPanelOpen(true)}
            title="Open Reference Panel"
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
              <h3>AI Research Assistant</h3>
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
              <Loader2 className="animate-spin" size={16} />
              <span style={{ color: activeAgentColor, fontWeight: 600 }}>
                {AGENTS.find((a) => a.id === activeAgent).name}
              </span>
              가 분석 중입니다...
            </div>
          )}
        </div>

        {/* --- Input Area with Agent Selector --- */}
        <div className="input-area-wrapper" onDragEnter={handleDrag}>
          {/* [NEW] Agent Selector Tabs */}
          <div className="agent-selector">
            {AGENTS.map((agent) => (
              <button
                key={agent.id}
                className={`agent-tab ${
                  activeAgent === agent.id ? "active" : ""
                }`}
                onClick={() => setActiveAgent(agent.id)}
                style={{
                  borderColor:
                    activeAgent === agent.id ? agent.color : "transparent",
                  color: activeAgent === agent.id ? agent.color : "#64748b",
                }}
              >
                <agent.icon size={16} />
                <span>{agent.name}</span>
              </button>
            ))}
          </div>

          {/* Drag Overlay */}
          {dragActive && (
            <div
              className="drag-overlay"
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <div className="drag-content">
                <UploadCloud size={48} className="drag-icon" />
                <p>파일을 여기에 놓으세요</p>
              </div>
            </div>
          )}

          {/* File Preview */}
          {pendingFiles.length > 0 && (
            <div className="file-preview-container">
              {pendingFiles.map((f, i) => (
                <div key={i} className="file-icon-wrapper" title={f.name}>
                  <div className="file-icon-box">
                    <FileText size={22} />
                    <button
                      className="file-remove-badge"
                      onClick={() => removePendingFile(i)}
                    >
                      <X size={10} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Input Box */}
          <div
            className="input-box-container"
            style={{ border: `1px solid ${activeAgentColor}40` }}
          >
            <label className="attach-btn-wrapper">
              <Paperclip size={24} className="action-icon" />
              <input
                type="file"
                multiple
                hidden
                onChange={(e) => handleFileSelection(e.target.files)}
                disabled={isWaiting}
              />
            </label>

            <textarea
              ref={textareaRef}
              className="main-text-input"
              value={input}
              onChange={handleInputResize}
              onKeyDown={handleKeyDown}
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
                <Loader2 className="animate-spin" size={24} />
              ) : (
                <Send
                  size={24}
                  className="action-icon"
                  style={{ color: activeAgentColor }}
                />
              )}
            </button>
          </div>
        </div>
      </main>

      {/* --- 3. [NEW] Right Sidebar (Reference Manager) --- */}
      <aside className={`right-sidebar ${!isRefPanelOpen ? "closed" : ""}`}>
        <div className="right-sidebar-header">
          <div className="header-left">
            <BookOpen size={18} />
            <h3>References</h3>
            <span className="badge">{references.length}</span>
          </div>
          <button
            className="toggle-btn text-dark"
            onClick={() => setIsRefPanelOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <div className="reference-list">
          {references.length === 0 ? (
            <div className="empty-ref">
              <Search size={32} />
              <p>
                검색된 논문이나
                <br />
                업로드된 파일이 없습니다.
              </p>
            </div>
          ) : (
            references.map((ref) => (
              <div
                key={ref.id}
                className={`ref-item ${ref.checked ? "selected" : ""}`}
              >
                <div className="ref-checkbox">
                  <input
                    type="checkbox"
                    checked={ref.checked}
                    onChange={() => toggleReference(ref.id)}
                  />
                </div>
                <div className="ref-info">
                  <span className={`ref-type ${ref.type}`}>{ref.type}</span>
                  <p className="ref-title" title={ref.title}>
                    {ref.title}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="right-sidebar-footer">
          <div className="footer-info">
            <CheckSquare size={14} />
            <span>Selected: {references.filter((r) => r.checked).length}</span>
          </div>
          <p className="help-text">
            선택한 자료가 다음 답변 생성에 사용됩니다.
          </p>
        </div>
      </aside>
    </div>
  );
};

export default Dashboard;
