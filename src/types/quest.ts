export type QuestDifficulty = 'EASY' | 'MEDIUM' | 'HARD' | 'CHAOS';
export type EnvironmentType = 'PARK' | 'CAMPUS' | 'CITY' | 'SURPRISE';
export type PlayStyleType = 'EXPLORER' | 'DETECTIVE' | 'OBSERVER' | 'ADVENTURER' | 'CHAOS';

export interface Objective {
  id: string;
  instruction: string;
  optional?: boolean;
}

export interface Quest {
  id: string;
  title: string;
  brief: string;
  duration_minutes: number;
  environment: string;
  difficulty: string;
  play_style: string;
  personality: string;
  objectives: Objective[] | string[];
  xp_reward: number;
  evidence_required: boolean;
  safety_notes?: string | null;
  created_at: string;
}

export type AttemptStatus = 
  | 'CREATED'
  | 'ACTIVE'
  | 'POCKET_MODE'
  | 'RETURNED'
  | 'EVIDENCE_PENDING'
  | 'VERIFYING'
  | 'COMPLETED'
  | 'PAUSED'
  | 'ABANDONED';

export interface QuestAttempt {
  id: string;
  quest_id: string;
  user_id: string;
  status: AttemptStatus;
  started_at: string;
  pocket_started_at?: string | null;
  completed_at?: string | null;
  result?: string | null;
  earned_xp: number;
}

export interface QuestGenerateRequest {
  duration_minutes: number;
  environment: string;
  play_style: string;
  personality?: string;
}
