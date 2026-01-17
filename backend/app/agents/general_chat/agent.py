"""
General Chat Agent
Main agent for general LLM conversations with optional document context
"""

import logging
from typing import Optional, List, Dict, Any

from app.agents.base_agent import BaseAgent
from app.agents.general_chat.schemas import ChatRequest, ChatResponse
from app.agents.general_chat.prompt import SYSTEM_PROMPT
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class GeneralChatAgent(BaseAgent):
    """
    General Chat Agent
    Provides standard LLM conversation with optional document context
    """

    def __init__(self):
        """Initialize general chat agent"""
        super().__init__()
        self.agent_type = "general_chat"
        self.system_prompt = SYSTEM_PROMPT
        self.llm_service = get_llm_service()

    async def execute(self, request: ChatRequest) -> ChatResponse:
        """
        Execute general chat

        Args:
            request: ChatRequest with user message and optional context

        Returns:
            ChatResponse with LLM response
        """
        try:
            logger.info(f"[GeneralChatAgent] Processing message: {request.content[:50]}...")

            # Build system prompt
            system_prompt = request.system_prompt or self.system_prompt

            # Build user prompt
            # If documents provided -> RAG mode
            # If no documents -> General conversation mode
            
            has_documents = request.selected_documents and len(request.selected_documents) > 0
            has_analysis_goal = bool(request.analysis_goal)
            
            if has_documents or has_analysis_goal:
                # RAG Mode: Structured prompt with context
                user_prompt_parts = []
                
                # 1. Analysis Goal (if provided)
                if has_analysis_goal:
                    user_prompt_parts.append(f"[분석 목표]: {request.analysis_goal}")
                
                # 2. Document Context (if provided)
                if has_documents:
                    doc_summaries = []
                    for idx, doc in enumerate(request.selected_documents, 1):
                        title = doc.get('title', 'Untitled')
                        summary = doc.get('summary', '')
                        if summary:
                            doc_summaries.append(f"[{idx}] {title}\n{summary}")
                        else:
                            doc_summaries.append(f"[{idx}] {title}\n(요약 없음)")
                    
                    if doc_summaries:
                        doc_context = "\n\n".join(doc_summaries)
                        user_prompt_parts.append(f"[참고 문서]:\n{doc_context}")
                        logger.info(f"[GeneralChatAgent] Using {len(request.selected_documents)} documents as context")
                
                # 3. User Question (PRIMARY)
                user_prompt_parts.append(f"[질문]: {request.content}")
                
                # Combine all parts
                user_prompt = "\n\n".join(user_prompt_parts)
            else:
                # General Conversation Mode: Just the content
                user_prompt = request.content
                logger.info(f"[GeneralChatAgent] General conversation mode")

            logger.info(f"[GeneralChatAgent] System prompt length: {len(system_prompt)}")
            logger.info(f"[GeneralChatAgent] User prompt length: {len(user_prompt)}")
            logger.info(f"[GeneralChatAgent] Has documents: {has_documents}")
            logger.info(f"[GeneralChatAgent] Has analysis goal: {has_analysis_goal}")

            # Call LLM via LLMService
            llm_response = await self.llm_service.generate(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

            logger.info(f"[GeneralChatAgent] Response received: {len(llm_response['content'])} chars")

            return ChatResponse(
                content=llm_response["content"],
                tokens_used=llm_response["usage"]["completion_tokens"],
                model="solar-1-mini-chat"
            )

        except Exception as e:
            logger.error(f"[GeneralChatAgent] Error: {str(e)}")
            raise

    async def chat(
        self,
        content: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        selected_documents: Optional[List[Dict[str, Any]]] = None,
        analysis_goal: Optional[str] = None,
    ) -> str:
        """
        Convenience method for simple chat calls

        Args:
            content: User message
            system_prompt: System prompt override
            temperature: LLM temperature
            max_tokens: Max tokens
            selected_documents: Optional context documents
            analysis_goal: Optional analysis goal

        Returns:
            Response string
        """
        request = ChatRequest(
            content=content,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            selected_documents=selected_documents,
            analysis_goal=analysis_goal,
        )
        response = await self.execute(request)
        return response.content
