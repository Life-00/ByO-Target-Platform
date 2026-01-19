import { create } from 'zustand';
import { INITIAL_PAPERS_DATA, INITIAL_REPORTS_DATA } from '../utils/constants';

export const useLibraryStore = create((set) => ({
  papers: INITIAL_PAPERS_DATA,
  reports: INITIAL_REPORTS_DATA,
  selectedPaper: null, // Changed from INITIAL_PAPERS_DATA[0]
  checkedItems: new Set(),
  activeTab: 'papers', // 'papers' | 'reports'

  // Actions
  setSelectedPaper: (paper) => set({ selectedPaper: paper }),
  toggleCheck: (id) => set((state) => {
    const newSet = new Set(state.checkedItems);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    return { checkedItems: newSet };
  }),
  batchSelect: (ids, shouldSelect) => set((state) => {
    const newSet = new Set(state.checkedItems);
    ids.forEach(id => {
      if (shouldSelect) newSet.add(id);
      else newSet.delete(id);
    });
    return { checkedItems: newSet };
  }),
  deletePaper: (id) => set((state) => {
    const newPapers = state.papers.filter(p => p.id !== id);
    let newSelected = state.selectedPaper;
    if (state.selectedPaper?.id === id) {
      newSelected = newPapers[0] || null;
    }
    const newChecked = new Set(state.checkedItems);
    newChecked.delete(id);
    return { 
      papers: newPapers, 
      selectedPaper: newSelected,
      checkedItems: newChecked 
    };
  }),
  deleteReport: (id) => set((state) => {
    const newReports = state.reports.filter(r => r.id !== id);
    let newSelected = state.selectedPaper;
    if (state.selectedPaper?.id === id) {
      newSelected = null;
    }
    const newChecked = new Set(state.checkedItems);
    newChecked.delete(id);
    return { 
      reports: newReports, 
      selectedPaper: newSelected,
      checkedItems: newChecked 
    };
  }),
  batchDelete: () => set((state) => {
    const newPapers = state.papers.filter(p => !state.checkedItems.has(p.id));
    const newReports = state.reports.filter(r => !state.checkedItems.has(r.id));
    let newSelected = state.selectedPaper;
    if (state.selectedPaper && state.checkedItems.has(state.selectedPaper.id)) {
      newSelected = null;
    }
    return {
      papers: newPapers,
      reports: newReports,
      selectedPaper: newSelected,
      checkedItems: new Set(),
    };
  }),
  addPaper: (paper) => set((state) => ({
    papers: [paper, ...state.papers],
    selectedPaper: paper,
  })),
  setPapers: (papers) => set({
    papers: papers,
    selectedPaper: papers.length > 0 ? papers[0] : null,
  }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  clearCheckedItems: () => set({ checkedItems: new Set() }),
}));
