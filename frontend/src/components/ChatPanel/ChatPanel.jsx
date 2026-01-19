import React, { useRef, useEffect } from 'react';
import {
  Bot, User, Target, CheckSquare, ArrowLeft, Lightbulb, ChevronDown,
  Microscope, Globe, PenTool, Send
} from 'lucide-react';
import { AGENT_THEME } from '../../utils/constants';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import AgentSelector from './AgentSelector';
import GoalSetting from './GoalSetting';
import ContextList from './ContextList';
import chatService from '../../services/generalChatService';
import searchAgentService from '../../services/searchAgentService';
import analysisAgentService from '../../services/analysisAgentService';

const ChatPanel = ({
  sessionId,
  selectedPaper,
  checkedItems,
  allItems,
  onBack,
  messages,
  onAddMessage,
  isTyping,
  onSetIsTyping,
  agentMode,
  onSetAgentMode,
  analysisGoal,
  onSetAnalysisGoal,
  isGoalOpen,
  isContextListOpen,
  onToggleGoal,
  onToggleContextList,
  sessionTitle,
  sessionDescription,
}) => {
  const selectedItemsList = allItems.filter(item => checkedItems.has(item.id));
  const theme = AGENT_THEME[agentMode];

  const handleSend = async (input) => {
    if (!input.trim() || !sessionId) return;

    // Report 모드는 아직 미구현
    if (agentMode === 'report') {
      const warningMessage = {
        id: Date.now(),
        role: 'assistant',
        content: `${agentMode} 모드는 아직 구현되지 않았습니다. General, Search 또는 Analysis 모드를 사용해주세요.`,
        timestamp: new Date(),
        isError: true,
      };
      onAddMessage(warningMessage);
      return;
    }

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    onAddMessage(userMessage);
    onSetIsTyping(true);

    try {
      if (agentMode === 'general') {
        // General Chat Mode - LLM 대화
        const response = await chatService.sendMessage(
          sessionId,
          input,
          null, // system_prompt - 백엔드에서 생성하도록
          0.7, // temperature
          2048, // max_tokens
          selectedItemsList, // selected_documents
          analysisGoal || null // analysis_goal
        );

        const aiMessage = {
          id: response.message_id,
          role: 'assistant',
          content: response.content,
          timestamp: new Date(response.generated_at),
          usage: response.usage,
        };

        onAddMessage(aiMessage);
      } else if (agentMode === 'search') {
        // Search Mode - arXiv 논문 검색
        // LLM이 백엔드에서 요청 개수를 자동 추출함
        const response = await searchAgentService.search(
          sessionId,
          input,
          analysisGoal || null,
          selectedItemsList, // 이미 다운로드된 문서 (중복 방지)
          0.7 // min_relevance_score
        );

        // 검색 결과 메시지 생성
        let resultContent = `🔍 **검색 결과**\n\n`;
        resultContent += `- 검색어: ${response.search_query}\n`;
        resultContent += `- 발견: ${response.papers_found}개 \u2192 필터링: ${response.papers_filtered}개 \u2192 다운로드: ${response.papers_downloaded}개\n\n`;

        if (response.papers && response.papers.length > 0) {
          resultContent += `**다운로드된 논문:**\n\n`;
          response.papers.forEach((paper, idx) => {
            resultContent += `${idx + 1}. **${paper.title}**\n`;
            resultContent += `   - 저자: ${paper.authors.slice(0, 3).join(', ')}${paper.authors.length > 3 ? ' 외' : ''}\n`;
            resultContent += `   - 관련성: ${(paper.relevance_score * 100).toFixed(0)}%\n`;
            resultContent += `   - arXiv ID: ${paper.arxiv_id}\n\n`;
          });
        } else {
          resultContent += `검색 결과가 없습니다.`;
        }

        const aiMessage = {
          id: Date.now() + 1,
          role: 'assistant',
          content: resultContent,
          timestamp: new Date(),
        };

        onAddMessage(aiMessage);
      } else if (agentMode === 'analysis') {
        // Analysis Mode - RAG 기반 문서 분석
        if (selectedItemsList.length === 0) {
          const warningMessage = {
            id: Date.now() + 1,
            role: 'assistant',
            content: '분석할 문서를 먼저 선택해주세요.',
            timestamp: new Date(),
            isError: true,
          };
          onAddMessage(warningMessage);
          onSetIsTyping(false);
          return;
        }

        const response = await analysisAgentService.analyze(
          sessionId,
          input,
          analysisGoal || null,
          selectedItemsList,
          5, // top_k: 상위 5개 청크
          0.5 // min_relevance_score
        );

        // 분석 결과 메시지 생성
        let resultContent = `📊 **분석 결과**\n\n${response.answer}\n\n`;
        
        if (response.citations && response.citations.length > 0) {
          resultContent += `\n**근거:**\n\n`;
          response.citations.forEach((citation, idx) => {
            resultContent += `${idx + 1}. **[${citation.document_title}, p.${citation.page_number}]**\n`;
            resultContent += `   > "${citation.text_excerpt}"\n`;
            resultContent += `   (관련성: ${(citation.relevance_score * 100).toFixed(0)}%)\n\n`;
          });
        }

        resultContent += `\n*분석된 문서: ${response.documents_analyzed}개 | 검색된 청크: ${response.chunks_retrieved}개*`;

        const aiMessage = {
          id: Date.now() + 1,
          role: 'assistant',
          content: resultContent,
          timestamp: new Date(),
          usage: { total_tokens: response.tokens_used },
        };

        onAddMessage(aiMessage);
      }
    } catch (error) {
      console.error('[ChatPanel] Failed to send message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: `오류가 발생했습니다: ${error.message || '메시지 전송에 실패했습니다.'}`,
        timestamp: new Date(),
        isError: true,
      };
      onAddMessage(errorMessage);
    } finally {
      onSetIsTyping(false);
    }
  };

  return (
    <div className="w-96 border-l border-gray-200 bg-white flex flex-col h-full flex-shrink-0 relative">
      {/* Header */}
      <div className="p-4 border-b border-gray-100 flex justify-between items-center bg-white relative z-20">
        <div className="flex items-center gap-2">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${theme.bg} ${theme.color}`}>
            {agentMode === 'general' && <Bot size={18} />}
            {agentMode === 'search' && <Globe size={18} />}
            {agentMode === 'analysis' && <Microscope size={18} />}
            {agentMode === 'report' && <PenTool size={18} />}
          </div>
          <div>
            <h2 className={`font-bold text-sm ${theme.color}`}>{theme.name}</h2>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${agentMode === 'general' ? 'bg-teal-500' : 'bg-green-500'}`}></span>
                <span className={`text-xs ${agentMode === 'general' ? 'text-teal-600 font-semibold' : 'text-gray-500'}`}>
                  {agentMode === 'general' ? 'Active' : 'Online'}
                </span>
              </div>
              {agentMode === 'general' && checkedItems.size > 0 && (
                <span className="text-[10px] bg-teal-100 text-teal-700 px-1.5 py-0.5 rounded font-medium">
                  {checkedItems.size} docs active
                </span>
              )}
              {agentMode !== 'general' && checkedItems.size > 0 && (
                <span className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-medium">
                  {checkedItems.size} docs active
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={onToggleGoal}
            className={`p-2 rounded-full transition-colors ${isGoalOpen || analysisGoal ? 'bg-teal-100 text-teal-700' : 'hover:bg-gray-100 text-gray-400'}`}
            title="분석 목표 설정"
          >
            <Target size={18} />
          </button>

          <button
            onClick={onToggleContextList}
            className={`p-2 rounded-full transition-all relative ${isContextListOpen ? 'bg-teal-100 text-teal-700' : 'hover:bg-gray-100 text-gray-400'}`}
            title={isContextListOpen ? "선택 목록 닫기" : "선택된 항목 보기"}
          >
            <CheckSquare size={18} />
            {checkedItems.size > 0 && !isContextListOpen && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
            )}
          </button>

          <button
            onClick={onBack}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
            title="세션 선택창으로 이동"
          >
            <ArrowLeft size={18} />
          </button>
        </div>
      </div>

      {/* Goal Setting Area */}
      <GoalSetting
        isOpen={isGoalOpen}
        analysisGoal={analysisGoal}
        onAnalysisGoalChange={onSetAnalysisGoal}
        sessionId={sessionId}
      />

      {/* Context List Area */}
      <ContextList
        isOpen={isContextListOpen}
        selectedItems={selectedItemsList}
      />

      {/* Active Goal Indicator */}
      {!isGoalOpen && !isContextListOpen && analysisGoal.trim() && (
        <div
          onClick={onToggleGoal}
          className="bg-teal-50 px-4 py-2 border-b border-teal-100 flex items-center gap-2 cursor-pointer hover:bg-teal-100 transition-colors"
        >
          <Target size={12} className="text-teal-700" />
          <p className="text-xs text-teal-800 truncate flex-1 font-medium">
            목표: {analysisGoal}
          </p>
          <ChevronDown size={12} className="text-teal-400" />
        </div>
      )}

      {/* Messages */}
      <ChatMessages
        messages={messages}
        isTyping={isTyping}
        agentMode={agentMode}
      />

      {/* Input Area */}
      <div className="bg-white border-t border-gray-100 relative z-20">
        {/* Agent Selector */}
        <AgentSelector
          agentMode={agentMode}
          onSetAgentMode={onSetAgentMode}
        />

        {/* Chat Input */}
        <ChatInput
          theme={theme}
          onSend={handleSend}
          isDisabled={isTyping}
        />
      </div>
    </div>
  );
};

export default ChatPanel;
