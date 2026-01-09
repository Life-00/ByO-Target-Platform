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
  Image as ImageIcon,
  Loader2,
} from "lucide-react";
import api from "../../api";
import "./Dashboard.css";

const Dashboard = ({ onLogout }) => {
  const [messages, setMessages] = useState([
    {
      role: "ai",
      content:
        "새로운 분석 세션이 시작되었습니다. 논문을 업로드하거나 질문을 입력하세요.",
    },
  ]);
  const [input, setInput] = useState("");
  const [pendingFiles, setPendingFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isWaiting]);

  // 새 채팅 세션 시작
  const handleNewChat = () => {
    console.log("--- Starting New Chat Session ---");
    setMessages([
      {
        role: "ai",
        content: "새로운 분석 세션이 시작되었습니다. 무엇을 도와드릴까요?",
      },
    ]);
    setPendingFiles([]);
    setInput("");
    setIsWaiting(false);
  };

  // 파일 업로드 처리 (현재는 시뮬레이션, 추후 백엔드 연동 예정)
  const handleFileUpload = async (files) => {
    setIsUploading(true);
    console.log("[FRONT] Processing files for upload...");

    for (const file of files) {
      console.log(`- Attached: ${file.name}`);
      // 실제 파일 업로드 로직은 차후 '파일 분석' 기능 구현 시 추가
    }

    setPendingFiles((prev) => [...prev, ...files]);
    setIsUploading(false);
  };

  //  메시지 전송 처리 (실제 백엔드 Solar-Pro 연동)
  const handleSendMessage = async () => {
    if (
      isUploading ||
      isWaiting ||
      (!input.trim() && pendingFiles.length === 0)
    )
      return;

    const userMsgContent = input;
    // 1. 화면에 사용자 메시지 먼저 표시
    setMessages((prev) => [...prev, { role: "user", content: userMsgContent }]);

    // 상태 초기화
    setIsWaiting(true);
    setInput("");
    setPendingFiles([]);

    console.log(`[REQUEST] Sending message to Solar-Pro: "${userMsgContent}"`);

    try {
      // 2. 백엔드 API 호출
      // 텍스트만 보낼 때는 FormData 혹은 JSON 둘 다 가능하지만,
      // 나중에 파일 전송을 고려해 FormData 형식을 사용합니다.
      const formData = new FormData();
      formData.append("message", userMsgContent);

      const response = await api.post("/chat", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      // 3. 백엔드로부터 받은 Solar-Pro의 답변을 화면에 추가
      const aiAnswer = response.data.reply;
      console.log("[RESPONSE] Solar-Pro replied successfully.");

      setMessages((prev) => [...prev, { role: "ai", content: aiAnswer }]);
    } catch (error) {
      console.error("[CHAT-ERROR]", error.response?.data || error.message);
      alert(
        "에이전트와 통신 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
      );

      // 에러 시 안내 메시지 추가
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "죄송합니다. 서버 응답에 문제가 발생했습니다." },
      ]);
    } finally {
      setIsWaiting(false);
    }
  };

  // 대기 중인 파일 삭제
  const removeFile = (idx) =>
    setPendingFiles((prev) => prev.filter((_, i) => i !== idx));

  return (
    <div
      className="dashboard-container"
      onDragOver={(e) => {
        e.preventDefault();
        setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragActive(false);
        handleFileUpload(Array.from(e.dataTransfer.files));
      }}
    >
      {dragActive && (
        <div className="drag-overlay">
          <h2>파일을 여기에 놓으세요</h2>
        </div>
      )}

      {/* 사이드바 영역 */}
      <aside className="sidebar">
        <div className="sidebar-title">
          <Microscope size={26} />
          <span>TV-A</span>
        </div>

        <button className="new-chat-btn" onClick={handleNewChat}>
          <Plus size={20} /> New Session
        </button>

        <div className="chat-list">
          <p className="chat-list-header">RESEARCH HISTORY</p>
          <div className="chat-item active">
            <MessageSquare size={18} />
            <span>현재 분석 세션</span>
          </div>
        </div>

        <button onClick={onLogout} className="logout-btn">
          <LogOut size={18} />
          <span>로그아웃</span>
        </button>
      </aside>

      {/* 메인 채팅 영역 */}
      <main className="chat-main">
        <div className="message-container" ref={scrollRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg-bubble ${m.role}`}>
              {m.content}
            </div>
          ))}
          {isWaiting && (
            <div
              className="msg-bubble ai"
              style={{ display: "flex", gap: "8px", alignItems: "center" }}
            >
              <Loader2 className="animate-spin" size={16} /> Solar-Pro가 분석
              중입니다...
            </div>
          )}
        </div>

        {/* 업로드 대기 파일 프리뷰 */}
        {pendingFiles.length > 0 && (
          <div className="file-preview-area">
            {pendingFiles.map((f, i) => (
              <div key={i} className="file-chip">
                {f.type.includes("image") ? (
                  <ImageIcon size={14} />
                ) : (
                  <FileText size={14} />
                )}
                <span>{f.name}</span>
                <X
                  size={14}
                  className="file-chip-remove"
                  onClick={() => removeFile(i)}
                />
              </div>
            ))}
          </div>
        )}

        {/* 입력창 영역 */}
        <div className="input-area-wrapper">
          <div className="input-box-container">
            <label
              style={{
                cursor: isUploading || isWaiting ? "default" : "pointer",
              }}
            >
              <Paperclip
                size={24}
                style={{
                  color: isUploading || isWaiting ? "#cbd5e1" : "#64748b",
                }}
              />
              <input
                type="file"
                multiple
                hidden
                disabled={isUploading || isWaiting}
                onChange={(e) => handleFileUpload(Array.from(e.target.files))}
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
              placeholder={
                isWaiting
                  ? "분석 답변을 기다리는 중..."
                  : "타겟 분석에 대해 질문하세요..."
              }
              disabled={isUploading || isWaiting}
            />

            <button
              className="send-button"
              onClick={handleSendMessage}
              disabled={
                isUploading ||
                isWaiting ||
                (!input.trim() && pendingFiles.length === 0)
              }
            >
              {isUploading || isWaiting ? (
                <Loader2 className="animate-spin" size={24} />
              ) : (
                <Send size={24} />
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
