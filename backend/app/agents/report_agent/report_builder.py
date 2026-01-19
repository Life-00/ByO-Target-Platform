"""
Report Builder
Generate research reports in Markdown and PDF formats
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
from typing import Optional

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

from app.agents.report_agent.schemas import ResearchReport

logger = logging.getLogger(__name__)


class ReportBuilder:
    """보고서 생성 도구"""

    # ============================================================================
    # Markdown Builder
    # ============================================================================

    @staticmethod
    async def build_markdown(report: ResearchReport) -> str:
        """
        Markdown 형식 보고서 생성

        Args:
            report: ResearchReport 객체

        Returns:
            Markdown 문자열
        """
        try:
            logger.info(f"[ReportBuilder] Building Markdown report: {report.title}")

            lines = []

            # Title
            lines.append(f"# {report.title}")
            lines.append("")

            # Metadata
            lines.append("## 📋 기본 정보")
            lines.append(f"- **연구주제**: {report.research_topic}")
            lines.append(f"- **생성일**: {datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"- **참고논문**: {len(report.related_papers)}개")
            lines.append("")

            # Validation Summary
            lines.append("## 🎯 타당성 평가")
            feasibility_emoji = "✅" if report.validation.is_feasible else "⚠️"
            lines.append(
                f"{feasibility_emoji} **평가 결과**: "
                f"{'연구 가능' if report.validation.is_feasible else '추가 검토 필요'}"
            )
            lines.append(f"- **타당성 점수**: {report.validation.feasibility_score:.1f}/100")
            lines.append(f"- **근거**: {report.validation.reasoning}")
            lines.append("")

            # Sections
            if report.sections:
                lines.append("## 📄 상세 분석")
                for section in report.sections:
                    lines.append(f"### {section.title}")
                    lines.append(section.content)
                    if section.citations:
                        lines.append("**참고 문헌:**")
                        for citation in section.citations:
                            lines.append(f"- {citation}")
                    lines.append("")

            # Evidence Summary
            if report.evidence_summary:
                lines.append("## 📚 증거 요약")
                lines.append(report.evidence_summary)
                lines.append("")

            # Recommendations
            if report.recommendations:
                lines.append("## 💡 권장사항")
                for idx, rec in enumerate(report.recommendations, 1):
                    lines.append(f"{idx}. {rec}")
                lines.append("")

            # Limitations
            if report.limitations:
                lines.append("## ⚠️ 한계 및 고려사항")
                for limitation in report.limitations:
                    lines.append(f"- {limitation}")
                lines.append("")

            # Related Papers
            if report.related_papers:
                lines.append("## 📖 참고 논문")
                for idx, paper in enumerate(report.related_papers, 1):
                    author_str = f" ({paper.authors})" if paper.authors else ""
                    year_str = f" [{paper.year}]" if paper.year else ""
                    lines.append(f"{idx}. {paper.title}{author_str}{year_str}")
                lines.append("")

            # Footer
            lines.append("---")
            lines.append(f"*보고서 생성: {datetime.now(ZoneInfo('Asia/Seoul')).isoformat()}*")

            markdown = "\n".join(lines)
            logger.info(f"[ReportBuilder] Markdown report built: {len(markdown)} chars")
            return markdown

        except Exception as e:
            logger.error(f"[ReportBuilder] Error building Markdown: {str(e)}")
            raise

    # ============================================================================
    # PDF Builder
    # ============================================================================

    @staticmethod
    async def build_pdf(report: ResearchReport) -> bytes:
        """
        PDF 형식 보고서 생성 (reportlab)

        Args:
            report: ResearchReport 객체

        Returns:
            PDF 바이너리
        """
        try:
            logger.info(f"[ReportBuilder] Building PDF report: {report.title}")

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
            )

            elements = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#1f4788"),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            )

            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#2e5c8a"),
                spaceAfter=12,
                spaceBefore=12,
                fontName="Helvetica-Bold",
            )

            body_style = ParagraphStyle(
                "CustomBody",
                parent=styles["Normal"],
                fontSize=11,
                alignment=TA_JUSTIFY,
                spaceAfter=12,
            )

            # Title
            elements.append(Paragraph(report.title, title_style))
            elements.append(Spacer(1, 0.3 * inch))

            # Metadata Table
            metadata_data = [
                ["항목", "내용"],
                ["연구주제", report.research_topic],
                ["생성일", datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")],
                ["참고논문", f"{len(report.related_papers)}개"],
            ]

            metadata_table = Table(metadata_data, colWidths=[1.5 * inch, 4 * inch])
            metadata_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e5c8a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
                ])
            )

            elements.append(metadata_table)
            elements.append(Spacer(1, 0.3 * inch))

            # Validation Section
            elements.append(Paragraph("🎯 타당성 평가", heading_style))

            feasibility_emoji = "✅" if report.validation.is_feasible else "⚠️"
            elements.append(
                Paragraph(
                    f"{feasibility_emoji} <b>평가 결과:</b> "
                    f"{'연구 가능' if report.validation.is_feasible else '추가 검토 필요'}",
                    body_style,
                )
            )
            elements.append(
                Paragraph(
                    f"<b>타당성 점수:</b> {report.validation.feasibility_score:.1f}/100",
                    body_style,
                )
            )
            elements.append(
                Paragraph(
                    f"<b>근거:</b> {report.validation.reasoning}",
                    body_style,
                )
            )
            elements.append(Spacer(1, 0.2 * inch))

            # Sections
            if report.sections:
                elements.append(Paragraph("📄 상세 분석", heading_style))
                for section in report.sections:
                    elements.append(Paragraph(section.title, heading_style))
                    # 긴 텍스트는 요약
                    content_preview = section.content[:500] + "..." if len(section.content) > 500 else section.content
                    elements.append(Paragraph(content_preview, body_style))

                    if section.citations:
                        elements.append(Paragraph("<b>참고 문헌:</b>", body_style))
                        for citation in section.citations[:3]:  # 최대 3개
                            elements.append(Paragraph(f"• {citation}", body_style))

                    elements.append(Spacer(1, 0.15 * inch))

            # Evidence Summary
            if report.evidence_summary:
                elements.append(PageBreak())
                elements.append(Paragraph("📚 증거 요약", heading_style))
                evidence_preview = (
                    report.evidence_summary[:800] + "..."
                    if len(report.evidence_summary) > 800
                    else report.evidence_summary
                )
                elements.append(Paragraph(evidence_preview, body_style))
                elements.append(Spacer(1, 0.2 * inch))

            # Recommendations
            if report.recommendations:
                elements.append(Paragraph("💡 권장사항", heading_style))
                for idx, rec in enumerate(report.recommendations[:5], 1):  # 최대 5개
                    elements.append(
                        Paragraph(f"<b>{idx}.</b> {rec}", body_style)
                    )
                elements.append(Spacer(1, 0.2 * inch))

            # Limitations
            if report.limitations:
                elements.append(Paragraph("⚠️ 한계 및 고려사항", heading_style))
                for limitation in report.limitations[:5]:  # 최대 5개
                    elements.append(
                        Paragraph(f"• {limitation}", body_style)
                    )
                elements.append(Spacer(1, 0.2 * inch))

            # Related Papers
            if report.related_papers:
                elements.append(PageBreak())
                elements.append(Paragraph("📖 참고 논문", heading_style))

                # 논문 테이블
                papers_data = [["#", "제목", "저자", "연도"]]
                for idx, paper in enumerate(report.related_papers[:10], 1):  # 최대 10개
                    title_short = paper.title[:40] + "..." if len(paper.title) > 40 else paper.title
                    author_short = paper.authors[:20] + "..." if paper.authors and len(paper.authors) > 20 else (paper.authors or "N/A")
                    year_str = str(paper.year) if paper.year else "N/A"
                    papers_data.append([str(idx), title_short, author_short, year_str])

                papers_table = Table(papers_data, colWidths=[0.4 * inch, 2.5 * inch, 1.5 * inch, 0.7 * inch])
                papers_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e5c8a")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                    ])
                )
                elements.append(papers_table)

            # Footer
            elements.append(Spacer(1, 0.3 * inch))
            footer_text = f"생성일: {datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')} | Report Agent"
            elements.append(
                Paragraph(
                    footer_text,
                    ParagraphStyle(
                        "Footer",
                        parent=styles["Normal"],
                        fontSize=9,
                        textColor=colors.grey,
                        alignment=TA_CENTER,
                    ),
                )
            )

            # Build PDF
            doc.build(elements)
            pdf_bytes = buffer.getvalue()
            buffer.close()

            logger.info(f"[ReportBuilder] PDF report built: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            logger.error(f"[ReportBuilder] Error building PDF: {str(e)}", exc_info=True)
            raise

    # ============================================================================
    # Helper Methods
    # ============================================================================

    @staticmethod
    async def build_all_formats(report: ResearchReport) -> dict:
        """
        모든 포맷으로 보고서 생성

        Args:
            report: ResearchReport 객체

        Returns:
            {
                "markdown": str,
                "pdf": bytes
            }
        """
        try:
            logger.info(f"[ReportBuilder] Building all formats for: {report.title}")

            markdown = await ReportBuilder.build_markdown(report)
            pdf = await ReportBuilder.build_pdf(report)

            return {
                "markdown": markdown,
                "pdf": pdf,
            }

        except Exception as e:
            logger.error(f"[ReportBuilder] Error building all formats: {str(e)}")
            raise

    @staticmethod
    def get_file_extension(format_type: str) -> str:
        """포맷에 해당하는 파일 확장자 반환"""
        extensions = {
            "markdown": "md",
            "pdf": "pdf",
        }
        return extensions.get(format_type, "txt")

    @staticmethod
    def get_mime_type(format_type: str) -> str:
        """포맷에 해당하는 MIME 타입 반환"""
        mime_types = {
            "markdown": "text/markdown",
            "pdf": "application/pdf",
        }
        return mime_types.get(format_type, "text/plain")
