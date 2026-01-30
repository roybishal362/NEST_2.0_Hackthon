// C-TRUST API Client
// ========================================
import axios, { AxiosError } from 'axios';
import type { Study, DQIScore, DashboardSummary, AgentStatus, AgentSignal, GuardianStatus, Notification } from '@/types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// Retry configuration
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

export const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add retry interceptor with exponential backoff
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const config = error.config;
        if (!config) return Promise.reject(error);

        // Initialize retry count
        const retryCount = (config as any).__retryCount || 0;

        // Check if should retry (network errors or 5xx server errors)
        const shouldRetry =
            !error.response ||
            (error.response.status >= 500 && error.response.status < 600);

        if (shouldRetry && retryCount < MAX_RETRIES) {
            (config as any).__retryCount = retryCount + 1;

            // Exponential backoff delay
            const delay = RETRY_DELAY_MS * Math.pow(2, retryCount);
            console.log(`Retrying API request (${retryCount + 1}/${MAX_RETRIES}) after ${delay}ms...`);

            await new Promise(resolve => setTimeout(resolve, delay));
            return api.request(config);
        }

        // Log error for debugging
        console.error('API Error:', {
            url: config.url,
            method: config.method,
            status: error.response?.status,
            message: error.message,
        });

        return Promise.reject(error);
    }
);

// API Methods
export const studiesAPI = {
    getAll: async (): Promise<Study[]> => {
        const { data } = await api.get('/studies');
        return data;
    },

    getById: async (studyId: string): Promise<Study> => {
        const { data } = await api.get(`/studies/${studyId}`);
        return data;
    },

    getDQI: async (studyId: string): Promise<DQIScore> => {
        const { data } = await api.get(`/studies/${studyId}/dqi`);
        return data;
    },

    getFeatures: async (studyId: string): Promise<Record<string, any>> => {
        const { data } = await api.get(`/studies/${studyId}/features`);
        return data;
    },

    getDashboardSummary: async (): Promise<DashboardSummary> => {
        const { data } = await api.get('/dashboard/summary');
        return data;
    }
};

// Agent API
export const agentsAPI = {
    getAll: async (): Promise<AgentStatus[]> => {
        const { data } = await api.get('/agents');
        return data;
    },

    getSignals: async (agentId: string): Promise<AgentSignal[]> => {
        const { data } = await api.get(`/agents/${agentId}/signals`);
        return data;
    },

    getAllSignals: async (): Promise<AgentSignal[]> => {
        const { data } = await api.get('/agents/signals');
        return data;
    },
};

// Guardian API
export const guardianAPI = {
    getStatus: async (): Promise<GuardianStatus> => {
        const { data } = await api.get('/guardian/status');
        return data;
    },

    getEvents: async (limit?: number): Promise<GuardianStatus['events']> => {
        const { data } = await api.get('/guardian/events', { params: { limit } });
        return data;
    },
};

// Notifications API
export const notificationsAPI = {
    getAll: async (): Promise<Notification[]> => {
        const { data } = await api.get('/notifications');
        return data;
    },

    acknowledge: async (notificationId: string): Promise<void> => {
        await api.post(`/notifications/${notificationId}/acknowledge`);
    },

    markRead: async (notificationId: string): Promise<void> => {
        await api.post(`/notifications/${notificationId}/read`);
    },
};

// Export API
export const exportAPI = {
    exportStudies: async (format: 'csv' | 'excel' = 'csv'): Promise<Blob> => {
        const { data } = await api.get('/export/studies', {
            params: { format },
            responseType: 'blob',
        });
        return data;
    },

    exportStudy: async (studyId: string, format: 'csv' | 'excel' = 'csv'): Promise<Blob> => {
        const { data } = await api.get(`/export/studies/${studyId}`, {
            params: { format },
            responseType: 'blob',
        });
        return data;
    },
};
