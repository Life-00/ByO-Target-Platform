import React from "react";
import { Book, FileType, List, ZoomIn, ZoomOut } from "lucide-react";

const PDFToolbar = ({
  paper,
  toggleLibrary,
  isLibraryOpen,
  isReport,
  viewMode,
  onViewModeChange,
  zoomLevel,
  onZoomIn,
  onZoomOut,
}) => {
  return (
    <div className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4 shadow-sm z-10">
      <div className="flex items-center gap-3">
        <button
          onClick={toggleLibrary}
          className={`p-2 rounded-md hover:bg-gray-100 text-gray-600 ${isLibraryOpen ? "bg-gray-100" : ""}`}
          title="Toggle Library"
        >
          <Book size={18} />
        </button>
        <div className="h-6 w-px bg-gray-300 mx-1"></div>

        <div className="flex items-center gap-2 truncate max-w-[200px] md:max-w-xs">
          {isReport ? (
            <span className="bg-indigo-100 text-indigo-700 text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider shrink-0">
              Report
            </span>
          ) : (
            <span className="bg-teal-100 text-teal-700 text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider shrink-0">
              Paper
            </span>
          )}
          <h2
            className="font-semibold text-gray-800 text-sm truncate"
            title={paper.title}
          >
            {paper.title}
          </h2>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* View Mode Toggle */}
        {!isReport && (
          <div className="flex items-center bg-gray-100 rounded-lg p-1 mr-2">
            <button
              onClick={() => onViewModeChange("text")}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors
                ${viewMode === "text" ? "bg-white text-teal-700 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
              title="원본 텍스트(PDF)"
            >
              <FileType size={14} />
              <span>Text</span>
            </button>
            <button
              onClick={() => onViewModeChange("summary")}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors
                ${viewMode === "summary" ? "bg-white text-teal-700 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
              title="요약 및 분석"
            >
              <List size={14} />
              <span>Summary</span>
            </button>
          </div>
        )}

        {/* Report Tab Label */}
        {isReport && (
          <div className="flex items-center bg-gray-100 rounded-lg p-1 mr-2 px-3">
            <span className="flex items-center gap-1 text-xs font-medium text-indigo-700">
              <List size={14} />
              <span>Report</span>
            </span>
          </div>
        )}

        {/* Zoom Controls */}
        {viewMode === "summary" && (
          <>
            <div className="h-6 w-px bg-gray-300 mx-1 hidden md:block"></div>
            <div className="flex items-center bg-gray-100 rounded-lg p-1">
              <button
                onClick={onZoomOut}
                className="p-1 hover:bg-white rounded shadow-sm text-gray-600"
              >
                <ZoomOut size={14} />
              </button>
              <span className="text-xs font-mono w-12 text-center text-gray-600">
                {zoomLevel}%
              </span>
              <button
                onClick={onZoomIn}
                className="p-1 hover:bg-white rounded shadow-sm text-gray-600"
              >
                <ZoomIn size={14} />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default React.memo(PDFToolbar);
