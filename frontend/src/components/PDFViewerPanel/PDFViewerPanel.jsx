import React, { memo } from "react";
import { Book, FileText, FileType, List, ZoomIn, ZoomOut } from "lucide-react";
import PDFToolbar from "./PDFToolbar";
import PDFViewer from "./PDFViewer";
import SummaryViewer from "./SummaryViewer";

const PDFViewerPanel = ({
  paper,
  toggleLibrary,
  isLibraryOpen,
  viewMode,
  onViewModeChange,
  zoomLevel,
  onZoomIn,
  onZoomOut,
}) => {
  if (!paper) {
    return (
      <div className="flex-1 bg-gray-100 flex flex-col items-center justify-center text-gray-400">
        <FileText size={48} className="mb-4 opacity-50" />
        <p>왼쪽 라이브러리에서 항목을 선택하거나 업로드해주세요.</p>
      </div>
    );
  }

  const isReport = paper.type === "report";

  // Report일 때는 무조건 summary 모드
  const displayMode = isReport ? "summary" : viewMode;

  return (
    <div className="flex-1 flex flex-col h-full min-w-0 bg-gray-100 relative">
      {/* Toolbar */}
      <PDFToolbar
        paper={paper}
        toggleLibrary={toggleLibrary}
        isLibraryOpen={isLibraryOpen}
        isReport={isReport}
        viewMode={viewMode}
        onViewModeChange={onViewModeChange}
        zoomLevel={zoomLevel}
        onZoomIn={onZoomIn}
        onZoomOut={onZoomOut}
      />

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative bg-gray-200">
        {displayMode === "text" && !isReport ? (
          <PDFViewer paper={paper} pdfUrl={paper.pdfUrl} />
        ) : (
          <SummaryViewer
            paper={paper}
            isReport={isReport}
            zoomLevel={zoomLevel}
          />
        )}
      </div>
    </div>
  );
};

export default memo(PDFViewerPanel);
