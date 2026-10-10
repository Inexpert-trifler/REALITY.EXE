import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';
import { BottomNavigation } from '../components/layout/BottomNavigation';
import { PixelCard } from '../components/pixel/PixelCard';
import { PixelButton } from '../components/pixel/PixelButton';
import { PixelBadge } from '../components/pixel/PixelBadge';
import { GameMasterMessage } from '../components/gamemaster/GameMasterMessage';
import { useGame } from '../context/GameContext';

export const QuestReadyPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentQuest, startQuest } = useGame();

  const handleStart = async () => {
    await startQuest();
    navigate('/quest/pocket');
  };

  if (!currentQuest) {
    return (
      <div className="flex flex-col min-h-screen bg-[#F7F3E8] justify-center items-center p-4">
        <p className="font-headline-sm uppercase text-[#2B2118] mb-4">NO QUEST READY</p>
        <PixelButton variant="primary" onClick={() => navigate('/quest/setup')}>
          GO TO SETUP
        </PixelButton>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F3E8] relative pb-20 pt-16 md:pl-64 md:pb-0">
      <AppHeader title="QUEST READY" />

      <main className="flex-1 p-4 flex flex-col gap-4 max-w-[480px] md:max-w-3xl mx-auto w-full select-none">
        {/* Top Status Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-xs bg-[#6FAF5F]" />
            <span className="font-label-sm text-[12px] text-[#A9784F] uppercase font-bold tracking-widest">
              GAME MASTER // DISPATCH
            </span>
          </div>
          <PixelBadge variant="sky" icon="verified">
            QUEST READY
          </PixelBadge>
        </div>

        {/* Main Quest Card */}
        <PixelCard shadowSize="lg" className="flex flex-col gap-3">
          <div className="flex items-center justify-between pb-2 border-b-2 border-[#F8E5D6]">
            <span className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-extrabold tracking-wider">
              [ QUEST DISPATCH #8904 ]
            </span>
            <span className="font-label-sm text-[10px] text-[#3F7042] uppercase font-bold">
              {currentQuest.play_style} MODE
            </span>
          </div>

          <h1 className="font-headline-lg text-[22px] uppercase text-[#2B2118] tracking-tight">
            {currentQuest.title}
          </h1>

          <p className="font-body-md text-[14px] text-[#6B5C4D] leading-relaxed">
            {currentQuest.brief}
          </p>

          {/* Metadata Badges Row */}
          <div className="flex items-center gap-2 flex-wrap pt-1">
            <PixelBadge variant="outline" icon="schedule">
              {currentQuest.duration_minutes} MIN
            </PixelBadge>
            <PixelBadge variant="secondary" icon="nature">
              {currentQuest.environment}
            </PixelBadge>
            <PixelBadge variant="primary" icon="speed">
              {currentQuest.difficulty}
            </PixelBadge>
            <PixelBadge variant="xp" icon="stars">
              +{currentQuest.xp_reward} XP
            </PixelBadge>
          </div>

          {/* Objectives List */}
          <div className="mt-2 pt-3 border-t-2 border-[#F8E5D6] flex flex-col gap-2">
            <span className="font-label-sm text-[11px] uppercase font-bold text-[#A9784F] tracking-wider">
              OBJECTIVES:
            </span>
            <div className="flex flex-col gap-2">
              {currentQuest.objectives.map((obj: any, index: number) => {
                const text = typeof obj === 'string' ? obj : obj.instruction;
                return (
                  <div
                    key={index}
                    className="flex items-start gap-2.5 p-2.5 rounded-lg bg-[#FFF1E8] border border-[#2B2118]"
                  >
                    <span className="w-5 h-5 rounded-xs bg-[#6FAF5F] text-[#FFFDF5] font-bold text-[10px] flex items-center justify-center border border-[#2B2118] shrink-0">
                      {index + 1}
                    </span>
                    <span className="font-body-sm text-[13px] text-[#2B2118]">
                      {text}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </PixelCard>

        {/* AI Game Master Dispatch Bubble */}
        <GameMasterMessage
          message="I've crafted this path specifically for your current grid area. Lock your phone into Pocket Mode once you take your first step."
        />

        {/* Primary Action Buttons */}
        <div className="flex flex-col gap-2 mt-2">
          <PixelButton variant="primary" size="lg" fullWidth onClick={handleStart}>
            [ START QUEST ]
          </PixelButton>
          <PixelButton
            variant="ghost"
            size="md"
            fullWidth
            onClick={() => navigate('/quest/setup')}
          >
            GENERATE ANOTHER
          </PixelButton>
        </div>
      </main>

      <BottomNavigation />
    </div>
  );
};
