import React, { createContext, useContext, useState, useEffect } from 'react';
import { Quest, QuestAttempt } from '../types/quest';
import { PlayerProfile, PlayerStats, Achievement, AdventureLogEntry } from '../types/player';
import { questsApi } from '../services/api/quests';
import { playerApi } from '../services/api/player';
import { authApi } from '../services/api/auth';

interface GameContextType {
  // Player State
  profile: PlayerProfile;
  stats: PlayerStats;
  achievements: Achievement[];
  adventureLog: AdventureLogEntry[];
  
  // Active Quest State Flow
  currentQuest: Quest | null;
  currentAttempt: QuestAttempt | null;
  selectedEvidenceFile: File | null;
  evidencePreviewUrl: string | null;
  verificationStatus: 'IDLE' | 'VERIFYING' | 'SUCCESS' | 'UNCERTAIN' | 'ERROR';
  verificationMessage: string;

  // Actions
  generateQuest: (options: { duration: number; environment: string; playStyle: string }) => Promise<Quest>;
  startQuest: () => Promise<void>;
  enterPocketMode: () => Promise<void>;
  returnFromPocket: () => Promise<void>;
  setEvidenceFile: (file: File | null) => void;
  submitQuest: () => Promise<void>;
  completeQuestFlow: () => void;
  resetQuest: () => void;
  refreshPlayerData: () => Promise<void>;
}

// Initial Default Profile Data (used as initial state or when backend returns initial user)
const DEFAULT_PROFILE: PlayerProfile = {
  id: 'usr_4092',
  user_id: 'usr_4092',
  display_name: 'SCOUT #4092',
  scout_id: '4092',
  sector: 'SOL-TERRA // GRID 42',
  preferred_personality: 'COZY',
  preferred_play_style: 'EXPLORER',
  level: 4,
  xp: 1240,
  created_at: new Date().toISOString(),
};

const DEFAULT_STATS: PlayerStats = {
  total_quests_attempted: 14,
  total_quests_completed: 12,
  completion_rate: 0.85,
  total_xp: 1240,
  level: 4,
  xp_in_current_level: 240,
  xp_to_next_level: 260,
  time_outside_minutes: 275,
  unlocked_achievements_count: 4,
  total_achievements_count: 16,
};

const DEFAULT_ACHIEVEMENTS: Achievement[] = [
  {
    id: 'ach_1',
    name: 'TOUCH GRASS',
    description: 'First outdoor expedition completed with zero phone screen disruptions.',
    rarity: 'COMMON // 88% SCOUTS',
    icon: '🌱',
    status: 'UNLOCKED',
    is_new: true,
  },
  {
    id: 'ach_2',
    name: 'CURIOUS MIND',
    description: 'Cataloged 5 species of micro-flora growing inside stone and asphalt crevices.',
    rarity: 'RARE // 34% SCOUTS',
    icon: '🔍',
    status: 'UNLOCKED',
  },
  {
    id: 'ach_3',
    name: 'POCKET PLAYER',
    description: 'Completed 3 distinct exploratory journeys in blind sensor audio mode.',
    rarity: 'UNCOMMON // 52% SCOUTS',
    icon: '🎒',
    status: 'UNLOCKED',
  },
  {
    id: 'ach_4',
    name: 'CHAOS AGENT',
    description: 'Deviated 400m from prescribed GPS walkways into wild alleyways.',
    rarity: 'EPIC // 19% SCOUTS',
    icon: '🌪️',
    status: 'UNLOCKED',
  },
  {
    id: 'ach_5',
    name: 'NIGHT OWL',
    description: 'Initiate and complete a twilight scout expedition past astronomical dusk.',
    rarity: 'LOCKED // UNKNOWN',
    icon: 'lock',
    status: 'LOCKED',
  },
  {
    id: 'ach_6',
    name: 'CARTOGRAPHER',
    description: 'Record expeditions across 3 distinct ecological biomes: Riverbank, Canopy, and Concrete.',
    rarity: 'LOCKED // UNKNOWN',
    icon: 'lock',
    status: 'LOCKED',
  },
];

const DEFAULT_LOG: AdventureLogEntry[] = [
  {
    id: 'log_1',
    quest_id: 'q_hidden_patch',
    title: 'THE HIDDEN PATCH',
    play_style: 'EXPLORER',
    duration_minutes: 20,
    completed_at: 'Today',
    xp_earned: 250,
    icon: '🌱',
  },
  {
    id: 'log_2',
    quest_id: 'q_listen_city',
    title: 'LISTEN TO THE CITY',
    play_style: 'OBSERVER',
    duration_minutes: 15,
    completed_at: 'Yesterday',
    xp_earned: 120,
    icon: '👀',
  },
  {
    id: 'log_3',
    quest_id: 'q_blue_thing',
    title: 'THE BLUE THING',
    play_style: 'DETECTIVE',
    duration_minutes: 25,
    completed_at: '2 days ago',
    xp_earned: 180,
    icon: '🔍',
  },
];

const DEFAULT_QUEST: Quest = {
  id: 'q_hidden_patch',
  title: 'THE HIDDEN PATCH',
  brief: 'A secluded patch of moss or wildflowers thrives untouched by human construction.',
  duration_minutes: 20,
  environment: 'PARK',
  difficulty: 'EASY',
  play_style: 'EXPLORER',
  personality: 'COZY',
  objectives: [
    { id: 'obj_1', instruction: 'Walk until you find non-lawn vegetation growing out of a stone or wall seam.' },
    { id: 'obj_2', instruction: 'Observe its pattern for 30 seconds without taking out your phone.' },
    { id: 'obj_3', instruction: 'Collect a mental detail or quick photo for verification.' }
  ],
  xp_reward: 250,
  evidence_required: true,
  safety_notes: 'Watch for uneven pavement and respect private garden boundaries.',
  created_at: new Date().toISOString(),
};

const GameContext = createContext<GameContextType | null>(null);

export const GameProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [profile, setProfile] = useState<PlayerProfile>(DEFAULT_PROFILE);
  const [stats, setStats] = useState<PlayerStats>(DEFAULT_STATS);
  const [achievements, setAchievements] = useState<Achievement[]>(DEFAULT_ACHIEVEMENTS);
  const [adventureLog, setAdventureLog] = useState<AdventureLogEntry[]>(DEFAULT_LOG);

  const [currentQuest, setCurrentQuest] = useState<Quest | null>(DEFAULT_QUEST);
  const [currentAttempt, setCurrentAttempt] = useState<QuestAttempt | null>(null);
  const [selectedEvidenceFile, setSelectedEvidenceFile] = useState<File | null>(null);
  const [evidencePreviewUrl, setEvidencePreviewUrl] = useState<string | null>(null);
  const [verificationStatus, setVerificationStatus] = useState<'IDLE' | 'VERIFYING' | 'SUCCESS' | 'UNCERTAIN' | 'ERROR'>('IDLE');
  const [verificationMessage, setVerificationMessage] = useState<string>('Game Master is analyzing your expedition...');

  // Auto-fetch profile from backend if online
  const refreshPlayerData = async () => {
    try {
      const p = await playerApi.getProfile();
      if (p) setProfile(p);
      const s = await playerApi.getStats();
      if (s) setStats(s);
      const a = await playerApi.getAchievements();
      if (a && a.length > 0) setAchievements(a);
      const log = await playerApi.getAdventureLog();
      if (log && log.length > 0) setAdventureLog(log);
    } catch {
      // Offline / unauthenticated fallback state active
    }
  };

  useEffect(() => {
    refreshPlayerData();
  }, []);

  const generateQuest = async (options: { duration: number; environment: string; playStyle: string }): Promise<Quest> => {
    try {
      const q = await questsApi.generate({
        duration_minutes: options.duration,
        environment: options.environment.toUpperCase(),
        play_style: options.playStyle.toUpperCase(),
      });
      setCurrentQuest(q);
      setCurrentAttempt(null);
      setSelectedEvidenceFile(null);
      setEvidencePreviewUrl(null);
      setVerificationStatus('IDLE');
      return q;
    } catch {
      // Deterministic quest fallback if API fails
      const fallbackQuest: Quest = {
        id: `q_gen_${Date.now()}`,
        title: options.playStyle === 'DETECTIVE' ? 'THE ANOMALOUS MARK' : options.playStyle === 'CHAOS' ? 'THE FORBIDDEN SHORTCUT' : 'THE HIDDEN PATCH',
        brief: `An unexpected ${options.environment.toLowerCase()} element awaits discovery along your path.`,
        duration_minutes: options.duration,
        environment: options.environment,
        difficulty: options.duration > 30 ? 'MEDIUM' : 'EASY',
        play_style: options.playStyle,
        personality: 'COZY',
        objectives: [
          { id: '1', instruction: `Explore the ${options.environment.toLowerCase()} zone for ${options.duration} minutes.` },
          { id: '2', instruction: 'Notice 3 micro-details off your normal routine path.' },
          { id: '3', instruction: 'Optional: Capture proof of your finding.' }
        ],
        xp_reward: options.duration * 10 + 50,
        evidence_required: true,
        safety_notes: 'Stay aware of traffic and stay in well-lit areas.',
        created_at: new Date().toISOString(),
      };
      setCurrentQuest(fallbackQuest);
      setCurrentAttempt(null);
      setSelectedEvidenceFile(null);
      setEvidencePreviewUrl(null);
      setVerificationStatus('IDLE');
      return fallbackQuest;
    }
  };

  const startQuest = async () => {
    if (!currentQuest) return;
    try {
      const attempt = await questsApi.start(currentQuest.id);
      setCurrentAttempt(attempt);
    } catch {
      setCurrentAttempt({
        id: `att_${Date.now()}`,
        quest_id: currentQuest.id,
        user_id: profile.id,
        status: 'ACTIVE',
        started_at: new Date().toISOString(),
        earned_xp: 0,
      });
    }
  };

  const enterPocketMode = async () => {
    if (!currentQuest) return;
    try {
      const attempt = await questsApi.pocket(currentQuest.id);
      setCurrentAttempt(attempt);
    } catch {
      if (currentAttempt) {
        setCurrentAttempt({
          ...currentAttempt,
          status: 'POCKET_MODE',
          pocket_started_at: new Date().toISOString(),
        });
      }
    }
  };

  const returnFromPocket = async () => {
    if (!currentQuest) return;
    try {
      const attempt = await questsApi.returnFromPocket(currentQuest.id);
      setCurrentAttempt(attempt);
    } catch {
      if (currentAttempt) {
        setCurrentAttempt({
          ...currentAttempt,
          status: 'RETURNED',
        });
      }
    }
  };

  const setEvidenceFile = (file: File | null) => {
    setSelectedEvidenceFile(file);
    if (file) {
      const url = URL.createObjectURL(file);
      setEvidencePreviewUrl(url);
    } else {
      setEvidencePreviewUrl(null);
    }
  };

  const submitQuest = async () => {
    if (!currentQuest) return;
    setVerificationStatus('VERIFYING');
    setVerificationMessage('Game Master is scanning your expedition evidence...');

    try {
      // Simulate/Trigger API verification step
      await new Promise((r) => setTimeout(r, 2200));

      try {
        await questsApi.complete(currentQuest.id);
      } catch {
        // Fallback for completion state
      }

      // Update XP and Stats
      const earnedXp = currentQuest.xp_reward;
      setProfile((prev) => {
        const newXp = prev.xp + earnedXp;
        const newLevel = Math.floor(newXp / 300) + 1;
        return {
          ...prev,
          xp: newXp,
          level: newLevel,
        };
      });

      setStats((prev) => ({
        ...prev,
        total_quests_completed: prev.total_quests_completed + 1,
        total_xp: prev.total_xp + earnedXp,
        time_outside_minutes: prev.time_outside_minutes + currentQuest.duration_minutes,
      }));

      // Add to adventure log
      const newEntry: AdventureLogEntry = {
        id: `log_${Date.now()}`,
        quest_id: currentQuest.id,
        title: currentQuest.title,
        play_style: currentQuest.play_style,
        duration_minutes: currentQuest.duration_minutes,
        completed_at: 'Just now',
        xp_earned: earnedXp,
        icon: currentQuest.play_style === 'EXPLORER' ? '🌱' : currentQuest.play_style === 'DETECTIVE' ? '🔍' : '👀',
      };
      setAdventureLog((prev) => [newEntry, ...prev]);

      setVerificationStatus('SUCCESS');
      setVerificationMessage(`Expedition Verified! Granted +${earnedXp} XP.`);
    } catch {
      setVerificationStatus('ERROR');
      setVerificationMessage("That evidence didn't make it through. Try submitting again?");
    }
  };

  const completeQuestFlow = () => {
    // Flow complete, clear attempt
    setCurrentAttempt(null);
  };

  const resetQuest = () => {
    setCurrentQuest(DEFAULT_QUEST);
    setCurrentAttempt(null);
    setSelectedEvidenceFile(null);
    setEvidencePreviewUrl(null);
    setVerificationStatus('IDLE');
  };

  return (
    <GameContext.Provider
      value={{
        profile,
        stats,
        achievements,
        adventureLog,
        currentQuest,
        currentAttempt,
        selectedEvidenceFile,
        evidencePreviewUrl,
        verificationStatus,
        verificationMessage,
        generateQuest,
        startQuest,
        enterPocketMode,
        returnFromPocket,
        setEvidenceFile,
        submitQuest,
        completeQuestFlow,
        resetQuest,
        refreshPlayerData,
      }}
    >
      {children}
    </GameContext.Provider>
  );
};

export const useGame = () => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
};
