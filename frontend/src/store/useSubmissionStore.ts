import { create } from 'zustand';

interface SubmissionState {
  code: string;
  isSubmitting: boolean;
  jobId: string | null;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | null;
  result: any;
  setCode: (code: string) => void;
  submitCode: () => Promise<void>;
  updateStatus: (status: any) => void;
}

export const useSubmissionStore = create<SubmissionState>((set, get) => ({
  code: '',
  isSubmitting: false,
  jobId: null,
  status: null,
  result: null,
  setCode: (code) => set({ code }),
  submitCode: async () => {
    set({ isSubmitting: true, status: 'PENDING' });
    try {
      // Mock API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      set({ jobId: 'job-12345', isSubmitting: false, status: 'RUNNING' });
      // In real implementation, this would connect to SSE/WebSocket listening for status updates
    } catch (error) {
      set({ status: 'FAILED', isSubmitting: false });
    }
  },
  updateStatus: (status) => set({ status })
}));
