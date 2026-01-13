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

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const isInitializing = useRef(false);

  useEffect(() => {
    const init = async () => {
      if (isInitializing.current) return;
      isInitializing.current = true;
      try {
        const res = await api.get("/chat/sessions");
        if (res.data.length > 0) {
          setSessions(res.data);
          handleSelectSession(res.data[0].id);
        } else {
          handleNewChat();
        }
      } catch (err) {
        isInitializing.current = false;
      }
    };
    init();
  }, []);

  // 메시지가 추가되거나 입력창 높이가 변할 때 스크롤 조정
  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, isWaiting, input]);

  const handleSelectSession = async (id) => {
    setCurrentSessionId(id);
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
    resetInputHeight();
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

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
    // Shift + Enter는 기본 동작(줄바꿈)을 수행하므로 별도 처리 불필요
  };

  return (
    <div className="dashboard-container">
      <aside className="sidebar">
        <div className="sidebar-title">
          <Microscope size={26} /> <span>TV-A</span>
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

      <main className="chat-main">
        <div className="message-container" ref={scrollRef}>
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
              disabled={!currentSessionId || isWaiting}
              rows={1} // 기본 줄 수
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
