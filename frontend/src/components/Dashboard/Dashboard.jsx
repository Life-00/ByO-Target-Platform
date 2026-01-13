import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown"; // 추가
import remarkGfm from "remark-gfm"; // 추가
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
  Menu, // 햄버거 메뉴 아이콘
  ChevronLeft, // 닫기 화살표 아이콘
} from "lucide-react";
import api from "../../api";
import "./Dashboard.css";

const Dashboard = ({ onLogout }) => {
  // --- 상태 관리 ---
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null); // null = 새 채팅 준비 상태
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [pendingFiles, setPendingFiles] = useState([]);
  const [isWaiting, setIsWaiting] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  // 반응형 사이드바 상태 (기본값: 데스크탑은 열림, 모바일은 닫힘)
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth > 768);

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const isInitializing = useRef(false);

  // --- 초기화 로직 (접속 시) ---
  useEffect(() => {
    const init = async () => {
      if (isInitializing.current) return;
      isInitializing.current = true;
      try {
        const res = await api.get("/chat/sessions");
        setSessions(res.data);
        // 중요: 최근 세션을 자동으로 선택하지 않음 -> 빈 화면 유지
        // 사용자가 명시적으로 클릭하거나 입력을 시작해야 세션 활성화
      } catch (err) {
        console.error("세션 목록 로드 실패", err);
      }
    };
    init();

    // 화면 크기 변경 감지하여 사이드바 상태 자동 조절
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setIsSidebarOpen(false);
      } else {
        setIsSidebarOpen(true);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // 메시지가 추가되거나 입력창 높이가 변할 때 스크롤 조정
  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isWaiting, input]);

  // --- 기능 핸들러 ---

  // 세션 클릭
  const handleSelectSession = async (id) => {
    setCurrentSessionId(id);
    try {
      const res = await api.get(`/chat/sessions/${id}/messages`);
      setMessages(res.data);
      // 모바일에서는 선택 시 사이드바 닫기
      if (window.innerWidth <= 768) setIsSidebarOpen(false);
    } catch (err) {
      console.error(err);
    }
  };

  // 'New Chatting' 버튼 클릭 -> 상태 초기화 (실제 생성은 메시지 보낼 때)
  const handleResetChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setPendingFiles([]);
    setInput("");
    if (window.innerWidth <= 768) setIsSidebarOpen(false);
  };

  // 세션 삭제
  const handleDeleteSession = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("이 대화를 삭제하시겠습니까?")) return;
    try {
      await api.delete(`/chat/sessions/${id}`);
      const updated = sessions.filter((s) => s.id !== id);
      setSessions(updated);

      // 현재 보고 있는 세션을 삭제했다면 초기화
      if (currentSessionId === id) {
        handleResetChat();
      }
    } catch (err) {
      alert("삭제 실패");
    }
  };

  // 파일 선택
  const handleFileSelection = (files) => {
    setPendingFiles((prev) => [...prev, ...Array.from(files)]);
  };

  const removePendingFile = (index) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // 드래그 앤 드롭
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

  // 입력창 높이 자동 조절 함수
  const handleInputResize = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  // 전송 후 높이 초기화
  const resetInputHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleSendMessage = async () => {
    if ((!input.trim() && pendingFiles.length === 0) || isWaiting) return;

    const userContent = input.trim();

    // 1. 화면에 사용자 메시지 즉시 표시
    setMessages((prev) => [
      ...prev,
      { role: "user", content: userContent || "파일 분석 요청" },
    ]);
    setInput("");
    resetInputHeight();
    setIsWaiting(true);

    try {
      let targetId = currentSessionId;

      // 2. 세션 ID가 없으면(=새 채팅) 서버에 세션 생성 요청
      if (!targetId) {
        const createRes = await api.post("/chat/sessions");
        targetId = createRes.data.id;

        // 제목 생성 (내용 앞부분 따오기)
        const newTitle = userContent
          ? userContent.substring(0, 15) +
            (userContent.length > 15 ? "..." : "")
          : "새로운 대화";

        // 제목 업데이트
        await api.patch(`/chat/sessions/${targetId}`, { title: newTitle });

        // 상태 업데이트
        const newSession = { ...createRes.data, title: newTitle };
        setSessions((prev) => [newSession, ...prev]);
        setCurrentSessionId(targetId);
      }

      // 3. 메시지 전송
      const formData = new FormData();
      formData.append("message", userContent || "파일을 분석해줘.");
      pendingFiles.forEach((file) => formData.append("files", file));

      const res = await api.post(`/chat/sessions/${targetId}/chat`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setMessages((prev) => [...prev, { role: "ai", content: res.data.reply }]);
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
    // Shift + Enter는 기본 동작(줄바꿈)을 수행하므로 별도 처리 불필요
  };

  return (
    <div className="dashboard-container">
      {/* 모바일 오버레이 (사이드바 열렸을 때 배경) */}
      {isSidebarOpen && window.innerWidth <= 768 && (
        <div
          className="mobile-overlay"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* --- 사이드바 --- */}
      <aside className={`sidebar ${!isSidebarOpen ? "closed" : ""}`}>
        <div className="sidebar-header">
          <div className="sidebar-title">
            <Microscope size={26} /> <span>TV-A</span>
          </div>
          {/* 메뉴 닫기 버튼 (제목 우측) */}
          <button
            className="toggle-btn"
            onClick={() => setIsSidebarOpen(false)}
            aria-label="Close menu"
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

      {/* --- 메인 영역 --- */}
      <main className="chat-main">
        {/* 메뉴 열기 버튼 (사이드바 닫혔을 때만 보임) */}
        {!isSidebarOpen && (
          <button
            className="sidebar-closed-toggle"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
        )}

        <div className="message-container" ref={scrollRef}>
          {/* 빈 화면 안내 (세션이 선택되지 않았거나 메시지가 없을 때) */}
          {messages.length === 0 && !currentSessionId && (
            <div className="empty-state">
              <Microscope
                size={56}
                style={{ marginBottom: 20, opacity: 0.2 }}
              />
              <h3>무엇을 도와드릴까요?</h3>
              <p style={{ marginTop: 10, fontSize: 14 }}>
                새로운 연구 분석을 시작하려면 아래에 질문을 입력하세요.
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`msg-bubble ${m.role}`}>
              {/* AI 메시지는 마크다운 렌더링, 유저는 텍스트 그대로 */}
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

        {/* 하단 입력 영역 */}
        <div className="input-area-wrapper" onDragEnter={handleDrag}>
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

          <div className="input-box-container">
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

            {/* textarea로 변경 */}
            <textarea
              ref={textareaRef}
              className="main-text-input"
              value={input}
              onChange={handleInputResize}
              onKeyDown={handleKeyDown}
              placeholder="질문을 입력하세요..."
              disabled={isWaiting}
              rows={1} // 기본 줄 수
            />

            <button
              className="icon-send-btn"
              onClick={handleSendMessage}
              disabled={isWaiting}
            >
              {isWaiting ? (
                <Loader2 className="animate-spin" size={24} />
              ) : (
                <Send size={24} className="action-icon" />
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
