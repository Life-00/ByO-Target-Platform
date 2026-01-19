import React from 'react';

const PDFViewer = ({ paper, pdfUrl }) => {
  if (!pdfUrl) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
        <p>PDF URL이 제공되지 않았습니다.</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col">
      <iframe
        src={`${pdfUrl}#toolbar=0`}
        className="w-full h-full border-none"
        title="PDF Viewer"
      />
    </div>
  );
};

export default React.memo(PDFViewer);
