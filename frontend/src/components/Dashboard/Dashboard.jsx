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
  }, [messages]);

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

  // 파일 업로드 처리
  const handleFileUpload = async (files) => {
    setIsUploading(true);
    console.log("--- BACKEND FILE UPLOAD IN PROGRESS ---");
    for (const file of files) {
      console.log(`PRINT: Processing ${file.name}...`);
      await new Promise((r) => setTimeout(r, 700)); // 업로드 시뮬레이션
    }
    setPendingFiles((prev) => [...prev, ...files]);
    setIsUploading(false);
  };

  // 메시지 전송 처리
  const handleSendMessage = async () => {
    if (
      isUploading ||
      isWaiting ||
      (!input.trim() && pendingFiles.length === 0)
    )
      return;

    const userMsg = input;
    const currentFiles = [...pendingFiles];

    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);

    setIsWaiting(true);
    setInput("");
    setPendingFiles([]);
    console.log(
      `[REQUEST] User sent message. Disabling button until response.`
    );

    console.log("PRINT: Sending request to Upstage Solar API...");
    await new Promise((r) => setTimeout(r, 1500)); // 답변 생성 시간

    const aiResponse =
      "분석이 완료되었습니다. 제공해주신 데이터를 바탕으로 타겟 유효성 검증 리포트를 생성했습니다.";
    setMessages((prev) => [...prev, { role: "ai", content: aiResponse }]);

    setIsWaiting(false);
    console.log(`[RESPONSE] Received answer. Re-enabling button.`);
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
      {/* 드래그 앤 드롭 오버레이 */}
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
            <span>Cancer Target Validation Study - Session 1</span>
          </div>

          <div className="chat-item">
            <MessageSquare size={18} />
            <span>Protein Interaction Analysis</span>
          </div>
        </div>

        <button onClick={onLogout} className="logout-btn">
          <LogOut size={18} />
          <span>로그아웃</span>
        </button>
      </aside>

      {/* 메인 채팅 영역 */}
      <main className="chat-main">
        {/* 메시지 리스트 */}
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
              <Loader2 className="animate-spin" size={16} /> 에이전트가 생각
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
            {/* 파일 첨부 버튼 */}
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

            {/* 텍스트 입력부 */}
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
                isWaiting ? "답변을 기다리는 중..." : "메시지를 입력하세요..."
              }
              disabled={isUploading || isWaiting}
            />

            {/* 전송 버튼 */}
            <button
              className="send-button"
              onClick={handleSendMessage}
              disabled={
                isUploading ||
                isWaiting ||
                (!input.trim() && pendingFiles.length === 0)
              }
              style={{
                background: "none",
                border: "none",
                color:
                  isUploading ||
                  isWaiting ||
                  (!input.trim() && pendingFiles.length === 0)
                    ? "#cbd5e1"
                    : "var(--bio-primary)",
                cursor: isUploading || isWaiting ? "not-allowed" : "pointer",
              }}
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
