import React from "react";
import { List, AlertCircle } from "lucide-react";

const SummaryViewer = ({ paper, isReport, zoomLevel }) => {
  const hasSummary = paper.summary && paper.summary.trim().length > 0;

  return (
    <div className="w-full h-full overflow-auto p-8 flex justify-center custom-scrollbar">
      <div
        className="bg-white shadow-lg transition-transform duration-200 ease-out origin-top text-justify"
        style={{
          width: `${8.5 * (zoomLevel / 100)}in`,
          minHeight: `${11 * (zoomLevel / 100)}in`,
          padding: `${1 * (zoomLevel / 100)}in`,
          fontSize: `${12 * (zoomLevel / 100)}pt`,
          height: "fit-content",
        }}
      >
        <div
          className={`font-serif text-gray-900 leading-relaxed ${isReport ? "font-sans" : ""}`}
        >
          {/* Header */}
          <div className="text-center mb-8 border-b pb-4">
            <h1 className="font-bold text-2xl mb-2 leading-tight">
              {paper.title}
            </h1>
            <p className="italic text-gray-600 mb-2">{paper.authors}</p>
            <p className="text-sm font-mono text-gray-500">
              {paper.conference} {paper.year}
            </p>
          </div>

          {/* Report Content - 전체 내용 표시 */}
          {isReport && paper.content ? (
            <div className="prose prose-sm max-w-none">
              {/* 타당성 평가 */}
              {paper.feasibilityScore !== undefined && (
                <div
                  className={`mb-6 p-4 rounded-lg border-2 ${paper.isFeasible ? "bg-green-50 border-green-300" : "bg-amber-50 border-amber-300"}`}
                >
                  <h3 className="font-bold text-base mb-2 flex items-center gap-2">
                    <span>{paper.isFeasible ? "✅" : "⚠️"}</span>
                    타당성 평가
                  </h3>
                  <div className="text-sm space-y-1">
                    <p>
                      <strong>점수:</strong> {paper.feasibilityScore.toFixed(1)}
                      /100
                    </p>
                    <p>
                      <strong>결과:</strong>{" "}
                      {paper.isFeasible ? "연구 가능" : "추가 검토 필요"}
                    </p>
                    {paper.abstract && (
                      <p className="mt-2">
                        <strong>근거:</strong> {paper.abstract}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* 주요 섹션 */}
              {paper.sections && paper.sections.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-bold text-base mb-3 border-b pb-2">
                    📄 주요 분석
                  </h3>
                  {paper.sections.map((section, idx) => (
                    <div key={idx} className="mb-4">
                      <h4 className="font-semibold text-sm text-gray-800 mb-2">
                        {idx + 1}. {section.title}
                      </h4>
                      <p className="text-sm text-gray-700 leading-relaxed pl-4 whitespace-pre-wrap">
                        {section.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {/* 시각화 */}
              {paper.visualizations && Object.keys(paper.visualizations).length > 0 && (
                <div className="mb-6 space-y-6">
                  <h3 className="font-bold text-base mb-3 border-b pb-2">
                    📊 시각화
                  </h3>
                  
                  {/* Evidence Network */}
                  {paper.visualizations.evidence_network && (
                    <div className="border rounded-lg overflow-hidden">
                      <h4 className="font-semibold text-sm bg-gray-50 p-3">
                        연구 증거 네트워크
                      </h4>
                      <div className="w-full h-96">
                        <iframe
                          srcDoc={paper.visualizations.evidence_network}
                          style={{ width: "100%", height: "100%", border: "none" }}
                          title="evidence-network"
                        />
                      </div>
                    </div>
                  )}
                  
                  {/* Feasibility Chart */}
                  {paper.visualizations.feasibility_chart && (
                    <div className="border rounded-lg overflow-hidden">
                      <h4 className="font-semibold text-sm bg-gray-50 p-3">
                        타당성 평가 차트
                      </h4>
                      <div className="w-full h-96">
                        <iframe
                          srcDoc={paper.visualizations.feasibility_chart}
                          style={{ width: "100%", height: "100%", border: "none" }}
                          title="feasibility-chart"
                        />
                      </div>
                    </div>
                  )}
                  
                  {/* Paper Distribution */}
                  {paper.visualizations.paper_distribution && (
                    <div className="border rounded-lg overflow-hidden">
                      <h4 className="font-semibold text-sm bg-gray-50 p-3">
                        논문 분포
                      </h4>
                      <div className="w-full h-96">
                        <iframe
                          srcDoc={paper.visualizations.paper_distribution}
                          style={{ width: "100%", height: "100%", border: "none" }}
                          title="paper-distribution"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 권장사항 */}
              {paper.recommendations && paper.recommendations.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-bold text-base mb-3 border-b pb-2">
                    💡 권장사항
                  </h3>
                  <ul className="list-decimal list-inside space-y-2 text-sm text-gray-700">
                    {paper.recommendations.map((rec, idx) => (
                      <li key={idx} className="pl-2">
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 한계점 */}
              {paper.limitations && paper.limitations.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-bold text-base mb-3 border-b pb-2">
                    ⚠️ 한계점
                  </h3>
                  <ul className="list-disc list-inside space-y-2 text-sm text-gray-700">
                    {paper.limitations.map((limit, idx) => (
                      <li key={idx} className="pl-2">
                        {limit}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 참고 논문 */}
              {paper.relatedPapers && paper.relatedPapers.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-bold text-base mb-3 border-b pb-2">
                    📚 참고 논문 ({paper.relatedPapers.length}개)
                  </h3>
                  <ul className="list-disc list-inside space-y-1 text-xs text-gray-600">
                    {paper.relatedPapers.map((ref, idx) => (
                      <li key={idx} className="pl-2">
                        {ref.title} ({ref.authors}, {ref.year})
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 생성 일시 */}
              {paper.createdAt && (
                <div className="text-xs text-gray-500 text-right mt-8 pt-4 border-t">
                  생성일시: {new Date(paper.createdAt).toLocaleString("ko-KR")}
                </div>
              )}
            </div>
          ) : isReport && !paper.content ? (
            /* Report인데 content가 없을 때 */
            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle
                size={20}
                className="text-blue-600 flex-shrink-0 mt-0.5"
              />
              <div>
                <h3 className="font-semibold text-blue-900 mb-1">
                  보고서 내용 없음
                </h3>
                <p className="text-sm text-blue-800">
                  이 보고서의 상세 내용이 아직 로드되지 않았습니다.
                </p>
              </div>
            </div>
          ) : hasSummary ? (
            /* Paper 요약 */
            <div className="mb-6">
              <h3 className="font-bold uppercase text-sm mb-2 text-gray-800 flex items-center gap-2">
                <List size={16} className="text-teal-700" />
                Core Summary
              </h3>
              <p className="font-sans text-sm text-gray-700 leading-6 pl-4 border-l-4 border-teal-200 whitespace-pre-wrap">
                {paper.summary}
              </p>
            </div>
          ) : (
            /* 요약 없음 */
            <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle
                size={20}
                className="text-amber-600 flex-shrink-0 mt-0.5"
              />
              <div>
                <h3 className="font-semibold text-amber-900 mb-1">
                  요약 생성 중
                </h3>
                <p className="text-sm text-amber-800">
                  이 문서의 요약이 아직 생성되지 않았습니다. 문서가 처리되는
                  동안 잠시 기다려주세요.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default React.memo(SummaryViewer);
