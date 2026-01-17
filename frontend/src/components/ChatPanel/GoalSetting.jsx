import React, { useState } from 'react';
import { Lightbulb, Check } from 'lucide-react';
import sessionService from '../../services/sessionService';

const GoalSetting = ({ isOpen, analysisGoal, onAnalysisGoalChange, sessionId }) => {
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

  const handleConfirm = async () => {
    if (!sessionId || !analysisGoal.trim()) return;
    
    setIsSaving(true);
    try {
      await sessionService.updateAnalysisGoal(sessionId, analysisGoal);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus(null), 2000);
    } catch (error) {
      console.error('Failed to save analysis goal:', error);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus(null), 2000);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className={`
      bg-teal-50 border-b border-teal-100 overflow-hidden transition-all duration-300 ease-in-out relative z-10
      ${isOpen ? 'max-h-40 opacity-100' : 'max-h-0 opacity-0'}
    `}>
      <div className="p-4">
        <div className="flex items-center gap-2 mb-2 text-teal-800 font-semibold text-xs uppercase tracking-wide">
          <Lightbulb size={12} className="fill-teal-800" />
          핵심 주제 / 분석 목표 설정
        </div>
        <div className="flex gap-2">
          <textarea
            value={analysisGoal}
            onChange={(e) => onAnalysisGoalChange(e.target.value)}
            placeholder="예: 이 논문의 한계점 위주로 비판해줘, 혹은 초보자도 알기 쉽게 요약해줘..."
            className="flex-1 text-xs p-2 rounded border-2 border-teal-500 bg-white text-gray-700 focus:outline-none focus:border-teal-600 resize-none h-20 placeholder-gray-300"
          />
          <button
            onClick={handleConfirm}
            disabled={isSaving || !analysisGoal.trim()}
            className={`
              flex items-center justify-center gap-1 px-3 py-2 rounded font-semibold text-xs uppercase tracking-wide
              transition-all duration-200 flex-shrink-0 h-20
              ${saveStatus === 'saved' 
                ? 'bg-green-500 text-white' 
                : saveStatus === 'error'
                ? 'bg-red-500 text-white'
                : isSaving
                ? 'bg-teal-400 text-white'
                : analysisGoal.trim()
                ? 'bg-teal-500 text-white hover:bg-teal-600'
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }
            `}
          >
            <Check size={14} />
            {saveStatus === 'saved' ? '저장됨' : saveStatus === 'error' ? '실패' : '확정'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default React.memo(GoalSetting);
