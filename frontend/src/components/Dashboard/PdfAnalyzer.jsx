import React from "react";
import { Worker, Viewer } from "@react-pdf-viewer/core";
import { defaultLayoutPlugin } from "@react-pdf-viewer/default-layout";
import { searchPlugin } from "@react-pdf-viewer/search";
import "./PdfAnalyzer.css";

import "@react-pdf-viewer/core/lib/styles/index.css";
import "@react-pdf-viewer/default-layout/lib/styles/index.css";
import "@react-pdf-viewer/search/lib/styles/index.css";

const PdfAnalyzer = ({ fileUrl, highlightText }) => {
  // 🔥 중요: useMemo 안/조건문 안 말고, 렌더 최상단에서 바로 호출
  const searchPluginInstance = searchPlugin();
  const defaultLayoutPluginInstance = defaultLayoutPlugin();

  const { highlight } = searchPluginInstance;

  const timerRef = React.useRef(null);

  React.useEffect(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    const q = (highlightText || "").trim();
    if (!q) return;

    timerRef.current = setTimeout(() => {
      try {
        highlight(q);
      } catch (e) {
        console.log("[PdfAnalyzer] highlight failed:", e);
      }
    }, 150);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [highlightText, highlight]);

  return (
    <div className="pdf-analysis-page">
      <div className="pdf-card">
        <div className="pdf-viewer-wrap">
          <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.4.120/build/pdf.worker.min.js">
            <Viewer
              fileUrl={fileUrl}
              plugins={[searchPluginInstance]} // ✅ defaultLayoutPluginInstance 제거
              theme="light"
            />
          </Worker>
        </div>
      </div>
    </div>
  );
};

export default React.memo(PdfAnalyzer);
