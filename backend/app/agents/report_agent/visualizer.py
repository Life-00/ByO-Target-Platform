"""
Report Agent Visualizer
Generate interactive visualizations for research reports
"""

import logging
from typing import List, Dict, Any, Optional
from io import StringIO

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

try:
    import networkx as nx
    from pyvis.network import Network
except ImportError:
    nx = None
    Network = None

from app.agents.report_agent.schemas import ResearchReport, ResearchValidation, DocumentReference

logger = logging.getLogger(__name__)


class Visualizer:
    """시각화 엔진"""

    # ============================================================================
    # Evidence Network Graph (Pyvis)
    # ============================================================================

    @staticmethod
    async def create_evidence_network(
        report: ResearchReport,
        output_file: Optional[str] = None
    ) -> str:
        """
        증거 네트워크 그래프 생성 (Pyvis)
        
        노드: 연구주제 + 논문들
        엣지: 연관성 관계

        Args:
            report: ResearchReport 객체
            output_file: 저장할 HTML 파일 경로 (None이면 HTML 문자열 반환)

        Returns:
            HTML 문자열 또는 파일 경로
        """
        try:
            if Network is None:
                logger.warning("[Visualizer] Pyvis not installed, returning placeholder")
                return "<p>네트워크 그래프 생성 불가 (pyvis 미설치)</p>"

            logger.info(f"[Visualizer] Creating evidence network for: {report.research_topic}")

            # NetworkX 그래프 생성
            G = nx.Graph()

            # 중앙 노드: 연구주제
            research_node = "연구주제"
            G.add_node(research_node, title=report.research_topic, color="#FF6B6B", size=30)

            # 논문 노드 추가
            for idx, paper in enumerate(report.related_papers, 1):
                node_id = f"paper_{idx}"
                title = f"{paper.title}\n({paper.authors or 'Unknown'}, {paper.year or 'N/A'})"
                G.add_node(node_id, title=title, color="#4ECDC4", size=15)

                # 중앙 노드와 연결
                G.add_edge(research_node, node_id, weight=1)

            # 논문 간 연결 (유사성 기반)
            num_papers = len(report.related_papers)
            if num_papers > 1:
                # 인접한 논문 연결 (간단한 네트워크)
                for i in range(num_papers - 1):
                    for j in range(i + 1, min(i + 3, num_papers)):  # 각 논문당 최대 3개 연결
                        G.add_edge(f"paper_{i+1}", f"paper_{j+1}", weight=0.5)

            # Pyvis 네트워크 생성
            net = Network(
                height="750px",
                width="100%",
                directed=False,
                notebook=False,
                cdn_resources="remote"
            )

            net.from_nx(G)

            # 물리 시뮬레이션 설정
            net.toggle_physics(True)
            net.show_buttons(filter_=["physics"])

            # HTML 생성
            if output_file:
                net.show(output_file)
                logger.info(f"[Visualizer] Network graph saved to: {output_file}")
                return output_file
            else:
                # HTML 문자열로 반환
                html_string = net.generate_html()
                logger.info(f"[Visualizer] Network graph generated: {len(html_string)} chars")
                return html_string

        except Exception as e:
            logger.error(f"[Visualizer] Error creating evidence network: {str(e)}")
            raise

    # ============================================================================
    # Feasibility Score Chart (Plotly)
    # ============================================================================

    @staticmethod
    async def create_feasibility_chart(
        validation: ResearchValidation,
        breakdown: Optional[Dict[str, float]] = None
    ) -> str:
        """
        타당성 점수 시각화 (Gauge + Bar Chart)

        Args:
            validation: ResearchValidation 객체
            breakdown: 세부 항목별 점수 {"선행연구": 80, "방법론": 70, ...}

        Returns:
            Plotly HTML 문자열
        """
        try:
            logger.info(f"[Visualizer] Creating feasibility chart: {validation.feasibility_score}")

            # 기본 breakdown이 없으면 생성
            if not breakdown:
                breakdown = {
                    "선행연구": min(100, validation.feasibility_score + 10),
                    "방법론": validation.feasibility_score,
                    "실행가능성": max(0, validation.feasibility_score - 15),
                    "학술기여도": validation.feasibility_score,
                }

            # Subplot 생성: Gauge + Bar Chart
            fig = make_subplots(
                rows=1,
                cols=2,
                subplot_titles=("타당성 종합 점수", "세부 항목별 점수"),
                specs=[[{"type": "indicator"}, {"type": "bar"}]],
                column_widths=[0.4, 0.6]
            )

            # 1. Gauge Chart (왼쪽)
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=validation.feasibility_score,
                    domain={"x": [0, 1], "y": [0, 1]},
                    title={"text": "점수"},
                    delta={"reference": 50},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "darkblue"},
                        "steps": [
                            {"range": [0, 25], "color": "#FF6B6B"},      # 빨강 (낮음)
                            {"range": [25, 50], "color": "#FFA94D"},     # 주황 (보통)
                            {"range": [50, 75], "color": "#74C0FC"},     # 파랑 (높음)
                            {"range": [75, 100], "color": "#51CF66"},    # 초록 (매우높음)
                        ],
                        "threshold": {
                            "line": {"color": "red", "width": 4},
                            "thickness": 0.75,
                            "value": 90,
                        },
                    },
                ),
                row=1,
                col=1,
            )

            # 2. Bar Chart (오른쪽)
            items = list(breakdown.keys())
            scores = list(breakdown.values())
            colors = [
                "#51CF66" if s >= 75 else "#74C0FC" if s >= 50 else "#FFA94D" if s >= 25 else "#FF6B6B"
                for s in scores
            ]

            fig.add_trace(
                go.Bar(
                    x=items,
                    y=scores,
                    marker={"color": colors},
                    text=scores,
                    textposition="auto",
                    hovertemplate="<b>%{x}</b><br>점수: %{y:.1f}/100<extra></extra>",
                ),
                row=1,
                col=2,
            )

            # 레이아웃 설정
            fig.update_layout(
                title_text="연구 타당성 평가",
                title_font_size=18,
                showlegend=False,
                height=500,
                hovermode="x unified",
                template="plotly_white",
            )

            fig.update_yaxes(range=[0, 100], row=1, col=2)

            html_string = fig.to_html(include_plotlyjs="cdn")
            logger.info(f"[Visualizer] Feasibility chart created: {len(html_string)} chars")
            return html_string

        except Exception as e:
            logger.error(f"[Visualizer] Error creating feasibility chart: {str(e)}")
            raise

    # ============================================================================
    # Trend Chart (Plotly)
    # ============================================================================

    @staticmethod
    async def create_trend_chart(
        data: List[Dict[str, Any]],
        title: str = "연구 동향",
        x_axis: str = "year",
        y_axis: str = "count"
    ) -> str:
        """
        연구 동향 차트 생성 (Line + Area)

        Args:
            data: 시계열 데이터
                [
                    {"year": 2020, "count": 5},
                    {"year": 2021, "count": 12},
                    ...
                ]
            title: 차트 제목
            x_axis: X축 필드명
            y_axis: Y축 필드명

        Returns:
            Plotly HTML 문자열
        """
        try:
            if not data:
                logger.warning("[Visualizer] No trend data provided")
                return "<p>트렌드 데이터가 없습니다.</p>"

            logger.info(f"[Visualizer] Creating trend chart: {title}")

            # 데이터 정렬
            sorted_data = sorted(data, key=lambda x: x.get(x_axis, 0))

            x_values = [item.get(x_axis) for item in sorted_data]
            y_values = [item.get(y_axis) for item in sorted_data]

            # Plotly 그래프
            fig = go.Figure()

            # Area Chart
            fig.add_trace(
                go.Scatter(
                    x=x_values,
                    y=y_values,
                    mode="lines+markers",
                    name="추세",
                    fill="tozeroy",
                    line={"color": "#4ECDC4", "width": 3},
                    marker={"size": 8, "color": "#FF6B6B"},
                    hovertemplate="<b>%{x}</b><br>%{y}개<extra></extra>",
                )
            )

            # 평균선 추가
            avg_y = sum(y_values) / len(y_values)
            fig.add_hline(
                y=avg_y,
                line_dash="dash",
                line_color="gray",
                annotation_text=f"평균: {avg_y:.1f}",
                annotation_position="right",
            )

            # 레이아웃
            fig.update_layout(
                title=title,
                xaxis_title=x_axis.capitalize(),
                yaxis_title=y_axis.capitalize(),
                height=400,
                template="plotly_white",
                hovermode="x unified",
            )

            html_string = fig.to_html(include_plotlyjs="cdn")
            logger.info(f"[Visualizer] Trend chart created: {len(html_string)} chars")
            return html_string

        except Exception as e:
            logger.error(f"[Visualizer] Error creating trend chart: {str(e)}")
            raise

    # ============================================================================
    # Paper Distribution Chart
    # ============================================================================

    @staticmethod
    async def create_paper_distribution_chart(
        papers: List[DocumentReference]
    ) -> str:
        """
        논문 분포 차트 (연도별, 저자별)

        Args:
            papers: DocumentReference 리스트

        Returns:
            Plotly HTML 문자열
        """
        try:
            logger.info(f"[Visualizer] Creating paper distribution chart for {len(papers)} papers")

            if not papers:
                return "<p>논문 데이터가 없습니다.</p>"

            # 연도별 논문 수
            year_counts = {}
            for paper in papers:
                year = paper.year or "Unknown"
                year_counts[year] = year_counts.get(year, 0) + 1

            # Plotly 그래프
            fig = make_subplots(
                rows=1,
                cols=2,
                subplot_titles=("연도별 논문 수", "저자별 논문 수 (Top 10)"),
                specs=[[{"type": "bar"}, {"type": "bar"}]],
            )

            # 1. 연도별 (왼쪽)
            years = sorted([y for y in year_counts.keys() if y != "Unknown"])
            counts = [year_counts[y] for y in years]

            fig.add_trace(
                go.Bar(
                    x=years,
                    y=counts,
                    marker={"color": "#4ECDC4"},
                    name="논문 수",
                    hovertemplate="<b>%{x}</b><br>%{y}개<extra></extra>",
                ),
                row=1,
                col=1,
            )

            # 2. 저자별 (오른쪽)
            author_counts = {}
            for paper in papers:
                if paper.authors:
                    # 첫 번째 저자만 추출
                    first_author = paper.authors.split(",")[0].strip()
                    author_counts[first_author] = author_counts.get(first_author, 0) + 1

            if author_counts:
                top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                authors = [a[0] for a in top_authors]
                author_cnts = [a[1] for a in top_authors]

                fig.add_trace(
                    go.Bar(
                        x=authors,
                        y=author_cnts,
                        marker={"color": "#FF6B6B"},
                        name="논문 수",
                        hovertemplate="<b>%{x}</b><br>%{y}개<extra></extra>",
                    ),
                    row=1,
                    col=2,
                )

            # 레이아웃
            fig.update_layout(
                title_text="논문 분포 분석",
                showlegend=False,
                height=400,
                template="plotly_white",
            )

            fig.update_xaxes(title_text="연도", row=1, col=1)
            fig.update_xaxes(title_text="저자", row=1, col=2)
            fig.update_yaxes(title_text="논문 수", row=1, col=1)
            fig.update_yaxes(title_text="논문 수", row=1, col=2)

            html_string = fig.to_html(include_plotlyjs="cdn")
            logger.info(f"[Visualizer] Paper distribution chart created: {len(html_string)} chars")
            return html_string

        except Exception as e:
            logger.error(f"[Visualizer] Error creating paper distribution chart: {str(e)}")
            raise

    # ============================================================================
    # All Visualizations Bundle
    # ============================================================================

    @staticmethod
    async def create_all_visualizations(report: ResearchReport) -> Dict[str, str]:
        """
        모든 시각화 생성

        Args:
            report: ResearchReport 객체

        Returns:
            {
                "evidence_network": HTML,
                "feasibility_chart": HTML,
                "paper_distribution": HTML
            }
        """
        try:
            logger.info(f"[Visualizer] Creating all visualizations for: {report.title}")

            visualizations = {}

            # 1. 증거 네트워크
            visualizations["evidence_network"] = await Visualizer.create_evidence_network(report)

            # 2. 타당성 점수 차트
            breakdown = {
                "선행연구": min(100, report.validation.feasibility_score + 10),
                "방법론": report.validation.feasibility_score,
                "실행가능성": max(0, report.validation.feasibility_score - 15),
                "학술기여도": report.validation.feasibility_score,
            }
            visualizations["feasibility_chart"] = await Visualizer.create_feasibility_chart(
                report.validation,
                breakdown
            )

            # 3. 논문 분포
            visualizations["paper_distribution"] = await Visualizer.create_paper_distribution_chart(
                report.related_papers
            )

            logger.info(f"[Visualizer] All visualizations created successfully")
            return visualizations

        except Exception as e:
            logger.error(f"[Visualizer] Error creating all visualizations: {str(e)}")
            raise
