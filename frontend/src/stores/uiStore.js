import { create } from 'zustand';

export const useUIStore = create((set) => ({
  isLibraryOpen: true,
  viewMode: 'text', // 'text' (PDF) | 'summary' (parsed)
  zoomLevel: 100,
  isGoalOpen: false,
  isContextListOpen: false,

  // Actions
  toggleLibrary: () => set((state) => ({ isLibraryOpen: !state.isLibraryOpen })),
  setLibraryOpen: (isOpen) => set({ isLibraryOpen: isOpen }),
  setViewMode: (mode) => set({ viewMode: mode }),
  setZoomLevel: (level) => set({ zoomLevel: Math.max(50, Math.min(200, level)) }),
  zoomIn: () => set((state) => ({ zoomLevel: Math.min(200, state.zoomLevel + 10) })),
  zoomOut: () => set((state) => ({ zoomLevel: Math.max(50, state.zoomLevel - 10) })),
  toggleGoal: () => set((state) => ({ 
    isGoalOpen: !state.isGoalOpen,
    isContextListOpen: false, // Close context list when opening goal
  })),
  toggleContextList: () => set((state) => ({
    isContextListOpen: !state.isContextListOpen,
    isGoalOpen: false, // Close goal when opening context list
  })),
  closeAll: () => set({ isGoalOpen: false, isContextListOpen: false }),
}));
