import { create } from 'zustand';
import { INITIAL_MESSAGES } from '../utils/constants';

export const useChatStore = create((set) => ({
  messages: INITIAL_MESSAGES,
  isTyping: false,
  agentMode: 'general', // 'general' | 'search' | 'analysis' | 'report'
  analysisGoal: '',

  // Actions
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message],
  })),
  setMessages: (messages) => set({ messages }),
  setIsTyping: (isTyping) => set({ isTyping }),
  setAgentMode: (mode) => set({ agentMode: mode }),
  setAnalysisGoal: (goal) => set({ analysisGoal: goal }),
  clearMessages: () => set({ messages: INITIAL_MESSAGES }),
  resetChat: () => set({
    messages: INITIAL_MESSAGES,
    isTyping: false,
    agentMode: 'general',
    analysisGoal: '',
  }),
}));
