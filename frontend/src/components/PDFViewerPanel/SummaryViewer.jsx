import React from 'react';
import { List, AlertCircle } from 'lucide-react';

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
          height: 'fit-content'
        }}
      >
        <div className={`font-serif text-gray-900 leading-relaxed ${isReport ? 'font-sans' : ''}`}>
          <div className="text-center mb-8 border-b pb-4">
            <h1 className="font-bold text-2xl mb-2 leading-tight">{paper.title}</h1>
            <p className="italic text-gray-600 mb-2">{paper.authors}</p>
            <p className="text-sm font-mono text-gray-500">{paper.conference} {paper.year}</p>
          </div>

          {hasSummary ? (
            <div className="mb-6">
              <h3 className="font-bold uppercase text-sm mb-2 text-gray-800 flex items-center gap-2">
                <List size={16} className="text-teal-700" />
                {isReport ? 'Executive Summary' : 'Core Summary'}
              </h3>
              <p className="font-sans text-sm text-gray-700 leading-6 pl-4 border-l-4 border-teal-200 whitespace-pre-wrap">
                {paper.summary}
              </p>
            </div>
          ) : (
            <div className="mb-6 bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle size={20} className="text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-amber-900 mb-1">요약 생성 중</h3>
                <p className="text-sm text-amber-800">
                  이 문서의 요약이 아직 생성되지 않았습니다. 문서가 처리되는 동안 잠시 기다려주세요.
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
