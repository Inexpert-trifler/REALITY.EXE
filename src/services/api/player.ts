import { apiFetch } from './client';
import { PlayerProfile, PlayerStats, Achievement, AdventureLogEntry } from '../../types/player';

export const playerApi = {
  async getProfile(): Promise<PlayerProfile> {
    return apiFetch<PlayerProfile>('/player/profile');
  },

  async updateProfile(updates: Partial<PlayerProfile>): Promise<PlayerProfile> {
    return apiFetch<PlayerProfile>('/player/profile', {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  async getStats(): Promise<PlayerStats> {
    return apiFetch<PlayerStats>('/player/stats');
  },

  async getAchievements(): Promise<Achievement[]> {
    return apiFetch<Achievement[]>('/player/achievements');
  },

  async getAdventureLog(): Promise<AdventureLogEntry[]> {
    return apiFetch<AdventureLogEntry[]>('/history');
  }
};
