export interface PlayerProfile {
  id: string;
  user_id: string;
  display_name: string;
  scout_id: string;
  sector: string;
  preferred_personality: string;
  preferred_play_style: string;
  level: number;
  xp: number;
  created_at: string;
}

export interface PlayerStats {
  total_quests_attempted: number;
  total_quests_completed: number;
  completion_rate: number;
  total_xp: number;
  level: number;
  xp_in_current_level: number;
  xp_to_next_level: number;
  time_outside_minutes: number;
  unlocked_achievements_count: number;
  total_achievements_count: number;
}

export interface Achievement {
  id: string;
  name: string;
  description: string;
  rarity: string;
  icon: string;
  status: 'UNLOCKED' | 'LOCKED';
  is_new?: boolean;
  unlocked_at?: string | null;
}

export interface AdventureLogEntry {
  id: string;
  quest_id: string;
  title: string;
  play_style: string;
  duration_minutes: number;
  completed_at: string;
  xp_earned: number;
  icon: string;
}
