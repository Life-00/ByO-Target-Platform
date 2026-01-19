import React from 'react';
import { Bot, Globe, Microscope, PenTool } from 'lucide-react';

const AgentSelector = ({ agentMode, onSetAgentMode }) => {
  return (
    <div className="absolute bottom-full left-0 w-full p-2 flex justify-center pointer-events-none">
      <div className="bg-white/90 backdrop-blur-sm shadow-lg border border-gray-200 rounded-full p-1 flex gap-1 pointer-events-auto">
        <button
          onClick={() => onSetAgentMode('general')}
          className={`px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 transition-all whitespace-nowrap
            ${agentMode === 'general' ? 'bg-teal-100 text-teal-700 ring-1 ring-teal-200' : 'text-gray-500 hover:bg-gray-100'}`}
        >
          <Bot size={12} /> General
        </button>
        <button
          onClick={() => onSetAgentMode('search')}
          className={`px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 transition-all whitespace-nowrap
            ${agentMode === 'search' ? 'bg-blue-100 text-blue-700 ring-1 ring-blue-200' : 'text-gray-500 hover:bg-gray-100'}`}
        >
          <Globe size={12} /> Search
        </button>
        <button
          onClick={() => onSetAgentMode('analysis')}
          className={`px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 transition-all whitespace-nowrap
            ${agentMode === 'analysis' ? 'bg-purple-100 text-purple-700 ring-1 ring-purple-200' : 'text-gray-500 hover:bg-gray-100'}`}
        >
          <Microscope size={12} /> Analysis
        </button>
        <button
          disabled
          className="px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 transition-all whitespace-nowrap text-gray-300 cursor-not-allowed opacity-50"
          title="Coming soon"
        >
          <PenTool size={12} /> Report
        </button>
      </div>
    </div>
  );
};

export default React.memo(AgentSelector);
