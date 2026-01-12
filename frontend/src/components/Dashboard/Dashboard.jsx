import React, { useState, useRef, useEffect } from "react";
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
  Menu, // 토글 아이콘 추가
} from "lucide-react";
import api from "../../api";
import "./Dashboard.css";

const Dashboard = ({ onLogout }) => {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [pendingFiles, setPendingFiles] = useState([]);
  const [isWaiting, setIsWaiting] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  // 사이드바 상태 관리 (기본값: 데스크톱은 열림, 모바일은 닫힘)
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth > 768);

  const scrollRef = useRef(null);
  const isInitializing = useRef(false);

  // 화면 크기 변경 감지 (반응형 대응)
  useEffect(() => {
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

  useEffect(() => {
    const init = async () => {
      if (isInitializing.current) return;
      isInitializing.current = true;
      try {
        const res = await api.get("/chat/sessions");
        if (res.data.length > 0) {
          setSessions(res.data);
          // 초기 로드 시에는 세션만 세팅하고, 모바일에서는 자동 선택 안 함 (목록 보여주기 위함)
          if (window.innerWidth > 768) {
            handleSelectSession(res.data[0].id);
          }
        } else {
          handleNewChat();
        }
      } catch (err) {
        isInitializing.current = false;
      }
    };
    init();
  }, []);

  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isWaiting]);

  const handleSelectSession = async (id) => {
    setCurrentSessionId(id);

    // 모바일에서는 채팅방 선택 시 사이드바 닫기 (UX 개선)
    if (window.innerWidth <= 768) {
      setIsSidebarOpen(false);
    }

    try {
      const res = await api.get(`/chat/sessions/${id}/messages`);
      setMessages(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleNewChat = async () => {
    try {
      const res = await api.post("/chat/sessions");
      setSessions((prev) => [res.data, ...prev]);
      handleSelectSession(res.data.id);
    } catch (err) {
      alert("생성 실패");
    }
  };

  const handleDeleteSession = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("삭제할까요?")) return;
    try {
      await api.delete(`/chat/sessions/${id}`);
      const updated = sessions.filter((s) => s.id !== id);
      setSessions(updated);
      if (currentSessionId === id) {
        if (updated.length > 0) handleSelectSession(updated[0].id);
        else window.location.reload();
      }
    } catch (err) {
      alert("삭제 실패");
    }
  };

  const handleFileSelection = (files) => {
    setPendingFiles((prev) => [...prev, ...Array.from(files)]);
  };

  const removePendingFile = (index) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files);
    }
  };

  const handleSendMessage = async () => {
    if (
      (!input.trim() && pendingFiles.length === 0) ||
      isWaiting ||
      !currentSessionId
    )
      return;

    const userContent = input.trim();
    const targetId = currentSessionId;
    const isFirst = messages.length <= 1;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userContent || "파일 분석 요청" },
    ]);
    setInput("");
    setIsWaiting(true);

    try {
      if (isFirst && userContent) {
        const title =
          userContent.substring(0, 15) + (userContent.length > 15 ? "..." : "");
        await api.patch(`/chat/sessions/${targetId}`, { title });
        setSessions((prev) =>
          prev.map((s) => (s.id === targetId ? { ...s, title } : s))
        );
      }

      const formData = new FormData();
      formData.append("message", userContent || "파일을 분석해줘.");
      pendingFiles.forEach((file) => formData.append("files", file));

      const res = await api.post(`/chat/sessions/${targetId}/chat`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setMessages((prev) => [...prev, { role: "ai", content: res.data.reply }]);
      setPendingFiles([]);
    } catch (err) {
      alert("전송 실패");
    } finally {
      setIsWaiting(false);
    }
  };

  return (
    <div className="dashboard-container">
      {/* 모바일용 오버레이 (사이드바 열렸을 때 배경 어둡게) */}
      <div
        className={`mobile-overlay ${isSidebarOpen ? "active" : ""}`}
        onClick={() => setIsSidebarOpen(false)}
      />

      {/* 사이드바 */}
      <aside className={`sidebar ${isSidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-header">
          <div className="sidebar-title">
            <Microscope size={26} /> <span>TV-A</span>
          </div>
          {/* 모바일에서 사이드바 닫기 버튼 */}
          <button
            className="mobile-close-btn"
            onClick={() => setIsSidebarOpen(false)}
          >
            <X size={24} />
          </button>
        </div>

        <button className="new-chat-btn" onClick={handleNewChat}>
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

      {/* 메인 채팅 영역 */}
      <main className="chat-main">
        {/* 상단 헤더 (토글 버튼 포함) */}
        <header className="chat-header">
          <button
            className="sidebar-toggle-btn"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          >
            <Menu size={24} color="#334155" />
          </button>
          <span className="header-title">
            {sessions.find((s) => s.id === currentSessionId)?.title ||
              "Target Validation Assistant"}
          </span>
        </header>

        <div className="message-container" ref={scrollRef}>
          {messages.length === 0 && !currentSessionId && (
            <div className="empty-state">
              <Microscope size={48} color="#cbd5e1" />
              <p>새로운 채팅을 시작하거나 기존 기록을 선택하세요.</p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`msg-bubble ${m.role}`}>
              {m.content}
            </div>
          ))}
          {isWaiting && (
            <div className="msg-bubble ai loading-msg">
              <Loader2 className="animate-spin" size={16} /> 분석 중...
            </div>
          )}
        </div>

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
            <input
              className="main-text-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) =>
                e.key === "Enter" &&
                !e.shiftKey &&
                (e.preventDefault(), handleSendMessage())
              }
              placeholder="질문을 입력하세요..."
              disabled={!currentSessionId || isWaiting}
            />
            <button
              className="icon-send-btn"
              onClick={handleSendMessage}
              disabled={!currentSessionId || isWaiting}
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
