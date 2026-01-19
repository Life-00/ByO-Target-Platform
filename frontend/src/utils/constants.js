// Agent Types & Colors
export const AGENT_MODES = {
  GENERAL: 'general',
  SEARCH: 'search',
  ANALYSIS: 'analysis',
  REPORT: 'report',
};

export const AGENT_THEME = {
  general: {
    color: 'text-teal-600',
    bg: 'bg-teal-50',
    border: 'border-teal-200',
    btn: 'bg-teal-600 hover:bg-teal-700',
    icon: 'Bot',
    name: 'General Agent',
    placeholder: '자유롭게 대화하거나 질문하세요...',
  },
  search: {
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    btn: 'bg-blue-600 hover:bg-blue-700',
    icon: 'Globe',
    name: 'Search Agent',
    placeholder: '궁금한 내용을 검색하거나 질문하세요...',
  },
  analysis: {
    color: 'text-purple-600',
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    btn: 'bg-purple-600 hover:bg-purple-700',
    icon: 'Microscope',
    name: 'Deep Analysis',
    placeholder: '논문에 대해 깊이 있는 질문을 해주세요...',
  },
  report: {
    color: 'text-orange-600',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    btn: 'bg-orange-600 hover:bg-orange-700',
    icon: 'PenTool',
    name: 'Report Agent',
    placeholder: '보고서 작성에 필요한 지시를 내려주세요...',
  },
};

// Initial Mock Data (removed - using real data from backend)
export const INITIAL_PAPERS_DATA = [];

export const INITIAL_REPORTS_DATA = [];

export const INITIAL_MESSAGES = [
  {
    id: 1,
    sender: 'ai',
    agentType: 'default',
    text: '안녕하세요! 논문 분석 도우미입니다. [기본], [검색], [정밀분석], [리포트] 에이전트를 선택해 대화할 수 있습니다.',
    timestamp: new Date().toISOString()
  }
];
