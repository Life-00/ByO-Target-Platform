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

            # 레이아웃 설정 (논문 figure 스타일)
            fig.update_layout(
                title={
                    "text": "<b>Figure 2. 연구 타당성 평가</b>",
                    "font": {"size": 20, "family": "Arial, sans-serif", "color": "#2c3e50"},
                    "x": 0.5,
                    "xanchor": "center"
                },
                showlegend=False,
                height=500,
                hovermode="x unified",
                template="plotly_white",
                margin=dict(l=80, r=80, t=120, b=80),
                font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
            )

            fig.update_yaxes(
                range=[0, 100],
                title_font=dict(size=14),
                tickfont=dict(size=12),
                row=1, col=2
            )
            fig.update_xaxes(
                title_font=dict(size=14),
                tickfont=dict(size=11),
                tickangle=-15,
                row=1, col=2
            )

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

            # 연도별 논문 수 (Unknown 제외, AI Generated 문서는 연도 null)
            year_counts = {}
            for paper in papers:
                # AI Generated 보고서는 연도를 포함하지 않음
                if paper.year and paper.year != "Unknown" and isinstance(paper.year, int):
                    year_counts[paper.year] = year_counts.get(paper.year, 0) + 1

            # Plotly 그래프
            fig = make_subplots(
                rows=1,
                cols=2,
                subplot_titles=("연도별 논문 분포", "주요 저자 분포 (Top 10)"),
                horizontal_spacing=0.15,
                specs=[[{"type": "bar"}, {"type": "bar"}]],
            )

            # 1. 연도별 (왼쪽)
            if year_counts:
                years = sorted(year_counts.keys())
                counts = [year_counts[y] for y in years]

                fig.add_trace(
                    go.Bar(
                        x=years,
                        y=counts,
                        marker={"color": "#4ECDC4", "line": {"width": 1, "color": "#3AAFA9"}},
                        name="논문 수",
                        text=counts,
                        textposition="outside",
                        textfont={"size": 14, "family": "Arial, sans-serif"},
                        hovertemplate="<b>연도: %{x}</b><br>논문 수: %{y}개<extra></extra>",
                    ),
                    row=1,
                    col=1,
                )
            else:
                # 데이터 없음 표시
                fig.add_annotation(
                    text="연도 정보가 없습니다",
                    xref="x", yref="y",
                    x=0.5, y=0.5,
                    showarrow=False,
                    row=1, col=1
                )

            # 2. 저자별 (오른쪽)
            author_counts = {}
            for paper in papers:
                if paper.authors and paper.authors != "AI Generated":
                    # 첫 번째 저자만 추출
                    first_author = paper.authors.split(",")[0].strip()
                    if first_author and first_author != "Unknown":
                        author_counts[first_author] = author_counts.get(first_author, 0) + 1

            if author_counts:
                top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                authors = [a[0][:20] + "..." if len(a[0]) > 20 else a[0] for a in top_authors]  # 이름 길이 제한
                author_cnts = [a[1] for a in top_authors]

                fig.add_trace(
                    go.Bar(
                        x=authors,
                        y=author_cnts,
                        marker={"color": "#FF6B6B", "line": {"width": 1, "color": "#E85D5D"}},
                        name="논문 수",
                        text=author_cnts,
                        textposition="outside",
                        textfont={"size": 14, "family": "Arial, sans-serif"},
                        hovertemplate="<b>%{x}</b><br>논문 수: %{y}개<extra></extra>",
                    ),
                    row=1,
                    col=2,
                )
            else:
                fig.add_annotation(
                    text="저자 정보가 없습니다",
                    xref="x2", yref="y2",
                    x=0.5, y=0.5,
                    showarrow=False,
                    row=1, col=2
                )

            # 레이아웃 (논문 figure 스타일)
            fig.update_layout(
                title={
                    "text": "<b>Figure 3. 논문 분포 분석</b>",
                    "font": {"size": 20, "family": "Arial, sans-serif", "color": "#2c3e50"},
                    "x": 0.5,
                    "xanchor": "center"
                },
                showlegend=False,
                height=500,
                template="plotly_white",
                margin=dict(l=80, r=80, t=120, b=80),
                font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
            )

            fig.update_xaxes(
                title_text="<b>연도</b>",
                title_font=dict(size=14),
                tickfont=dict(size=12),
                row=1, col=1
            )
            fig.update_xaxes(
                title_text="<b>저자</b>",
                title_font=dict(size=14),
                tickfont=dict(size=10),
                tickangle=-45,
                row=1, col=2
            )
            fig.update_yaxes(
                title_text="<b>논문 수</b>",
                title_font=dict(size=14),
                tickfont=dict(size=12),
                row=1, col=1
            )
            fig.update_yaxes(
                title_text="<b>논문 수</b>",
                title_font=dict(size=14),
                tickfont=dict(size=12),
                row=1, col=2
            )

            html_string = fig.to_html(include_plotlyjs="cdn")
            logger.info(f"[Visualizer] Paper distribution chart created: {len(html_string)} chars")
            return html_string

        except Exception as e:
            logger.error(f"[Visualizer] Error creating paper distribution chart: {str(e)}")
            raise

    # ============================================================================
    # Comparison Chart (from LLM data)
    # ============================================================================

    @staticmethod
    async def create_comparison_chart(comparison_data: Dict[str, Any]) -> str:
        """
        비교 분석 차트 생성 (LLM 데이터 기반)

        Args:
            comparison_data: {
                "labels": ["A", "B"],
                "values": [85, 92],
                "metric": "소거능 (%)"
            }

        Returns:
            HTML string
        """
        try:
            labels = comparison_data.get("labels", [])
            values = comparison_data.get("values", [])
            metric = comparison_data.get("metric", "값")

            if not labels or not values or len(labels) != len(values):
                logger.warning(f"[Visualizer] Invalid comparison data")
                return "<p>비교 데이터가 부족합니다</p>"

            logger.info(f"[Visualizer] Creating comparison chart: {labels}")

            fig = go.Figure(data=[
                go.Bar(
                    x=labels,
                    y=values,
                    text=values,
                    textposition='outside',
                    textfont=dict(size=14, family="Arial, sans-serif"),
                    marker=dict(
                        color=values,
                        colorscale='Viridis',
                        showscale=False,
                        line=dict(width=1, color="#34495e")
                    ),
                    hovertemplate="<b>%{x}</b><br>" + metric + ": %{y}<extra></extra>"
                )
            ])

            fig.update_layout(
                title={
                    "text": f"<b>Figure 4. 비교 분석 - {metric}</b>",
                    "font": {"size": 20, "family": "Arial, sans-serif", "color": "#2c3e50"},
                    "x": 0.5,
                    "xanchor": "center"
                },
                xaxis_title="<b>항목</b>",
                yaxis_title=f"<b>{metric}</b>",
                template="plotly_white",
                height=450,
                margin=dict(l=80, r=80, t=120, b=80),
                font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
                xaxis=dict(title_font=dict(size=14), tickfont=dict(size=12)),
                yaxis=dict(title_font=dict(size=14), tickfont=dict(size=12))
            )

            html_string = fig.to_html(
                include_plotlyjs='cdn',
                div_id='comparison_chart'
            )

            return html_string

        except Exception as e:
            logger.error(f"[Visualizer] Error creating comparison chart: {str(e)}")
            raise

    # ============================================================================
    # All Visualizations Bundle
    # ============================================================================

    @staticmethod
    async def create_all_visualizations(
        report: ResearchReport, 
        viz_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        모든 시각화 생성

        Args:
            report: ResearchReport 객체
            viz_data: LLM에서 추출한 시각화 데이터 (Optional)

        Returns:
            {
                "evidence_network": HTML,
                "feasibility_chart": HTML,
                "paper_distribution": HTML,
                "comparison_chart": HTML (if data available)
            }
        """
        try:
            logger.info(f"[Visualizer] Creating all visualizations for: {report.title}")
            logger.info(f"[Visualizer] Visualization data provided: {bool(viz_data)}")

            visualizations = {}

            # 1. 증거 네트워크
            visualizations["evidence_network"] = await Visualizer.create_evidence_network(report)

            # 2. 타당성 점수 차트 (viz_data 사용 또는 기본값)
            if viz_data and "feasibility_breakdown" in viz_data:
                breakdown = viz_data["feasibility_breakdown"]
                logger.info(f"[Visualizer] Using LLM-provided feasibility breakdown: {breakdown}")
            else:
                # 기본값 사용
                breakdown = {
                    "선행연구": min(100, report.validation.feasibility_score + 10),
                    "방법론": report.validation.feasibility_score,
                    "실행가능성": max(0, report.validation.feasibility_score - 15),
                    "학술기여도": report.validation.feasibility_score,
                }
                logger.warning(f"[Visualizer] No feasibility breakdown in viz_data, using defaults")
                
            visualizations["feasibility_chart"] = await Visualizer.create_feasibility_chart(
                report.validation,
                breakdown
            )

            # 3. 비교 차트 (viz_data에 comparison_data가 있는 경우)
            if viz_data and "comparison_data" in viz_data:
                comparison_data = viz_data["comparison_data"]
                if "labels" in comparison_data and "values" in comparison_data:
                    visualizations["comparison_chart"] = await Visualizer.create_comparison_chart(
                        comparison_data
                    )
                    logger.info(f"[Visualizer] Created comparison chart")

            logger.info(f"[Visualizer] All visualizations created successfully: {list(visualizations.keys())}")
            return visualizations

        except Exception as e:
            logger.error(f"[Visualizer] Error creating all visualizations: {str(e)}", exc_info=True)
            raise
