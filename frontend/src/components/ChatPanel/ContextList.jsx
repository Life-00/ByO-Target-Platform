import React from 'react';
import { CheckSquare, Book, FileBarChart } from 'lucide-react';

const ContextList = ({ isOpen, selectedItems }) => {
  return (
    <div className={`
      bg-teal-50 border-b border-teal-100 overflow-hidden transition-all duration-300 ease-in-out relative z-10
      ${isOpen ? 'max-h-64 opacity-100' : 'max-h-0 opacity-0'}
    `}>
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 text-teal-800 font-semibold text-xs uppercase tracking-wide">
            <CheckSquare size={12} className="text-teal-800" />
            선택된 분석 대상 ({selectedItems.length})
          </div>
        </div>

        <div className="max-h-40 overflow-y-auto custom-scrollbar pr-1 space-y-1">
          {selectedItems.length === 0 ? (
            <p className="text-xs text-teal-400 italic p-2 text-center">선택된 문서가 없습니다.</p>
          ) : (
            selectedItems.map(item => (
              <div key={item.id} className="bg-white p-2 rounded border border-teal-100 flex items-start gap-2">
                <div className="mt-0.5 text-teal-500">
                  {item.type === 'report' ? <FileBarChart size={12} /> : <Book size={12} />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-gray-800 truncate">{item.title}</p>
                  <p className="text-[10px] text-gray-500 truncate">{item.authors}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default React.memo(ContextList);
