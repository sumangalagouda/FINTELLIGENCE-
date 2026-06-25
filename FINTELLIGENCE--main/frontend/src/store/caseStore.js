import { create } from 'zustand';

const useCaseStore = create((set) => ({
  selectedCaseId: null,
  setSelectedCaseId: (id) => set({ selectedCaseId: id }),
  cases: [],
  setCases: (cases) => set({ cases }),
}));

export default useCaseStore;
