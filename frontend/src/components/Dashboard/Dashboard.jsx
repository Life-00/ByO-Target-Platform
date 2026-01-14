import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Microscope, Plus, Zap, FileUp, CheckCircle2,
  X, Send, Sparkles, Cpu, Play, Download, ExternalLink,
  Loader2, Layout, LogOut, ClipboardCheck, Ban
} from "lucide-react";
import api from "../../api";
import "./Dashboard.css";

// ==================================================================================
// [Micro Component] FileListItem (유지)
// ==================================================================================
const FileListItem = React.memo(({ item, isActive, onSelect, onToggle, onDelete }) => {
  const handleToggle = (e) => { e.stopPropagation(); onToggle(item); };
  const handleDelete = (e) => { e.stopPropagation(); onDelete(item); };
  const handleSelect = () => onSelect(item);

  return (
    <div className={`item-card ${isActive ? "active" : ""}`} onClick={handleSelect}>
      <button className="delete-btn" onClick={handleDelete}><X size={12}/></button>
      <div className="card-content">
        <div className={`checkbox-icon ${item.checked ? "checked" : ""}`} onClick={handleToggle}>
          {item.checked ? <CheckCircle2 size={18}/> : <div style={{width:'16px', height:'16px', border:'2px solid #cbd5e1', borderRadius:'50%'}}></div>}
        </div>
        <div className="item-info">
          <div className="item-title">{item.title}</div>
          <div className="item-meta">
            <span className="badge">{item.itemType}</span>
            {(item.status === "indexed" || item.status === "analyzed") && <span className="badge analyzed">Analyzed</span>}
            {item.status === "uploading" && <span className="badge" style={{color: 'orange'}}>Uploading...</span>}
          </div>
        </div>
      </div>
    </div>
  );
}, (prev, next) => {
  return (
    prev.isActive === next.isActive &&
    prev.item.checked === next.item.checked &&
    prev.item.title === next.item.title &&
    prev.item.status === next.item.status
  );
});

// ==================================================================================
// [Component 1] LeftPanel
// ==================================================================================
const LeftPanel = React.memo(({
  sessions, currentSessionId, leftTab, setLeftTab,
  references, viewingRef,
  onSelectSession, onCreateSessionTrigger, 
  onToggleRef, onRemoveRef, onSelectRef,
  onUploadTrigger, onRetrievalTrigger, onLogout
}) => {
  const fileInputRef = useRef(null);

  const handleUploadChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onUploadTrigger(e.target.files);
    }
  };

  return (
    <section className="left-panel">
      <div className="brand-header">
        <div className="logo-box"><Microscope size={22} color="white"/></div>
        <div className="brand-text"><h1>TV-A</h1><p>Bio-Terminal</p></div>
      </div>
      <div className="session-info">
        <p className="session-label">Current Session</p>
        <p className="session-value">{sessions.find(s=>s.id===currentSessionId)?.title || "Select Session"}</p>
      </div>
      <div className="tab-container">
        <div className="tab-group">
          {["session", "library", "report"].map(tab => (
            <button key={tab} onClick={() => setLeftTab(tab)} className={`tab-btn ${leftTab === tab ? "active" : ""}`}>{tab}</button>
          ))}
        </div>
      </div>
      <div className="list-area custom-scrollbar">
        {leftTab === "session" && (
          <>
            <button className="btn-secondary" onClick={onCreateSessionTrigger}><Plus size={14}/> New Session</button>
            {sessions.map(s => (
              <div key={s.id} onClick={() => onSelectSession(s.id)} className={`item-card ${currentSessionId === s.id ? "active" : ""}`}>
                <div className="card-content">
                  <div className="item-info">
                    <div className="item-title">{s.title}</div>
                    <div className="item-meta"><span className="badge">{new Date(s.created_at).toLocaleDateString()}</span></div>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
        {leftTab === "library" && (
          <>
            <button className="btn-primary" onClick={onRetrievalTrigger}><Zap size={14}/> Retrieval Agent</button>
            <div className="upload-group">
              <button className="btn-secondary" style={{marginBottom:0}} onClick={() => fileInputRef.current.click()}><FileUp size={14}/> Upload</button>
              <input type="file" multiple hidden ref={fileInputRef} onChange={handleUploadChange} />
            </div>
            
            {references.map(ref => (
              <FileListItem 
                key={ref.id}
                item={ref}
                isActive={viewingRef?.id === ref.id}
                onSelect={onSelectRef}
                onToggle={onToggleRef}
                onDelete={onRemoveRef}
              />
            ))}
          </>
        )}
        {leftTab === "report" && (
          <div className="empty-state">
            <ClipboardCheck size={32} style={{opacity:0.3, marginBottom:'12px'}}/>
            <p style={{fontSize:'12px'}}>Reports will be archived here.</p>
          </div>
        )}
      </div>
      <div className="panel-footer">
        <button className="logout-btn" onClick={onLogout}><LogOut size={14}/> Logout</button>
        <div className="sync-badge"><div className="status-dot"></div>Synced</div>
      </div>
    </section>
  );
});

// ==================================================================================
// [Component 2] CenterPanel
// ==================================================================================
const CenterPanel = React.memo(({ 
  viewingRef, centerTab, setCenterTab, 
  pdfUrl, isPdfLoading, summaryContent, isSummaryLoading,
  onDownload 
}) => {
  // 요약과 초록 분리 마커
  const SUMMARY_MARKER = "\n\n---SUMMARY_SECTION---\n";
  const cleanAbstract = viewingRef?.abstract?.split(SUMMARY_MARKER)[0] || "내용 없음";

  return (
    <section className="center-panel">
      <div className="center-header">
        <button onClick={() => setCenterTab("original")} className={`nav-tab ${centerTab === "original" ? "active" : ""}`}>Original Paper</button>
        <button onClick={() => setCenterTab("analysis")} className={`nav-tab ${centerTab === "analysis" ? "active" : ""}`}>Paper Analysis</button>
        <button onClick={() => setCenterTab("summary")} className={`nav-tab ${centerTab === "summary" ? "active" : ""}`}>Summary</button>
      </div>
      <div className="content-area custom-scrollbar">
        {viewingRef ? (
          <>
            {/* 1. Original Paper (PDF 뷰어) */}
            {centerTab === "original" && (
               <div className="pdf-viewer-container">
                 {isPdfLoading ? (
                   <div className="loading-state"><Loader2 className="animate-spin" size={32}/></div>
                 ) : viewingRef.hasPdf && pdfUrl ? (
                   <iframe src={pdfUrl} className="pdf-frame" title="PDF Viewer" />
                 ) : (
                   <div className="doc-paper">
                     <div className="doc-header-meta">PDF Unavailable</div>
                     <h1 className="doc-headline">{viewingRef.title}</h1>
                     <div className="doc-body">{cleanAbstract}</div>
                   </div>
                 )}
               </div>
            )}

            {/* 2. Paper Analysis (분석 정보) */}
            {centerTab === "analysis" && (
              <div className="doc-paper animate-in">
                <span className="doc-header-meta">{viewingRef.type} Analysis</span>
                <h1 className="doc-headline">{viewingRef.title}</h1>
                <div className="section-title">Abstract</div>
                <div className="doc-body">{cleanAbstract}</div>
              </div>
            )}

            {/* 3. Summary (🔥 핵심: Uploaded File과 동일한 '종이' 디자인 적용) */}
            {centerTab === "summary" && (
              <div className="summary-view" style={{ padding: '0' }}>
                {isSummaryLoading ? (
                  <div className="loading-state" style={{ height: '300px' }}>
                    <Loader2 className="animate-spin" size={24} color="var(--primary)"/>
                    <p>Fetching Executive Summary...</p>
                  </div>
                ) : (
                  <div className="doc-paper animate-in" style={{ 
                    maxWidth: '850px', 
                    margin: '0 auto', 
                    boxShadow: '0 10px 25px rgba(0,0,0,0.05)',
                    border: '1px solid var(--border)' 
                  }}>
                    <div className="doc-header-meta" style={{ display:'flex', justifyContent:'space-between' }}>
                      <span>Executive Summary Report</span>
                      <span className="badge analyzed">AI GENERATED</span>
                    </div>
                    <div className="markdown-body" style={{ marginTop: '20px' }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {summaryContent || "분석된 요약 내용이 없습니다."}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="empty-state">문서를 선택해 주세요.</div>
        )}
      </div>
    </section>
  );
});

// ==================================================================================
// [Component 3] RightPanel (Chat Logic + Streaming)
// ==================================================================================
const ChatView = React.memo(({ messages, isWaiting, onConfirmAction, onCancelAction }) => {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isWaiting]);

  return (
    <div className="chat-area custom-scrollbar" ref={scrollRef}>
      {messages.map((m, i) => (
        <div key={i} className={`msg-row ${m.role}`}>
          {m.role === "ai" && <div className="ai-avatar"><Cpu size={18}/></div>}
          <div className={`msg-bubble ${m.role} ${m.isLog ? "log" : ""}`}>
            {m.isLog ? (
              <>
                <Loader2 className="animate-spin" size={14} />
                <span>{m.content}</span>
              </>
            ) : (
              m.role === "ai" ? (
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || ""}</ReactMarkdown>
                  {m.isProposal && (
                    <div className="proposal-actions">
                      <button className="proposal-btn confirm" onClick={() => onConfirmAction(m.agentType, m.analysisData)}>
                        <Play size={12}/> {m.agentType === "retrieval" ? "검색 실행" : "진행"}
                      </button>
                      <button className="proposal-btn cancel" onClick={onCancelAction}>
                        <X size={12}/> 취소
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                m.content
              )
            )}
          </div>
        </div>
      ))}
    </div>
  );
});

const ChatInput = React.memo(({ isWaiting, onSendMessage }) => {
  const [localInput, setLocalInput] = useState("");
  const textareaRef = useRef(null);

  const handleInputResize = (e) => {
    setLocalInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  const handleSendTrigger = () => {
    if(!localInput.trim()) return;
    onSendMessage(localInput);
    setLocalInput("");
    if(textareaRef.current) textareaRef.current.style.height = "auto";
  };

  return (
    <div className="input-area">
      <div className={`input-wrapper ${isWaiting ? 'disabled' : ''}`}>
        <textarea 
          ref={textareaRef}
          className="chat-textarea custom-scrollbar"
          placeholder={isWaiting ? "Processing..." : "Ask a research question..."}
          rows={1}
          value={localInput}
          onChange={handleInputResize}
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSendTrigger())}
          disabled={isWaiting}
        />
        <button className="send-icon-btn" onClick={handleSendTrigger} disabled={isWaiting}>
          <Send size={16}/>
        </button>
      </div>
    </div>
  );
});

const RightPanel = React.memo(({ 
  messages, isWaiting, 
  onSendMessage, onConfirmAction, onCancelAction 
}) => {
  return (
    <section className="right-panel">
      <div className="agent-header">
        <div className="agent-info">
          <Sparkles size={16} className="text-teal-500"/>
          <span className="agent-name">Bio-Insight Agent</span>
          <span className="agent-version">v2.4</span>
        </div>
        <div className="confidence-box">
          <span>Confidence: 82%</span>
          <div className="progress-bar"><div className="progress-val"></div></div>
        </div>
      </div>

      <ChatView 
        messages={messages}
        isWaiting={isWaiting}
        onConfirmAction={onConfirmAction}
        onCancelAction={onCancelAction}
      />
      <ChatInput 
        isWaiting={isWaiting}
        onSendMessage={onSendMessage}
      />
    </section>
  );
});


// ==================================================================================
// [Main] Dashboard
// ==================================================================================
const Dashboard = ({ onLogout }) => {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [references, setReferences] = useState([]); 
  
  // UI State
  const [leftTab, setLeftTab] = useState("session"); 
  const [centerTab, setCenterTab] = useState("analysis");
  const [viewingRef, setViewingRef] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const [summaryContent, setSummaryContent] = useState("");
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);

  // Modals & Inputs
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [showRetrievalModal, setShowRetrievalModal] = useState(false);
  const [newSessionTitle, setNewSessionTitle] = useState("");
  const [retrievalQuery, setRetrievalQuery] = useState("");
  const [isWaiting, setIsWaiting] = useState(false);
  
  // Shield Ref
  const pendingActionsRef = useRef({ toggling: new Set(), deleting: new Set() });

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    else delete api.defaults.headers.common["Authorization"];
  }, []);

  // --- Data Fetching Logic ---
  const fetchSessionData = useCallback(async (sessionId) => {
    if (!sessionId) return;
    try {
      const [msgRes, filesRes, candidatesRes, selectionsRes] = await Promise.all([
        api.get(`/sessions/${sessionId}/messages`),
        api.get(`/sessions/${sessionId}/files`),
        api.get(`/sessions/${sessionId}/research/candidates`),
        api.get(`/sessions/${sessionId}/selections`),
      ]);

      setMessages(Array.isArray(msgRes.data) ? msgRes.data : []);
      
      const selectionsData = Array.isArray(selectionsRes.data) ? selectionsRes.data : [];
      const filesData = Array.isArray(filesRes.data) ? filesRes.data : [];
      const candidatesData = Array.isArray(candidatesRes.data) ? candidatesRes.data : [];
      const selectedIds = new Set(selectionsData.map(s => s.item_id));
      
      const processItems = (items, type) => items.map(item => ({
        id: item.id,
        title: type === "file" ? item.original_name : item.title,
        type: type === "file" ? "FILE" : "PAPER",
        status: type === "file" ? item.status : "staged",
        isLocal: false,
        itemType: type,
        url: item.url,
        abstract: item.abstract || (type === "file" ? "파일 본문 내용은 아직 제공되지 않습니다." : "초록 정보 없음"),
        hasPdf: item.has_pdf,
        serverChecked: selectedIds.has(item.id) 
      }));

      const newFiles = processItems(filesData, "file");
      const newPapers = processItems(candidatesData, "paper");
      let mergedList = [...newFiles, ...newPapers];
      mergedList = mergedList.filter(item => !pendingActionsRef.current.deleting.has(item.id));

      setReferences(prev => {
        const prevMap = new Map(prev.map(r => [r.id, r]));
        return mergedList.map(newItem => {
          const isToggling = pendingActionsRef.current.toggling.has(newItem.id);
          const currentChecked = isToggling ? prevMap.get(newItem.id)?.checked : newItem.serverChecked;
          return { ...newItem, checked: currentChecked !== undefined ? currentChecked : newItem.serverChecked };
        });
      });
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => {
    const init = async () => {
      try {
        const res = await api.get("/sessions");
        setSessions(Array.isArray(res.data) ? res.data : []);
      } catch (e) { setSessions([]); }
    };
    init();
  }, []);

  const hasActiveTasks = useMemo(() => {
    return references.some(r => r.status === 'uploading' || r.status === 'processing');
  }, [references]);

  useEffect(() => {
    if (!currentSessionId || isWaiting) return;
    const intervalTime = hasActiveTasks ? 3000 : 20000;
    const intervalId = setInterval(() => { fetchSessionData(currentSessionId); }, intervalTime);
    return () => clearInterval(intervalId);
  }, [currentSessionId, fetchSessionData, hasActiveTasks, isWaiting]);

  // --- Handlers ---
  const handleSelectSession = useCallback((id) => {
    setCurrentSessionId(id);
    fetchSessionData(id);
    setViewingRef(null);
  }, [fetchSessionData]);

  const handleCreateSession = async () => {
    if (!newSessionTitle.trim()) return;
    try {
      const res = await api.post("/sessions", { title: newSessionTitle });
      const newSession = res.data;
      setSessions(prev => [newSession, ...prev]);
      handleSelectSession(newSession.id);
      setShowSessionModal(false);
      setNewSessionTitle("");
    } catch (e) { alert("세션 생성 실패"); }
  };

  const uploadFiles = useCallback(async (files) => {
    if (!currentSessionId || !files.length) return;
    const newRefs = Array.from(files).map((file, i) => ({
      id: `temp-${Date.now()}-${i}`, title: file.name, type: "FILE", status: "uploading",
      checked: true, isLocal: true, isLoading: true, itemType: "file"
    }));
    setReferences(prev => [...prev, ...newRefs]);

    const fd = new FormData();
    Array.from(files).forEach(f => fd.append("files", f));
    try {
      const res = await api.post(`/sessions/${currentSessionId}/files`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      const uploadedData = res.data || [];
      for (const item of uploadedData) {
        await api.post(`/sessions/${currentSessionId}/selections/toggle`, { item_type: "uploaded_file", item_id: item.file_id });
      }
      fetchSessionData(currentSessionId);
    } catch (e) { 
      alert("업로드 실패"); 
      setReferences(prev => prev.filter(r => !r.id.toString().startsWith("temp")));
    }
  }, [currentSessionId, fetchSessionData]);

  const toggleReference = useCallback(async (ref) => {
    if (!currentSessionId) return;
    setReferences(prev => prev.map(r => r.id === ref.id ? { ...r, checked: !r.checked } : r));
    pendingActionsRef.current.toggling.add(ref.id);
    try {
      const type = ref.itemType === "file" ? "uploaded_file" : "staged_paper";
      await api.post(`/sessions/${currentSessionId}/selections/toggle`, { item_type: type, item_id: ref.id });
    } catch (e) { 
      setReferences(prev => prev.map(r => r.id === ref.id ? { ...r, checked: !r.checked } : r));
    } finally {
      setTimeout(() => { pendingActionsRef.current.toggling.delete(ref.id); }, 1000); 
    }
  }, [currentSessionId]);

  const removeReference = useCallback(async (ref) => {
    if (!window.confirm("항목을 삭제하시겠습니까?")) return;
    setReferences(prev => prev.filter(r => r.id !== ref.id));
    if (viewingRef?.id === ref.id) setViewingRef(null);
    pendingActionsRef.current.deleting.add(ref.id);
    try {
      if(ref.itemType === "file") await api.delete(`/sessions/${currentSessionId}/files/${ref.id}`);
    } catch (e) { 
      alert("삭제 실패");
      pendingActionsRef.current.deleting.delete(ref.id);
      fetchSessionData(currentSessionId);
    }
  }, [currentSessionId, viewingRef, fetchSessionData]);

  // --- PDF & Summary Logic ---
  const loadPdfPreview = useCallback(async (ref) => {
    if (!ref || !currentSessionId) return;
    setIsPdfLoading(true);
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
    try {
      let res;
      if (ref.itemType === "paper" && ref.hasPdf) {
        res = await api.get(`/sessions/${currentSessionId}/papers/${ref.id}/download`, { responseType: "blob" });
      } else if (ref.itemType === "file") {
        res = await api.get(`/sessions/${currentSessionId}/files/${ref.id}/download`, { responseType: "blob" });
      } else {
        throw new Error("PDF source not available");
      }
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      setPdfUrl(url);
    } catch (e) { setPdfUrl(null); } finally { setIsPdfLoading(false); }
  }, [currentSessionId]); 

  const fetchSummary = useCallback(async (ref) => {
    if (!ref || !currentSessionId) return;
    setIsSummaryLoading(true);
    setSummaryContent(""); 
    try {
      let endpoint = "";
      if (ref.itemType === "file" || ref.itemType === "uploaded_file") {
         endpoint = `/sessions/${currentSessionId}/files/${ref.id}/summary`;
      } else if (ref.itemType === "paper" || ref.itemType === "staged_paper") {
         endpoint = `/sessions/${currentSessionId}/papers/${ref.id}/summary`;
      }
      if (endpoint) {
        const res = await api.get(endpoint);
        if (res.data.status === "empty" && ref.abstract) {
           setSummaryContent(`### [Abstract]\n\n${ref.abstract}\n\n*(자동 요약본이 없어 초록을 표시합니다)*`);
        } else {
           setSummaryContent(res.data.content);
        }
      } else {
        setSummaryContent("지원하지 않는 문서 타입입니다.");
      }
    } catch (e) { setSummaryContent("요약 정보를 불러오는 데 실패했습니다."); } finally { setIsSummaryLoading(false); }
  },[currentSessionId]);

  useEffect(() => {
    if (!viewingRef) return;
    if (centerTab === "original") loadPdfPreview(viewingRef);
    if (centerTab === "summary") fetchSummary(viewingRef);
  }, [centerTab, viewingRef, loadPdfPreview, fetchSummary]);

  useEffect(() => { return () => { if (pdfUrl) URL.revokeObjectURL(pdfUrl); }; }, [pdfUrl]);

  const handleDownload = async (ref) => {
    if (ref.itemType === "paper" && ref.hasPdf) {
      try {
        const res = await api.get(`/sessions/${currentSessionId}/papers/${ref.id}/download`, { responseType: "blob" });
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement("a"); link.href = url; link.setAttribute("download", `${ref.title.substring(0, 50)}.pdf`);
        document.body.appendChild(link); link.click(); link.remove();
      } catch (e) {
        alert("다운로드 중 오류가 발생했습니다. 원문 링크를 엽니다.");
        if (ref.url) window.open(ref.url, "_blank");
      }
    } else if (ref.itemType === "paper") {
      if (ref.url) window.open(ref.url, "_blank");
      else alert("링크 정보가 없습니다.");
    } else {
      try {
        const res = await api.get(`/sessions/${currentSessionId}/files/${ref.id}/download`, { responseType: "blob" });
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement("a"); link.href = url; link.setAttribute("download", ref.title);
        document.body.appendChild(link); link.click(); link.remove();
      } catch (e) { alert("다운로드 오류"); }
    }
  };

  // ----------------------------------------------------------------------------------
  // 🔥 [Core Feature] Chat & Research Logic
  // ----------------------------------------------------------------------------------

  // 1. 일반 채팅 (RAG)
  const handleSendMessage = useCallback(async (msgText) => {
    if (!msgText || !msgText.trim() || isWaiting || !currentSessionId) return;

    setMessages(prev => [...prev, { role: "user", content: msgText }]);
    setIsWaiting(true);

    try {
      const selectedRefs = references.filter(r => r.checked);
      const contextItems = selectedRefs.map(r => ({
        id: r.id,
        type: r.itemType === "file" ? "uploaded_file" : "staged_paper",
        status: r.status || "uploaded",
        title: r.title
      }));

      const body = { message: msgText, context_items: contextItems };
      // 일반 채팅은 /chat 엔드포인트 사용
      const res = await api.post(`/sessions/${currentSessionId}/chat`, body);
      setMessages(prev => [...prev, { role: "ai", content: res.data.reply }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: "ai", content: "오류 발생: " + e.message }]);
    } finally {
      setIsWaiting(false);
      fetchSessionData(currentSessionId);
    }
  }, [isWaiting, currentSessionId, references]);

  // 2. 스트림 응답 처리 (Research용)
  const processStreamResponse = async (response) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            
            const lines = buffer.split("\n");
            buffer = lines.pop(); // Incomplete line handling

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const data = JSON.parse(line);
                    
                    if (data.type === "log") {
                        // 로그는 마지막 메시지가 로그라면 업데이트, 아니면 추가
                        setMessages(prev => {
                            const last = prev[prev.length - 1];
                            if (last && last.isLog) {
                                return [...prev.slice(0, -1), { role: "ai", content: data.content, isLog: true }];
                            }
                            return [...prev, { role: "ai", content: data.content, isLog: true }];
                        });
                    } else if (data.type === "proposal") {
                        setMessages(prev => [...prev, {
                            role: "ai", 
                            content: data.content, 
                            isProposal: true, 
                            agentType: "retrieval", // Research Agent
                            analysisData: data.analysis
                        }]);
                    } else if (data.type === "result" || data.type === "message" || data.type === "error") {
                        setMessages(prev => [...prev, { role: "ai", content: data.content }]);
                        if (data.type === "result") {
                            // 결과가 나오면 목록 갱신을 위해 데이터 다시 불러오기
                            setTimeout(() => fetchSessionData(currentSessionId), 1000);
                        }
                    }
                } catch (e) { console.error("Stream Parse Error", e); }
            }
        }
    } catch (err) {
        console.error("Stream Read Error", err);
        setMessages(prev => [...prev, { role: "ai", content: "스트리밍 중 오류가 발생했습니다." }]);
    }
  };

  // 3. 논문 검색 (Research) - 🔥 수정됨
  const handleRetrieval = async () => {
    if (!retrievalQuery.trim()) return;
    const query = retrievalQuery;
    
    setShowRetrievalModal(false);
    setRetrievalQuery("");
    setLeftTab("library"); // 결과 확인을 위해 탭 이동

    // UI에 유저 메시지 표시
    setMessages(prev => [...prev, { role: "user", content: query }]);
    setIsWaiting(true);

    try {
        // 🔥 중요: fetch API를 사용하여 Stream 처리 (Axios 대신)
        const token = localStorage.getItem("token");
        const response = await fetch(`${api.defaults.baseURL}/sessions/${currentSessionId}/research`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ query: query, is_confirmed: false }) // 제안 모드
        });

        await processStreamResponse(response);
    } catch (e) {
        setMessages(prev => [...prev, { role: "ai", content: "검색 요청 실패: " + e.message }]);
    } finally {
        setIsWaiting(false);
    }
  };

  // 4. 검색 확정 (Proposal Confirm) - 🔥 수정됨
  const handleConfirmAction = useCallback(async (agentType, analysisData) => {
    if (agentType !== "retrieval") return; // 현재는 retrieval만 처리

    // UI 업데이트 (버튼 제거)
    setMessages(prev => {
        const msgs = [...prev];
        const last = msgs[msgs.length - 1];
        if (last && last.isProposal) msgs[msgs.length - 1] = { ...last, isProposal: false };
        return [...msgs, { role: "user", content: "진행해 주세요." }];
    });
    setIsWaiting(true);

    try {
        const token = localStorage.getItem("token");
        const response = await fetch(`${api.defaults.baseURL}/sessions/${currentSessionId}/research`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            // 확정 모드 (confirmed_intent 전달)
            body: JSON.stringify({ 
                query: "confirmed", 
                is_confirmed: true,
                confirmed_intent: analysisData 
            }) 
        });

        await processStreamResponse(response);
    } catch (e) {
        setMessages(prev => [...prev, { role: "ai", content: "실행 오류: " + e.message }]);
    } finally {
        setIsWaiting(false);
    }
  }, [currentSessionId]);

  const handleCancelAction = useCallback(() => {
      setMessages(prev => {
        const msgs = [...prev];
        const last = msgs[msgs.length - 1];
        if (last && last.isProposal) {
            msgs[msgs.length - 1] = { ...last, isProposal: false, content: last.content + "\n\n*(취소됨)*" };
        }
        return msgs;
    });
    setIsWaiting(false);
  }, []);

  return (
    <div className="dashboard-layout">
      <LeftPanel 
        sessions={sessions} currentSessionId={currentSessionId}
        leftTab={leftTab} setLeftTab={setLeftTab}
        references={references} viewingRef={viewingRef}
        onSelectSession={handleSelectSession}
        onCreateSessionTrigger={() => setShowSessionModal(true)}
        onToggleRef={toggleReference}
        onRemoveRef={removeReference}
        onSelectRef={setViewingRef}
        onUploadTrigger={uploadFiles}
        onRetrievalTrigger={() => setShowRetrievalModal(true)}
        onLogout={onLogout}
      />
      <CenterPanel 
        viewingRef={viewingRef} centerTab={centerTab} setCenterTab={setCenterTab}
        pdfUrl={pdfUrl} isPdfLoading={isPdfLoading}
        summaryContent={summaryContent} isSummaryLoading={isSummaryLoading}
        onDownload={handleDownload}
      />
      <RightPanel 
        messages={messages} isWaiting={isWaiting}
        onSendMessage={handleSendMessage}
        onConfirmAction={handleConfirmAction}
        onCancelAction={handleCancelAction}
      />

      {/* Modals */}
      {showSessionModal && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-head">
              <h3>New Session</h3>
              <button className="close-btn" onClick={() => setShowSessionModal(false)}><X size={20}/></button>
            </div>
            <div className="modal-content">
              <input className="modal-input" placeholder="Enter research topic..." value={newSessionTitle} onChange={e => setNewSessionTitle(e.target.value)} autoFocus />
            </div>
            <div className="modal-foot">
              <button className="modal-btn-confirm" onClick={handleCreateSession}>Create</button>
              <button className="modal-btn-cancel" onClick={() => setShowSessionModal(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {showRetrievalModal && (
        <div className="modal-overlay">
          <div className="modal-box">
            <div className="modal-head">
              <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
                <Zap size={18} color="var(--primary)"/>
                <h3>Retrieval Agent</h3>
              </div>
              <button className="close-btn" onClick={() => setShowRetrievalModal(false)}><X size={20}/></button>
            </div>
            <div className="modal-content">
              <p className="modal-desc">Search for papers on PubMed/bioRxiv.</p>
              <textarea className="modal-input" style={{height:'100px', resize:'none'}} placeholder="e.g. Recent studies on EGFR..." value={retrievalQuery} onChange={e => setRetrievalQuery(e.target.value)} />
            </div>
            <div className="modal-foot">
              <button className="modal-btn-confirm" onClick={handleRetrieval}>Start Search</button>
              <button className="modal-btn-cancel" onClick={() => setShowRetrievalModal(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;