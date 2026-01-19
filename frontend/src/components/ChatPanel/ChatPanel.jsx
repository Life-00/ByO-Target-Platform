import React, { useRef, useEffect } from "react";
import {
  Bot,
  User,
  Target,
  CheckSquare,
  ArrowLeft,
  Lightbulb,
  ChevronDown,
  Microscope,
  Globe,
  PenTool,
  Send,
} from "lucide-react";
import { AGENT_THEME } from "../../utils/constants";
import ChatMessages from "./ChatMessages";
import ChatInput from "./ChatInput";
import AgentSelector from "./AgentSelector";
import GoalSetting from "./GoalSetting";
import ContextList from "./ContextList";
import chatService from "../../services/generalChatService";
import searchAgentService from "../../services/searchAgentService";
import analysisAgentService from "../../services/analysisAgentService";
import reportAgentService from "../../services/reportAgentService";

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
  const selectedItemsList = allItems.filter((item) =>
    checkedItems.has(item.id),
  );
  const theme = AGENT_THEME[agentMode];

  const handleSend = async (input) => {
    if (!input.trim() || !sessionId) return;

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    onAddMessage(userMessage);
    onSetIsTyping(true);

    try {
      if (agentMode === "general") {
        // General Chat Mode - LLM 대화
        const response = await chatService.sendMessage(
          sessionId,
          input,
          null, // system_prompt - 백엔드에서 생성하도록
          0.7, // temperature
          2048, // max_tokens
          selectedItemsList, // selected_documents
          analysisGoal || null, // analysis_goal
        );

        const aiMessage = {
          id: response.message_id,
          role: "assistant",
          content: response.content,
          timestamp: new Date(response.generated_at),
          usage: response.usage,
        };

        onAddMessage(aiMessage);
      } else if (agentMode === "search") {
        // Search Mode - arXiv 논문 검색
        // LLM이 백엔드에서 요청 개수를 자동 추출함
        const response = await searchAgentService.search(
          sessionId,
          input,
          analysisGoal || null,
          selectedItemsList, // 이미 다운로드된 문서 (중복 방지)
          0.7, // min_relevance_score
        );

        // 검색 결과 메시지 생성
        let resultContent = `🔍 **검색 결과**\n\n`;
        resultContent += `- 검색어: ${response.search_query}\n`;
        resultContent += `- 발견: ${response.papers_found}개 \u2192 필터링: ${response.papers_filtered}개 \u2192 다운로드: ${response.papers_downloaded}개\n\n`;

        if (response.papers && response.papers.length > 0) {
          resultContent += `**다운로드된 논문:**\n\n`;
          response.papers.forEach((paper, idx) => {
            resultContent += `${idx + 1}. **${paper.title}**\n`;
            resultContent += `   - 저자: ${paper.authors.slice(0, 3).join(", ")}${paper.authors.length > 3 ? " 외" : ""}\n`;
            resultContent += `   - 관련성: ${(paper.relevance_score * 100).toFixed(0)}%\n`;
            resultContent += `   - arXiv ID: ${paper.arxiv_id}\n\n`;
          });
        } else {
          resultContent += `검색 결과가 없습니다.`;
        }

        const aiMessage = {
          id: Date.now() + 1,
          role: "assistant",
          content: resultContent,
          timestamp: new Date(),
        };

        onAddMessage(aiMessage);
      } else if (agentMode === "analysis") {
        // Analysis Mode - RAG 기반 문서 분석
        if (selectedItemsList.length === 0) {
          const warningMessage = {
            id: Date.now() + 1,
            role: "assistant",
            content: "분석할 문서를 먼저 선택해주세요.",
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
          0.5, // min_relevance_score
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
          role: "assistant",
          content: resultContent,
          timestamp: new Date(),
          usage: { total_tokens: response.tokens_used },
        };

        onAddMessage(aiMessage);
      } else if (agentMode === "report") {
        // Report Mode - 연구 타당성 보고서 생성
        if (selectedItemsList.length === 0) {
          const warningMessage = {
            id: Date.now() + 1,
            role: "assistant",
            content: "보고서를 생성할 문서를 먼저 선택해주세요.",
            timestamp: new Date(),
            isError: true,
          };
          onAddMessage(warningMessage);
          onSetIsTyping(false);
          return;
        }

        const response = await reportAgentService.generateReport(
          input, // research topic
          {
            researchDescription: null,
            analysisGoal: analysisGoal || null,
            documents: selectedItemsList,
            includeVisualizations: false, // 텍스트만 표시
            includeNetworkGraph: false,
            reportType: "comprehensive",
            temperature: 0.7,
            maxTokens: 4096,
            sessionId: sessionId,
          },
        );

        // 보고서 결과 메시지 생성
        let resultContent = `📝 **${response.report.title}**\n\n`;

        // 타당성 평가
        const validation = response.report.validation;
        const feasibilityEmoji = validation.is_feasible ? "✅" : "⚠️";
        resultContent += `${feasibilityEmoji} **타당성 평가**\n`;
        resultContent += `- 점수: ${validation.feasibility_score.toFixed(1)}/100\n`;
        resultContent += `- 결과: ${validation.is_feasible ? "연구 가능" : "추가 검토 필요"}\n`;
        resultContent += `- 근거: ${validation.reasoning}\n\n`;

        // 주요 섹션
        if (response.report.sections && response.report.sections.length > 0) {
          resultContent += `**주요 분석**\n\n`;
          response.report.sections.forEach((section, idx) => {
            resultContent += `**${idx + 1}. ${section.title}**\n${section.content}\n\n`;
          });
        }

        // 증거 요약
        if (response.report.evidence_summary) {
          resultContent += `**📚 증거 요약**\n${response.report.evidence_summary}\n\n`;
        }

        // 권장사항
        if (
          response.report.recommendations &&
          response.report.recommendations.length > 0
        ) {
          resultContent += `**💡 권장사항**\n`;
          response.report.recommendations.forEach((rec, idx) => {
            resultContent += `${idx + 1}. ${rec}\n`;
          });
          resultContent += `\n`;
        }

        // 한계점
        if (
          response.report.limitations &&
          response.report.limitations.length > 0
        ) {
          resultContent += `**⚠️ 한계점**\n`;
          response.report.limitations.forEach((limit, idx) => {
            resultContent += `${idx + 1}. ${limit}\n`;
          });
          resultContent += `\n`;
        }

        // 참고 논문
        if (
          response.report.related_papers &&
          response.report.related_papers.length > 0
        ) {
          resultContent += `**📄 참고 논문: ${response.report.related_papers.length}개**\n`;
        }

        resultContent += `\n*토큰 사용: ${response.tokens_used}*`;

        const aiMessage = {
          id: Date.now() + 1,
          role: "assistant",
          content: resultContent,
          timestamp: new Date(),
          usage: { total_tokens: response.tokens_used },
        };

        onAddMessage(aiMessage);

        // 생성된 보고서를 Library의 Reports 탭에 저장
        if (response.report) {
          const { useLibraryStore } = await import("../../stores/libraryStore");
          const addReport = useLibraryStore.getState().addReport;

          const reportItem = {
            id: Date.now() + 2,
            type: "report",
            title: response.report.title || input.substring(0, 50),
            authors: "AI Generated",
            year: new Date().getFullYear().toString(),
            conference: "Report Agent",
            abstract: validation.reasoning,
            content: resultContent,
            feasibilityScore: validation.feasibility_score,
            isFeasible: validation.is_feasible,
            createdAt: new Date().toISOString(),
            sections: response.report.sections,
            recommendations: response.report.recommendations,
            limitations: response.report.limitations,
            relatedPapers: response.report.related_papers,
          };

          addReport(reportItem);
          console.log("[ChatPanel] Report saved to library:", reportItem.title);
        }
      }
    } catch (error) {
      console.error("[ChatPanel] Failed to send message:", error);
      const errorMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: `오류가 발생했습니다: ${error.message || "메시지 전송에 실패했습니다."}`,
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
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center ${theme.bg} ${theme.color}`}
          >
            {agentMode === "general" && <Bot size={18} />}
            {agentMode === "search" && <Globe size={18} />}
            {agentMode === "analysis" && <Microscope size={18} />}
            {agentMode === "report" && <PenTool size={18} />}
          </div>
          <div>
            <h2 className={`font-bold text-sm ${theme.color}`}>{theme.name}</h2>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                <span
                  className={`w-2 h-2 rounded-full ${agentMode === "general" ? "bg-teal-500" : "bg-green-500"}`}
                ></span>
                <span
                  className={`text-xs ${agentMode === "general" ? "text-teal-600 font-semibold" : "text-gray-500"}`}
                >
                  {agentMode === "general" ? "Active" : "Online"}
                </span>
              </div>
              {agentMode === "general" && checkedItems.size > 0 && (
                <span className="text-[10px] bg-teal-100 text-teal-700 px-1.5 py-0.5 rounded font-medium">
                  {checkedItems.size} docs active
                </span>
              )}
              {agentMode !== "general" && checkedItems.size > 0 && (
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
            className={`p-2 rounded-full transition-colors ${isGoalOpen || analysisGoal ? "bg-teal-100 text-teal-700" : "hover:bg-gray-100 text-gray-400"}`}
            title="분석 목표 설정"
          >
            <Target size={18} />
          </button>

          <button
            onClick={onToggleContextList}
            className={`p-2 rounded-full transition-all relative ${isContextListOpen ? "bg-teal-100 text-teal-700" : "hover:bg-gray-100 text-gray-400"}`}
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
        <AgentSelector agentMode={agentMode} onSetAgentMode={onSetAgentMode} />

        {/* Chat Input */}
        <ChatInput theme={theme} onSend={handleSend} isDisabled={isTyping} />
      </div>
    </div>
  );
};

export default ChatPanel;
