import React from 'react';
import { Book, FileBarChart } from 'lucide-react';

const LibraryTabs = ({ activeTab, onTabChange }) => {
  return (
    <div className="flex border-b border-gray-200 shrink-0 h-12">
      <button
        onClick={() => onTabChange("papers")}
        className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-1 transition-colors relative
          ${activeTab === "papers" ? 'text-teal-600 bg-teal-50/50' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'}
        `}
      >
        <Book size={14} />
        Papers
        {activeTab === "papers" && <span className="absolute bottom-0 left-0 w-full h-0.5 bg-teal-600"></span>}
      </button>
      <button
        onClick={() => onTabChange("reports")}
        className={`flex-1 py-3 text-xs font-semibold flex items-center justify-center gap-1 transition-colors relative
          ${activeTab === "reports" ? 'text-teal-600 bg-teal-50/50' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'}
        `}
      >
        <FileBarChart size={14} />
        Reports
        {activeTab === "reports" && <span className="absolute bottom-0 left-0 w-full h-0.5 bg-teal-600"></span>}
      </button>
    </div>
  );
};

export default React.memo(LibraryTabs);
