import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';
import { BottomNavigation } from '../components/layout/BottomNavigation';
import { PixelCard } from '../components/pixel/PixelCard';
import { PixelButton } from '../components/pixel/PixelButton';
import { PixelBadge } from '../components/pixel/PixelBadge';
import { XPBar } from '../components/player/XPBar';
import { GameMasterMessage } from '../components/gamemaster/GameMasterMessage';
import { useGame } from '../context/GameContext';

export const QuestCompletePage: React.FC = () => {
  const navigate = useNavigate();
  const { currentQuest, profile, completeQuestFlow } = useGame();

  const handleNextQuest = () => {
    completeQuestFlow();
    navigate('/quest/setup');
  };

  const handleViewProfile = () => {
    completeQuestFlow();
    navigate('/profile');
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F3E8] relative pb-20 pt-16 select-none md:pl-64 md:pb-0">
      <AppHeader title="QUEST COMPLETE" />

      <main className="flex-1 p-4 flex flex-col gap-4 max-w-[480px] md:max-w-3xl mx-auto w-full">
        {/* Victory Celebration Header */}
        <PixelCard shadowSize="lg" className="text-center py-6 bg-gradient-to-b from-[#FFFDF5] to-[#FFF1E8]">
          <div className="w-16 h-16 rounded-xl bg-[#E5B84B] border-2 border-[#2B2118] text-[#2B2118] flex items-center justify-center text-[36px] mx-auto mb-2 shadow-[0_4px_0_0_#B88526] animate-bounce">
            🏆
          </div>

          <PixelBadge variant="xp" icon="military_tech" size="md" className="mb-2">
            VICTORY
          </PixelBadge>

          <h1 className="font-headline-lg text-[26px] uppercase text-[#2B2118] tracking-tight">
            QUEST COMPLETE!
          </h1>
          <p className="font-headline-md text-[18px] uppercase text-[#3F7042] mt-1 font-bold">
            {currentQuest?.title || 'THE HIDDEN PATCH'}
          </p>

          <div className="mt-4 p-3 rounded-lg bg-[#FFFDF5] border-2 border-[#2B2118] inline-flex items-center gap-2 shadow-[0_2px_0_0_#2B2118]">
            <span className="text-[20px]">⭐</span>
            <span className="font-headline-lg text-[22px] text-[#C49A2F] uppercase">
              +{currentQuest?.xp_reward || 250} XP GAINED
            </span>
          </div>
        </PixelCard>

        {/* Level & XP Progress Card */}
        <PixelCard shadowSize="md">
          <span className="font-label-sm text-[11px] uppercase font-bold text-[#A9784F] tracking-wider block mb-2">
            SCOUT PROGRESSION
          </span>
          <XPBar currentXp={profile.xp} maxXp={1500} level={profile.level} />
        </PixelCard>

        {/* Achievement Unlocked Callout */}
        <PixelCard shadowSize="md" className="bg-[#FFFDF5] border-[#3F7042]">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-[#B0F49C] border-2 border-[#2B2118] text-[24px] flex items-center justify-center shadow-[0_2px_0_0_#2B2118] shrink-0">
              🌱
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-headline-sm text-[15px] uppercase text-[#2B2118]">
                  TOUCH GRASS
                </span>
                <span className="font-label-sm text-[9px] uppercase font-extrabold text-[#3F7042] bg-[#B0F49C] px-1.5 py-0.5 rounded border border-[#2B2118]">
                  UNLOCKED
                </span>
              </div>
              <p className="font-body-sm text-[12px] text-[#6B5C4D] mt-0.5">
                Completed outdoor expedition without phone screen checks.
              </p>
            </div>
          </div>
        </PixelCard>

        {/* Game Master Message */}
        <GameMasterMessage
          message="Sensational work, Scout #4092. You've grounded yourself in the physical world today. Your dossier has been updated."
        />

        {/* Action CTAs */}
        <div className="flex flex-col gap-2 mt-2">
          <PixelButton variant="primary" size="lg" fullWidth onClick={handleNextQuest}>
            [ NEXT QUEST ]
          </PixelButton>
          <PixelButton variant="secondary" size="md" fullWidth onClick={handleViewProfile}>
            VIEW PROFILE
          </PixelButton>
        </div>
      </main>

      <BottomNavigation />
    </div>
  );
};
