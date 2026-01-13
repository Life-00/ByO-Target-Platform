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
  FileText,
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
  FileUp, // [NEW] 파일 업로드 아이콘
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

  // [Mod] References 통합 관리 (서버 파일 + 로컬 업로드 대기 파일)
  // 구조: { id: string|number, title: string, type: 'file'|'paper', checked: boolean, file?: File, isLocal?: boolean }
  const [references, setReferences] = useState([]);

  const [activeAgent, setActiveAgent] = useState("general");
  const [isRefPanelOpen, setIsRefPanelOpen] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth > 1024);
  const [dragActive, setDragActive] = useState(false); // 드래그 상태 (우측 패널용)

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null); // 우측 패널 파일 인풋용
  const isInitializing = useRef(false);

  // --- 초기화 ---
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
      // 서버에서 해당 세션의 문서 목록을 가져와 references에 세팅한다고 가정
      // const docRes = await api.get(...)
      // setReferences(docRes.data);
      setReferences([]); // 임시 초기화
      if (window.innerWidth <= 768) setIsSidebarOpen(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setReferences([]); // 파일 목록도 초기화
    setInput("");
    setActiveAgent("general");
    if (window.innerWidth <= 768) setIsSidebarOpen(false);
    if (textareaRef.current) textareaRef.current.focus();
  };

  // [Mod] 파일 선택 핸들러 (중복 방지 & Reference로 추가)
  const handleFileSelection = (files) => {
    const newFiles = Array.from(files);

    // 중복 체크
    const uniqueFiles = newFiles.filter((file) => {
      const isDuplicate = references.some((ref) => ref.title === file.name);
      return !isDuplicate;
    });

    if (uniqueFiles.length === 0) {
      alert("이미 추가된 파일입니다.");
      return;
    }

    const newRefs = uniqueFiles.map((file, index) => ({
      id: `local-${Date.now()}-${index}`, // 임시 ID
      title: file.name,
      type: "file",
      checked: true, // 업로드 시 기본 선택
      isLocal: true, // 로컬 파일임을 표시
      file: file, // 실제 파일 객체 저장
    }));

    setReferences((prev) => [...prev, ...newRefs]);

    // 파일 추가 시 우측 패널이 닫혀있다면 열어줌
    if (!isRefPanelOpen) setIsRefPanelOpen(true);
  };

  // 참조 자료 삭제 (취소)
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

  // [Mod] 드래그 앤 드롭 (우측 사이드바 영역)
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

  const handleSendMessage = async () => {
    // 로컬 파일 중 체크된 것이 있는지 확인
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
          ? userContent.substring(0, 15) + "..."
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

      // 1. 이미 서버에 있는 파일 ID들 (isLocal이 아닌 것들)
      const serverRefIds = references
        .filter((r) => !r.isLocal && r.checked)
        .map((r) => r.id);
      formData.append("context_ids", JSON.stringify(serverRefIds));

      // 2. 새로 업로드할 파일들 (isLocal인 것들)
      localFilesToSend.forEach((ref) => {
        formData.append("files", ref.file);
      });

      const res = await api.post(`/chat/sessions/${targetId}/chat`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setMessages((prev) => [...prev, { role: "ai", content: res.data.reply }]);

      // 3. 전송 성공 후, 로컬 파일을 서버 파일로 상태 업데이트 (ID 교체 등)
      // 예: 서버가 업로드된 파일들의 실제 ID를 uploaded_files로 돌려준다고 가정
      if (res.data.uploaded_files) {
        // 기존 로컬 파일 제거하고 서버 응답으로 대체하거나 상태 업데이트 로직 필요
        // 여기서는 간단히 로컬 플래그 제거 형태로 가정
        const updatedRefs = references.map((ref) => {
          if (ref.isLocal && ref.checked) {
            // 실제로는 서버에서 받은 ID로 교체해야 함
            return { ...ref, isLocal: false };
          }
          return ref;
        });
        setReferences(updatedRefs);
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

      {/* --- Left Sidebar --- */}
      <aside className={`sidebar ${!isSidebarOpen ? "closed" : ""}`}>
        {/* (기존 코드 동일) */}
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

      {/* --- Main Chat Area --- */}
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
              Analyzing...
            </div>
          )}
        </div>

        {/* --- Floating Input Area --- */}
        <div className="floating-input-wrapper">
          {/* Agent Selector (Floating top) */}
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
                <agent.icon size={14} />
                <span>{agent.name}</span>
              </button>
            ))}
          </div>

          {/* Input Box */}
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

      {/* --- Right Sidebar (Reference & Upload) --- */}
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
            {/* [Mod] 업로드 버튼을 여기로 이동 */}
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

        {/* 드래그 오버레이 메시지 */}
        {dragActive && (
          <div className="sidebar-drag-overlay">
            <UploadCloud size={40} />
            <p>Drop files to add references</p>
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
                <div className="ref-checkbox">
                  <input
                    type="checkbox"
                    checked={ref.checked}
                    onChange={() => toggleReference(ref.id)}
                  />
                </div>
                <div className="ref-info">
                  <div className="ref-meta">
                    <span className={`ref-type ${ref.type}`}>{ref.type}</span>
                    {ref.isLocal && (
                      <span className="ref-badge-local">Ready</span>
                    )}
                  </div>
                  <p className="ref-title" title={ref.title}>
                    {ref.title}
                  </p>
                </div>
                {/* 삭제(취소) 버튼 */}
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
          <p className="help-text">
            선택된 자료는 Agent에게
            <br />
            컨텍스트로 제공됩니다.
          </p>
        </div>
      </aside>
    </div>
  );
};

export default Dashboard;
