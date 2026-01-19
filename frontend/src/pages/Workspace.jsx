import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLibraryStore } from '../stores/libraryStore';
import { useChatStore } from '../stores/chatStore';
import { useUIStore } from '../stores/uiStore';
import LibraryPanel from '../components/LibraryPanel/LibraryPanel';
import PDFViewerPanel from '../components/PDFViewerPanel/PDFViewerPanel';
import ChatPanel from '../components/ChatPanel/ChatPanel';
import sessionService from '../services/sessionService';
import generalChatService from '../services/generalChatService';
import documentService from '../services/documentService';
import embeddingAgentService from '../services/embeddingAgentService';
import authService from '../services/authService';

const Workspace = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Subscribe to stores
  const libraryState = useLibraryStore();
  const chatState = useChatStore();
  const uiState = useUIStore();

  // 세션 정보, 채팅 히스토리 및 문서 로드
  useEffect(() => {
    const loadSessionData = async () => {
      if (!sessionId) {
        navigate('/session');
        return;
      }

      setIsLoading(true);
      try {
        // 세션 정보 로드
        const sessionData = await sessionService.getSession(sessionId);
        console.log('[Workspace] Session loaded:', sessionData);
        setSession(sessionData);

        // 저장된 분석 목표가 있으면 설정
        if (sessionData.analysis_goal) {
          chatState.setAnalysisGoal(sessionData.analysis_goal);
          console.log('[Workspace] Loaded analysis goal:', sessionData.analysis_goal);
        }

        // 채팅 히스토리 로드 (실패해도 계속 진행)
        try {
          const historyData = await generalChatService.getHistory(sessionId);
          console.log('[Workspace] Chat history loaded:', historyData);
          
          // 채팅 메시지를 store에 설정
          if (historyData.messages && historyData.messages.length > 0) {
            chatState.setMessages(historyData.messages.map(msg => ({
              id: msg.id,
              role: msg.role,
              content: msg.content,
              timestamp: new Date(msg.created_at),
            })));
          } else {
            chatState.setMessages([]);
          }
        } catch (historyErr) {
          console.warn('[Workspace] Failed to load chat history, continuing anyway:', historyErr);
          // 히스토리 로드 실패해도 빈 배열로 시작
          chatState.setMessages([]);
        }

        // 세션의 문서들 로드 (실패해도 계속 진행)
        try {
          const docsData = await documentService.getDocuments(100, 0, sessionId);
          console.log('[Workspace] Session documents loaded:', docsData);
          
          // 문서를 paper로 변환하여 store에 설정
          if (docsData.documents && Array.isArray(docsData.documents)) {
            const papers = await Promise.all(
              docsData.documents.map(async (doc) => {
                let pdfUrl = '';
                try {
                  pdfUrl = await documentService.getDownloadUrl(doc.id);
                } catch (error) {
                  console.error(`Failed to load PDF URL for document ${doc.id}:`, error);
                }

                return {
                  id: doc.id,
                  type: 'paper',
                  title: doc.title || 'Untitled Document',
                  authors: 'User Uploaded',
                  year: new Date(doc.created_at).getFullYear().toString(),
                  conference: 'Custom',
                  abstract: doc.description || 'User uploaded document',
                  content: 'Content extracted and embedded in ChromaDB',
                  summary: doc.summary || '',
                  pdfUrl: pdfUrl,
                  metadata: {
                    uploadedAt: doc.created_at,
                    fileSize: doc.file_size,
                    fileName: doc.file_name,
                  },
                };
              })
            );
            
            // Store에 논문들을 설정
            libraryState.setPapers(papers);
          }
        } catch (docsErr) {
          console.warn('[Workspace] Failed to load documents, continuing anyway:', docsErr);
          // 문서 로드 실패해도 계속
        }

      } catch (err) {
        console.error('[Workspace] Failed to load session data:', err);
        setError(err.message);
        // 세션이 없으면 세션 목록으로 이동
        if (err.status === 404) {
          setTimeout(() => navigate('/session'), 2000);
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadSessionData();
  }, [sessionId, navigate]);

  const allItems = [...libraryState.papers, ...libraryState.reports];

  // 로딩 또는 에러 상태 표시
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto mb-4"></div>
          <p className="text-gray-600">세션 로딩 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="text-red-600 text-xl mb-4">⚠️</div>
          <p className="text-red-600 mb-2">{error}</p>
          <button
            onClick={() => navigate('/session')}
            className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700"
          >
            세션 목록으로
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden font-sans text-gray-900">
      {/* Library Panel - Left */}
      <LibraryPanel 
        papers={libraryState.papers}
        reports={libraryState.reports}
        selectedPaper={libraryState.selectedPaper}
        onSelectPaper={libraryState.setSelectedPaper}
        isOpen={uiState.isLibraryOpen}
        toggleLibrary={uiState.toggleLibrary}
        checkedItems={libraryState.checkedItems}
        onToggleCheck={libraryState.toggleCheck}
        onDeleteItem={async (id, type) => {
          try {
            // 서버에서 문서 삭제
            await documentService.deleteDocument(id);
            
            // 로컬 상태에서 삭제
            if (type === 'paper') {
              libraryState.deletePaper(id);
            } else {
              libraryState.deleteReport(id);
            }
          } catch (error) {
            console.error('Failed to delete document:', error);
            alert('문서 삭제에 실패했습니다.');
          }
        }}
        onBatchSelect={libraryState.batchSelect}
        onBatchDelete={libraryState.batchDelete}
        onFileUpload={async (file) => {
          // 업로드 진행 상태 표시
          const uploadingPaper = {
            id: Date.now(),
            type: 'paper',
            title: file.name.replace('.pdf', ''),
            authors: "Uploading...",
            year: new Date().getFullYear().toString(),
            conference: "Custom",
            abstract: "파일 업로드 및 분석 중...",
            content: "Content being extracted...",
            pdfUrl: URL.createObjectURL(file),
            isUploading: true,
          };
          
          // 임시 paper를 화면에 표시
          libraryState.addPaper(uploadingPaper);

          try {
            // Step 1: 문서 업로드 (storage에 저장)
            console.log('[Workspace] Uploading document to storage...');
            const uploadResult = await documentService.uploadDocument(
              file,
              file.name.replace('.pdf', ''),
              'User uploaded PDF document',
              sessionId
            );
            console.log('[Workspace] Document uploaded:', uploadResult);

            const documentId = uploadResult.id || uploadResult.document_id;
            
            // Step 2: EmbeddingAgent 자동 실행 (chromadb까지 적재)
            console.log('[Workspace] Triggering EmbeddingAgent for document:', documentId);
            const analysisResult = await embeddingAgentService.analyzeDocument(
              documentId,
              sessionId
            );
            console.log('[Workspace] Document analysis completed:', analysisResult);

            // Step 3: 완료된 paper 정보로 업데이트
            const completedPaper = {
              id: documentId,
              type: 'paper',
              title: file.name.replace('.pdf', ''),
              authors: "User Uploaded",
              year: new Date().getFullYear().toString(),
              conference: "Custom",
              abstract: analysisResult.status || "Successfully processed and embedded",
              content: "Content extracted and embedded in ChromaDB",
              pdfUrl: URL.createObjectURL(file),
              isUploading: false,
              metadata: {
                chunks: analysisResult.chunk_count,
                embeddings: analysisResult.embedding_count,
                uploadedAt: new Date().toISOString(),
              },
            };

            // 임시 paper를 완료된 paper로 교체
            libraryState.deletePaper(uploadingPaper.id);
            libraryState.addPaper(completedPaper);

            console.log('[Workspace] File upload workflow completed successfully');
          } catch (error) {
            console.error('[Workspace] File upload workflow failed:', error);
            
            // 에러 상태로 업데이트
            const errorPaper = {
              ...uploadingPaper,
              isUploading: false,
              authors: "Upload Failed",
              abstract: error.message || "문서 업로드 또는 분석 실패",
            };
            
            libraryState.deletePaper(uploadingPaper.id);
            libraryState.addPaper(errorPaper);

            // 사용자에게 알림
            alert(`파일 업로드 실패: ${error.message || '알 수 없는 오류'}`);
          }
        }}
        onLogout={async () => {
          try {
            await authService.logoutAsync();
            window.location.href = '/';
          } catch (error) {
            console.error('Logout failed:', error);
            // 실패해도 로그인 페이지로 이동
            window.location.href = '/';
          }
        }}
        onSettings={() => alert('설정 창을 엽니다.')}
        activeTab={libraryState.activeTab}
        onTabChange={libraryState.setActiveTab}
      />

      {/* PDF Viewer Panel - Center */}
      <PDFViewerPanel
        paper={libraryState.selectedPaper}
        toggleLibrary={uiState.toggleLibrary}
        isLibraryOpen={uiState.isLibraryOpen}
        viewMode={uiState.viewMode}
        onViewModeChange={uiState.setViewMode}
        zoomLevel={uiState.zoomLevel}
        onZoomIn={uiState.zoomIn}
        onZoomOut={uiState.zoomOut}
      />

      {/* Chat Panel - Right */}
      <ChatPanel
        sessionId={sessionId}
        selectedPaper={libraryState.selectedPaper}
        checkedItems={libraryState.checkedItems}
        allItems={allItems}
        onBack={() => navigate('/session')}
        messages={chatState.messages}
        onAddMessage={chatState.addMessage}
        isTyping={chatState.isTyping}
        onSetIsTyping={chatState.setIsTyping}
        agentMode={chatState.agentMode}
        onSetAgentMode={chatState.setAgentMode}
        analysisGoal={chatState.analysisGoal}
        onSetAnalysisGoal={chatState.setAnalysisGoal}
        isGoalOpen={uiState.isGoalOpen}
        isContextListOpen={uiState.isContextListOpen}
        onToggleGoal={uiState.toggleGoal}
        onToggleContextList={uiState.toggleContextList}
        sessionTitle={session?.title}
        sessionDescription={session?.description}
      />
    </div>
  );
};

export default Workspace;
