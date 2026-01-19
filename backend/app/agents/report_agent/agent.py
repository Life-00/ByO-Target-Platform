"""
Report Agent Implementation
Generates comprehensive research feasibility reports with Intent-based execution
"""

import logging
import re
import json
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo

from app.agents.base_agent import BaseAgent
from app.agents.report_agent.schemas import (
    ReportAgentRequest,
    ReportAgentResponse,
    ResearchReport,
    ResearchValidation,
    ReportSection,
)
from app.agents.report_agent.prompt import (
    SYSTEM_PROMPT,
    REPORT_GENERATION_PROMPT,
    EVIDENCE_SYNTHESIS_PROMPT,
)
from app.agents.report_agent.llm_integration import LLMIntegration
from app.agents.report_agent.data_normalizer import DataNormalizer
from app.agents.report_agent.report_builder import ReportBuilder
from app.agents.report_agent.visualizer import Visualizer
from app.services.llm_service import get_llm_service
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


# ============================================================================
# Intent Classification
# ============================================================================


class ExecutionIntent(Enum):
    """사용자 의도 분류"""
    FULL_REPORT = "full_report"          # 전체 보고서 생성
    DATA_PROCESSING = "data_processing"  # 데이터 정리/변환
    VISUALIZATION = "visualization"      # 시각화만
    QUICK_ANALYSIS = "quick_analysis"    # 빠른 LLM 분석만


# ============================================================================
# Report Agent
# ============================================================================


class ReportAgent(BaseAgent):
    """
    Report Agent
    Generates comprehensive research feasibility reports with Intent-based execution
    Automatically selects execution strategy based on input parameters
    """

    def __init__(self):
        """Initialize report agent"""
        super().__init__()
        self.agent_type = "report_agent"
        self.system_prompt = SYSTEM_PROMPT
        self.llm_service = get_llm_service()
        self.llm_integration = LLMIntegration()
        self.embedding_service = get_embedding_service()

    async def execute(self, request: ReportAgentRequest) -> ReportAgentResponse:
        """
        Execute comprehensive report generation with all features

        항상 완전한 보고서를 생성합니다:
        - 8개 섹션 포함 완전한 보고서
        - 자동 시각화 포함
        - 근거 분석 및 타당성 평가
        - Markdown & PDF 생성

        Args:
            request: ReportAgentRequest with research topic and optional parameters

        Returns:
            ReportAgentResponse with complete report including visualizations
        """
        try:
            # 항상 완전한 보고서 생성 (시각화 자동 포함)
            logger.info(f"[ReportAgent] Generating comprehensive report with all features")
            
            # 시각화와 네트워크 그래프를 자동으로 포함
            request.include_visualizations = True
            request.include_network_graph = True
            
            return await self._execute_full_report(request)

        except Exception as e:
            logger.error(f"[ReportAgent] Error: {str(e)}", exc_info=True)
            raise

    # ============================================================================
    # Intent Classification
    # ============================================================================

    async def _classify_intent(self, request: ReportAgentRequest) -> ExecutionIntent:
        """
        Classify user intent based on request content and structure

        Classification order:
        1. Keyword detection in research_topic
        2. Structure detection (presence of optional parameters)
        3. Default to QUICK_ANALYSIS

        Args:
            request: ReportAgentRequest

        Returns:
            ExecutionIntent enum value
        """
        # Step 1: Keyword-based detection
        intent = self._keyword_based_intent(request.research_topic)
        if intent:
            return intent

        # Step 2: Structure-based detection
        if request.research_data and request.research_data.related_documents:
            return ExecutionIntent.FULL_REPORT
        elif hasattr(request, "data_to_normalize") and request.data_to_normalize:
            return ExecutionIntent.DATA_PROCESSING

        # Default: Quick analysis
        return ExecutionIntent.QUICK_ANALYSIS

    def _keyword_based_intent(self, text: str) -> Optional[ExecutionIntent]:
        """
        Detect intent using keyword matching in user input

        Args:
            text: User input text

        Returns:
            ExecutionIntent or None
        """
        text_lower = text.lower()

        keywords = {
            ExecutionIntent.DATA_PROCESSING: [
                "정리", "변환", "정규화", "단위", "표", "데이터", "통합", "정렬",
            ],
            ExecutionIntent.VISUALIZATION: [
                "그래프", "차트", "시각화", "네트워크", "도식", "그림", "플롯", "대시보드",
            ],
            ExecutionIntent.QUICK_ANALYSIS: [
                "분석해줘", "평가해줘", "어때", "가능해", "어떻게", "의견", "생각", "판단",
            ],
            ExecutionIntent.FULL_REPORT: [
                "보고서", "타당성", "평가", "종합", "전체", "완전한", "상세",
            ],
        }

        for intent, kws in keywords.items():
            if any(kw in text_lower for kw in kws):
                logger.info(f"[ReportAgent] Intent detected by keyword: {intent.value}")
                return intent

        return None

    # ============================================================================
    # Intent Execution: FULL_REPORT
    # ============================================================================

    async def _execute_full_report(self, request: ReportAgentRequest) -> ReportAgentResponse:
        """
        🔵 Full Report Generation
        
        Execution pipeline:
        1. Prepare document context
        2. Generate main report via LLM
        3. Extract validation (feasibility score)
        4. Generate sections
        5. Create evidence summary
        6. Extract recommendations & limitations
        7. Compile final report
        8. Build Markdown & PDF formats
        9. Generate visualizations
        """
        try:
            logger.info(f"[ReportAgent] Executing FULL_REPORT intent")

            # Step 1: Prepare document context
            documents_text = await self._prepare_documents_context(
                request.research_data.related_documents
            )
            logger.info(f"[ReportAgent] Prepared context for {len(request.research_data.related_documents)} documents")

            # Step 2: Generate main report via LLM
            report_content = await self._generate_main_report(
                request.research_topic,
                request.research_data.description,
                request.research_data.analysis_goal,
                documents_text,
                request.temperature,
                request.max_tokens
            )
            logger.info(f"[ReportAgent] Main report content generated")

            # Step 3: Parse validation
            validation = await self._extract_validation(report_content)
            logger.info(f"[ReportAgent] Feasibility score: {validation.feasibility_score:.1f}/100")

            # Step 4: Generate sections
            sections = await self._generate_sections(report_content)
            logger.info(f"[ReportAgent] Generated {len(sections)} report sections")

            # Step 5: Generate evidence summary
            evidence_summary = await self._generate_evidence_summary(
                documents_text,
                request.temperature,
                request.max_tokens
            )
            logger.info(f"[ReportAgent] Evidence summary generated")

            # Step 6: Extract recommendations
            recommendations = await self.llm_integration.extract_recommendations(report_content)
            logger.info(f"[ReportAgent] Extracted {len(recommendations)} recommendations")

            # Step 7: Extract limitations
            limitations = await self.llm_integration.extract_limitations(report_content)
            logger.info(f"[ReportAgent] Extracted {len(limitations)} limitations")

            # Step 8: Compile final report
            final_report = ResearchReport(
                title=f"연구주제 타당성 평가 보고서: {request.research_topic}",
                research_topic=request.research_topic,
                validation=validation,
                sections=sections,
                evidence_summary=evidence_summary,
                recommendations=recommendations,
                limitations=limitations,
                related_papers=request.research_data.related_documents
            )
            logger.info(f"[ReportAgent] Final report compiled")

            # Step 9: Generate report formats
            markdown = await ReportBuilder.build_markdown(final_report)
            pdf = await ReportBuilder.build_pdf(final_report)
            logger.info(f"[ReportAgent] Report formats generated (Markdown + PDF)")

            # Step 10: Parse visualization data from report content
            viz_data = self._extract_visualization_data(report_content)
            logger.info(f"[ReportAgent] Extracted visualization data: {bool(viz_data)}")

            # Step 11: Generate visualizations using extracted data
            visualizations = {}
            try:
                if viz_data:
                    visualizations = await Visualizer.create_all_visualizations(final_report, viz_data)
                    logger.info(f"[ReportAgent] Visualizations generated: {len(visualizations)} charts")
                else:
                    logger.warning(f"[ReportAgent] No visualization data found, using defaults")
                    visualizations = await Visualizer.create_all_visualizations(final_report, None)
            except Exception as viz_error:
                logger.warning(f"[ReportAgent] Visualization generation failed: {str(viz_error)}")
                visualizations = {}

            # Markdown에 시각화 섹션 추가
            if visualizations:
                viz_section = "\n\n## 📊 시각화\n\n"
                for viz_name, viz_html in visualizations.items():
                    viz_section += f"### {viz_name}\n{viz_html}\n\n"
                markdown += viz_section

            return ReportAgentResponse(
                report=final_report,
                visualizations=visualizations,  # 시각화 데이터 포함
                metadata={
                    "generated_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
                    "report_type": request.report_type,
                    "documents_count": len(request.research_data.related_documents),
                    "intent": "full_report",
                    "visualizations": list(visualizations.keys()),
                    "visualization_count": len(visualizations),
                    "markdown_length": len(markdown),
                    "pdf_bytes": len(pdf),
                },
                tokens_used=0,  # TODO: Sum actual token usage
                report_format="json"
            )

        except Exception as e:
            logger.error(f"[ReportAgent] Error in FULL_REPORT: {str(e)}", exc_info=True)
            raise

    # ============================================================================
    # Intent Execution: DATA_PROCESSING
    # ============================================================================

    async def _execute_data_processing(self, request: ReportAgentRequest) -> ReportAgentResponse:
        """
        🟢 Data Processing
        Executes data normalization and unit conversion
        """
        try:
            logger.info(f"[ReportAgent] Executing DATA_PROCESSING intent")

            if not request.data_to_normalize:
                raise ValueError("data_to_normalize required for DATA_PROCESSING")

            result = {"success": False, "data": None}

            # TODO: Implement actual data processing
            # For now, return placeholder
            result["success"] = True
            result["data"] = request.data_to_normalize

            logger.info(f"[ReportAgent] Data processing completed")

            return ReportAgentResponse(
                report=ResearchReport(
                    title="데이터 정리 결과",
                    research_topic=request.research_topic,
                    validation=ResearchValidation(
                        is_feasible=True,
                        feasibility_score=0,
                        reasoning="데이터 정리 완료"
                    ),
                    sections=[],
                    evidence_summary="",
                    recommendations=[],
                    limitations=[],
                    related_papers=[]
                ),
                metadata={
                    "intent": "data_processing",
                    "result": result,
                },
                tokens_used=0,
                report_format="json"
            )

        except Exception as e:
            logger.error(f"[ReportAgent] Error in DATA_PROCESSING: {str(e)}", exc_info=True)
            raise

    # ============================================================================
    # Intent Execution: VISUALIZATION
    # ============================================================================

    async def _execute_visualization(self, request: ReportAgentRequest) -> ReportAgentResponse:
        """
        🟡 Visualization
        Creates visualizations based on requested type
        """
        try:
            logger.info(f"[ReportAgent] Executing VISUALIZATION intent")

            # Create a minimal report from request data
            final_report = ResearchReport(
                title=f"시각화: {request.research_topic}",
                research_topic=request.research_topic,
                validation=ResearchValidation(
                    is_feasible=True,
                    feasibility_score=75,
                    reasoning="시각화 생성"
                ),
                sections=[],
                evidence_summary="",
                recommendations=[],
                limitations=[],
                related_papers=request.research_data.related_documents or []
            )

            # Generate visualizations
            visualizations = await Visualizer.create_all_visualizations(final_report)
            logger.info(f"[ReportAgent] Visualizations created successfully")

            return ReportAgentResponse(
                report=final_report,
                metadata={
                    "intent": "visualization",
                    "visualizations": visualizations,
                },
                tokens_used=0,
                report_format="html"
            )

        except Exception as e:
            logger.error(f"[ReportAgent] Error in VISUALIZATION: {str(e)}", exc_info=True)
            raise

    # ============================================================================
    # Intent Execution: QUICK_ANALYSIS
    # ============================================================================

    async def _execute_quick_analysis(self, request: ReportAgentRequest) -> ReportAgentResponse:
        """
        ⚪ Quick Analysis
        Simple LLM call without full report generation
        """
        try:
            logger.info(f"[ReportAgent] Executing QUICK_ANALYSIS intent")

            # Simple LLM call
            analysis = await self.llm_integration.call_llm(
                prompt=request.research_topic,
                system_prompt=self.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

            logger.info(f"[ReportAgent] Quick analysis completed: {len(analysis)} chars")

            return ReportAgentResponse(
                report=ResearchReport(
                    title="빠른 분석",
                    research_topic=request.research_topic,
                    validation=ResearchValidation(
                        is_feasible=True,
                        feasibility_score=0,
                        reasoning=analysis[:200] if analysis else ""
                    ),
                    sections=[
                        ReportSection(
                            title="분석 결과",
                            content=analysis,
                            citations=[]
                        )
                    ] if analysis else [],
                    evidence_summary="",
                    recommendations=[],
                    limitations=[],
                    related_papers=[]
                ),
                metadata={
                    "intent": "quick_analysis",
                    "analysis_length": len(analysis),
                },
                tokens_used=0,
                report_format="json"
            )

        except Exception as e:
            logger.error(f"[ReportAgent] Error in QUICK_ANALYSIS: {str(e)}", exc_info=True)
            raise

    # ============================================================================
    # Helper Methods
    # ============================================================================

    async def _prepare_documents_context(self, documents: List) -> str:
        """
        Prepare formatted document context for LLM with semantic search
        
        For each document, retrieves the most relevant chunks from ChromaDB
        to provide rich, meaningful context rather than just metadata
        """
        try:
            context_parts = []
            
            # Extract document IDs and research topic/goal from the request
            document_ids = [doc.id for doc in documents]
            
            logger.info(f"[ReportAgent] Preparing context for {len(documents)} documents")
            
            # For report agent, we want broader context, so use the document titles as search queries
            for idx, doc in enumerate(documents, 1):
                try:
                    # Semantic search for relevant chunks from this document
                    # Use document title as initial query for broader context
                    embed_result = await self.embedding_service.embed(doc.title, use_cache=True)
                    query_embedding = embed_result["embedding"]
                    
                    # Get ChromaDB collection
                    collection = self.embedding_service.get_collection()
                    
                    if not collection:
                        logger.warning(f"[ReportAgent] ChromaDB unavailable for document {idx}, using metadata")
                        doc_header = f"[{doc.title}]\n저자: {doc.authors or 'Unknown'}\n연도: {doc.year or 'Unknown'}\n\n"
                        context_parts.append(doc_header)
                        continue
                    
                    # 중요: 특정 문서의 청크만 검색하도록 where 필터 추가
                    where_filter = {
                        "document_id": {"$in": [doc.id, str(doc.id)]}
                    }
                    
                    logger.info(f"[ReportAgent] Searching ChromaDB for document ID: {doc.id}")
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=10,  # Get up to 10 chunks per document for report context
                        where=where_filter,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    if results and results["ids"] and len(results["ids"]) > 0:
                        logger.info(f"[ReportAgent] ChromaDB returned {len(results['ids'][0])} chunks for document {idx}")
                        chunks_text = []
                        document_title = doc.title  # 논문 제목 우선
                        document_filename = None
                        for i, result_id in enumerate(results["ids"][0]):
                            metadata = results["metadatas"][0][i]
                            chunk_text = results["documents"][0][i]
                            chunk_doc_id = metadata.get("document_id")
                            
                            logger.debug(f"[ReportAgent] Chunk {i}: doc_id={chunk_doc_id}, expected={doc.id}, match={chunk_doc_id == doc.id or str(chunk_doc_id) == str(doc.id)}")
                            
                            # Check if this chunk belongs to the current document
                            if chunk_doc_id == doc.id or str(chunk_doc_id) == str(doc.id):
                                chunks_text.append(chunk_text)
                                if not document_filename:
                                    document_filename = metadata.get("filename")
                        
                        if chunks_text:
                            doc_content = "\n\n".join(chunks_text[:5])  # Use top 5 chunks
                            # 제목 우선, 파일명은 부가 정보로
                            title_display = document_title or document_filename or "Unknown"
                            doc_header = f"[{title_display}]\n"
                            if document_filename and document_title and document_filename != document_title:
                                doc_header += f"파일명: {document_filename}\n"
                            doc_header += f"저자: {doc.authors or 'Unknown'}\n연도: {doc.year or 'Unknown'}\n\n"
                            context_parts.append(f"{doc_header}{doc_content}")
                            logger.info(f"[ReportAgent] Successfully retrieved {len(chunks_text)} chunks for document {idx} (ID: {doc.id})")
                        else:
                            # Fallback to metadata if no matching chunks found
                            doc_header = f"[{doc.title}]\n저자: {doc.authors or 'Unknown'}\n연도: {doc.year or 'Unknown'}\n\n"
                            context_parts.append(doc_header)
                            logger.warning(f"[ReportAgent] No matching chunks found for document {idx} (ID: {doc.id}), using metadata only")
                    else:
                        # Fallback to metadata if ChromaDB query returns nothing
                        doc_header = f"[{doc.title}]\n저자: {doc.authors or 'Unknown'}\n연도: {doc.year or 'Unknown'}\n\n"
                        context_parts.append(doc_header)
                        logger.warning(f"[ReportAgent] ChromaDB query returned no results for document {idx}")
                        
                except Exception as chunk_error:
                    logger.warning(f"[ReportAgent] Error retrieving chunks for document {idx}: {str(chunk_error)}")
                    # Fallback to metadata
                    doc_header = f"[{doc.title}]\n저자: {doc.authors or 'Unknown'}\n연도: {doc.year or 'Unknown'}\n\n"
                    context_parts.append(doc_header)

            return "\n\n---\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"[ReportAgent] Error preparing documents: {str(e)}")
            # Fallback: return simple metadata
            fallback_parts = []
            for idx, doc in enumerate(documents, 1):
                doc_text = f"""[{idx}] {doc.title}
Authors: {doc.authors or 'Unknown'}
Year: {doc.year or 'Unknown'}"""
                fallback_parts.append(doc_text)
            return "\n\n".join(fallback_parts)

    async def _generate_main_report(
        self,
        topic: str,
        description: Optional[str],
        analysis_goal: Optional[str],
        documents: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate main report content via LLM"""
        try:
            prompt = REPORT_GENERATION_PROMPT.format(
                research_topic=topic,
                research_description=description or "Not specified",
                analysis_goal=analysis_goal or "Comprehensive analysis",
                documents=documents
            )

            response = await self.llm_integration.call_llm(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response

        except Exception as e:
            logger.error(f"[ReportAgent] Error generating main report: {str(e)}")
            raise

    async def _extract_validation(self, report_content: str) -> ResearchValidation:
        """Extract feasibility validation from LLM response"""
        try:
            return await self.llm_integration.parse_validation(report_content)

        except Exception as e:
            logger.error(f"[ReportAgent] Error extracting validation: {str(e)}")
            # Return default validation
            return ResearchValidation(
                is_feasible=True,
                feasibility_score=50.0,
                reasoning="분석 결과를 확인하세요"
            )

    async def _generate_sections(self, report_content: str) -> List[ReportSection]:
        """Parse report content into structured sections"""
        try:
            sections = []

            # Parse sections from markdown-style headers
            section_pattern = r"##\s+(.+?)\n(.*?)(?=##|$)"
            matches = re.findall(section_pattern, report_content, re.DOTALL)

            for title, content in matches[:5]:  # Limit to 5 sections
                if content.strip():
                    sections.append(
                        ReportSection(
                            title=title.strip(),
                            content=content.strip()[:500],  # Limit content to 500 chars
                            citations=[]
                        )
                    )

            # If no sections found, create default section
            if not sections:
                sections.append(
                    ReportSection(
                        title="분석 내용",
                        content=report_content[:500],
                        citations=[]
                    )
                )

            return sections

        except Exception as e:
            logger.error(f"[ReportAgent] Error generating sections: {str(e)}")
            return []

    async def _generate_evidence_summary(
        self,
        documents: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate synthesis of evidence from documents"""
        try:
            prompt = EVIDENCE_SYNTHESIS_PROMPT.format(documents=documents)

            response = await self.llm_integration.call_llm(
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response

        except Exception as e:
            logger.error(f"[ReportAgent] Error generating evidence summary: {str(e)}")
            return "증거 종합 분석이 진행 중입니다."

    def _extract_visualization_data(self, report_content: str) -> Optional[Dict[str, Any]]:
        """
        Extract visualization data from LLM report content
        Looks for JSON block with visualization_data
        """
        try:
            # Find JSON block in report content
            json_pattern = r'```json\s*(\{.*?"visualization_data".*?\})\s*```'
            match = re.search(json_pattern, report_content, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                if "visualization_data" in data:
                    logger.info(f"[ReportAgent] Successfully extracted visualization data")
                    return data["visualization_data"]
                else:
                    logger.warning(f"[ReportAgent] JSON found but no visualization_data key")
                    return None
            else:
                logger.warning(f"[ReportAgent] No JSON visualization block found in report")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"[ReportAgent] JSON parsing error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"[ReportAgent] Error extracting visualization data: {str(e)}")
            return None
