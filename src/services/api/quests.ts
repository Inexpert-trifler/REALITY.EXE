import { apiFetch } from './client';
import { Quest, QuestAttempt, QuestGenerateRequest } from '../../types/quest';

export interface QuestListResponse {
  quests: Quest[];
  total: number;
  skip: number;
  limit: number;
}

export const questsApi = {
  async generate(payload: QuestGenerateRequest): Promise<Quest> {
    return apiFetch<Quest>('/quests/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async list(skip = 0, limit = 20): Promise<QuestListResponse> {
    return apiFetch<QuestListResponse>(`/quests?skip=${skip}&limit=${limit}`);
  },

  async getById(id: string): Promise<Quest> {
    return apiFetch<Quest>(`/quests/${id}`);
  },

  async start(questId: string): Promise<QuestAttempt> {
    return apiFetch<QuestAttempt>(`/quests/${questId}/start`, {
      method: 'POST',
    });
  },

  async pocket(questId: string): Promise<QuestAttempt> {
    return apiFetch<QuestAttempt>(`/quests/${questId}/pocket`, {
      method: 'POST',
    });
  },

  async returnFromPocket(questId: string): Promise<QuestAttempt> {
    return apiFetch<QuestAttempt>(`/quests/${questId}/return`, {
      method: 'POST',
    });
  },

  async pause(questId: string): Promise<QuestAttempt> {
    return apiFetch<QuestAttempt>(`/quests/${questId}/pause`, {
      method: 'POST',
    });
  },

  async resume(questId: string): Promise<QuestAttempt> {
    return apiFetch<QuestAttempt>(`/quests/${questId}/resume`, {
      method: 'POST',
    });
  },

  async abandon(questId: string): Promise<QuestAttempt> {
    return apiFetch<QuestAttempt>(`/quests/${questId}/abandon`, {
      method: 'POST',
    });
  },

  async complete(questId: string): Promise<QuestAttempt> {
    return apiFetch<QuestAttempt>(`/quests/${questId}/complete`, {
      method: 'POST',
    });
  }
};
