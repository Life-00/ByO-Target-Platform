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
  CheckCircle2, // ✅ 추가됨: 분석 완료 아이콘
} from "lucide-react";
import api from "../../api"; // baseURL: http://localhost:8000/api/v1
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

  // References: { id, title, type, checked, isLocal, isLoading, file, status, itemType }
  const [references, setReferences] = useState([]);

  const [activeAgent, setActiveAgent] = useState("general");
  const [isRefPanelOpen, setIsRefPanelOpen] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth > 1024);
  const [dragActive, setDragActive] = useState(false);

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const isInitializing = useRef(false);

  // --- 초기화 로직: 세션 목록 로드 ---
  useEffect(() => {
    const init = async () => {
      if (isInitializing.current) return;
      isInitializing.current = true;
      try {
        const res = await api.get("/sessions");
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

  // --- 헬퍼 함수: References 병합 로직 ---
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
          status: f.status, // ✅ 분석 상태(indexed 등) 연동
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
          status: "staged", // 논문은 기본 상태
          checked: selectedIds.has(p.id),
          isLocal: false,
          isLoading: false,
          source: p.source,
          itemType: "paper",
        };
      });

      setReferences([...mappedFiles, ...mappedPapers]);
    } catch (err) {
      console.error("References 로드 실패", err);
    }
  };

  // --- 핸들러 ---

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
    if (window.innerWidth <= 768) setIsSidebarOpen(false);
    if (textareaRef.current) textareaRef.current.focus();
  };

  const handleDeleteSession = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("이 대화를 삭제하시겠습니까?")) return;
    try {
      await api.delete(`/sessions/${id}`);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (currentSessionId === id) handleResetChat();
    } catch (err) {
      alert("삭제 실패");
    }
  };

  const handleFileSelection = (files) => {
    const newFiles = Array.from(files || []);
    const uniqueFiles = newFiles.filter((file) => {
      return !references.some((ref) => ref.title === file.name);
    });

    if (uniqueFiles.length === 0 && newFiles.length > 0) {
      alert("이미 추가된 파일입니다.");
      return;
    }

    const newRefs = uniqueFiles.map((file, index) => {
      const ext = file.name.split(".").pop()?.toUpperCase() || "FILE";
      return {
        id: `local-${Date.now()}-${index}`,
        title: file.name,
        type: ext,
        status: "uploading",
        checked: true,
        isLocal: true,
        isLoading: true,
        file: file,
        itemType: "file",
      };
    });

    setReferences((prev) => [...prev, ...newRefs]);
    if (!isRefPanelOpen) setIsRefPanelOpen(true);

    setTimeout(() => {
      setReferences((prev) =>
        prev.map((ref) => (ref.isLoading ? { ...ref, isLoading: false } : ref))
      );
    }, 800);
  };

  const removeReference = async (id, isLocal) => {
    if (isLocal) {
      setReferences((prev) => prev.filter((ref) => ref.id !== id));
    } else {
      if (!currentSessionId) return;
      if (!window.confirm("서버에서 파일을 삭제하시겠습니까?")) return;
      try {
        const targetRef = references.find((r) => r.id === id);
        if (targetRef && targetRef.itemType === "file") {
          await api.delete(`/sessions/${currentSessionId}/files/${id}`);
        }
        setReferences((prev) => prev.filter((ref) => ref.id !== id));
      } catch (err) {
        console.error("파일 삭제 실패", err);
        alert("삭제 중 오류가 발생했습니다.");
      }
    }
  };

  const toggleReference = async (id) => {
    const target = references.find((r) => r.id === id);
    if (!target) return;

    // UI 선반영
    setReferences((prev) =>
      prev.map((ref) =>
        ref.id === id ? { ...ref, checked: !ref.checked } : ref
      )
    );

    if (target.isLocal) return;

    if (currentSessionId) {
      try {
        const apiItemType =
          target.itemType === "file" ? "uploaded_file" : "staged_paper";

        await api.post(`/sessions/${currentSessionId}/selections/toggle`, {
          item_type: apiItemType,
          item_id: id,
        });
      } catch (err) {
        console.error("Selection toggle failed", err);
        // 실패 시 롤백
        setReferences((prev) =>
          prev.map((ref) =>
            ref.id === id ? { ...ref, checked: !ref.checked } : ref
          )
        );
      }
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

  // --- 메시지 전송 및 에이전트 실행 ---
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

      // 1. 세션 생성
      if (!targetId) {
        const createRes = await api.post("/sessions", {
          title:
            userContent.substring(0, 15) +
            (userContent.length > 15 ? "..." : "") || "New Session",
        });
        targetId = createRes.data.id;
        setSessions((prev) => [createRes.data, ...prev]);
        setCurrentSessionId(targetId);
      }

      let uploadedItems = []; 

      // 2. 로컬 파일 업로드
      if (localFilesToSend.length > 0) {
        const fd = new FormData();
        localFilesToSend.forEach((ref) => fd.append("files", ref.file));

        const uploadRes = await api.post(
          `/sessions/${targetId}/files`,
          fd,
          { headers: { "Content-Type": "multipart/form-data" } }
        );

        uploadedItems = uploadRes.data || [];
        
        // 업로드된 파일 Selection 동기화
        for (const file of uploadedItems) {
          const correctId = file.file_id || file.id; 
          await api.post(`/sessions/${targetId}/selections/toggle`, {
            item_type: "uploaded_file",
            item_id: correctId,
          });
        }
      }

      // 업로드 성공 후 UI 갱신 (로컬->서버)
      if (uploadedItems.length > 0) {
        setReferences((prev) => {
          const existingServerFiles = prev.filter((r) => !r.isLocal);
          const newlyUploaded = uploadedItems.map((f) => {
            const title = f.original_name || f.filename || "FILE";
            const ext = (title.split(".").pop() || "FILE").toUpperCase();
            return {
              id: f.file_id || f.id, 
              title,
              type: ext,
              status: f.status || "uploaded",
              checked: true,
              isLocal: false,
              isLoading: false,
              itemType: "file",
            };
          });
          const remainingLocal = prev.filter((r) => r.isLocal && !r.checked);
          return [...existingServerFiles, ...newlyUploaded, ...remainingLocal];
        });
      }

      // 3. 에이전트별 요청
      let resData = null;
      let replyText = "";

      // 컨텍스트 ID 수집
      const uploadedIds = uploadedItems.map(f => f.file_id || f.id);
      const serverRefIds = references
        .filter((r) => !r.isLocal && r.checked)
        .map((r) => r.id);
      const contextIds = [...serverRefIds, ...uploadedIds];

      if (activeAgent === "general") {
        const res = await api.post(`/sessions/${targetId}/chat`, {
          message: userContent || "파일을 분석해줘.",
          context_ids: contextIds
        });
        resData = res.data;
        replyText = resData.reply || "답변이 도착했습니다."; 
      } else if (activeAgent === "retrieval") {
        const res = await api.post(`/sessions/${targetId}/research`, {
          query: userContent || "관련 논문 검색",
          top_k: 5,
        });
        resData = res.data; 
        replyText = `검색 완료: ${resData?.length || 0}건의 논문을 찾았습니다.`;
      } else if (activeAgent === "extractor") {
        const res = await api.post(
          `/sessions/${targetId}/extract?force=false`,
          {}
        );
        resData = res.data; 
        replyText = "선택된 파일에 대한 정보 추출 작업을 완료했습니다.";
      } else if (activeAgent === "synthesizer") {
        const res = await api.post(`/sessions/${targetId}/report`, {
          prompt: userContent || "보고서 작성해줘",
        });
        resData = res.data; 
        replyText = resData.content;
      }

      // 4. 상태 갱신
      const [msgRes] = await Promise.all([
        api.get(`/sessions/${targetId}/messages`),
        fetchAndMergeReferences(targetId)
      ]);
      
      setMessages(msgRes.data);

    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "오류가 발생했습니다. 다시 시도해주세요." },
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

      {/* Left Sidebar */}
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

      {/* Main Chat Area */}
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
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content}
                  </ReactMarkdown>
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

      {/* Right Sidebar */}
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
            references.map((ref) => {
              // ✅ 분석 완료 상태 체크 (백엔드가 'indexed'로 보내줌)
              const isIndexed = ref.status === "indexed";

              return (
                <div
                  key={ref.id}
                  className={`ref-item ${ref.checked ? "selected" : ""} ${isIndexed ? "indexed" : ""}`}
                  onClick={() => !ref.isLoading && toggleReference(ref.id)}
                >
                  <div className="ref-checkbox-area">
                    {ref.isLoading ? (
                      <Loader2 className="animate-spin" size={14} color="#94a3b8" />
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
                      {/* 뱃지 스타일 (indexed일 때 다름) */}
                      <span className={`ref-ext-badge ${isIndexed ? "indexed-badge" : ""}`}>
                        {ref.type}
                      </span>
                      {/* ✅ 분석 완료 라벨 */}
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

                  <button
                    className="ref-delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeReference(ref.id, ref.isLocal);
                    }}
                  >
                    <X size={12} />
                  </button>
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