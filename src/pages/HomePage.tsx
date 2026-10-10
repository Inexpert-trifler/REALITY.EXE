import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';
import { BottomNavigation } from '../components/layout/BottomNavigation';
import { PixelCard } from '../components/pixel/PixelCard';
import { PixelButton } from '../components/pixel/PixelButton';
import { PixelBadge } from '../components/pixel/PixelBadge';
import { XPBar } from '../components/player/XPBar';
import { PixelSettingsModal } from '../components/pixel/PixelSettingsModal';
import { useGame } from '../context/GameContext';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { profile, stats } = useGame();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F3E8] relative pb-20 pt-16 md:pl-64 md:pb-0">
      <AppHeader onOpenSettings={() => setIsSettingsOpen(true)} />

      <main className="flex-1 p-4 flex flex-col gap-4 max-w-[480px] md:max-w-5xl mx-auto w-full select-none md:p-8">
        {/* Top Region Sub-Bar */}
        <div className="flex justify-between items-center px-1 opacity-90 md:mb-2">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-xs bg-[#6FAF5F]" />
            <span className="font-label-sm text-[10px] text-[#A9784F] uppercase tracking-widest font-bold">
              REGION: SECTOR-04 // TERRA
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 bg-[#EEC052] rounded-xs rotate-45" />
            <span className="font-label-sm text-[10px] text-[#6B5C4D] font-bold">CLEAR SKIES</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-8">
          {/* Left Column */}
          <div className="flex flex-col gap-4">
            {/* Player Level & XP Status Card */}
            <PixelCard shadowSize="md">
              <div className="flex items-center gap-3">
                <div className="relative shrink-0">
                  <div className="w-14 h-14 rounded-lg bg-[#F8E5D6] border-2 border-[#2B2118] p-1 flex items-center justify-center text-[24px]">
                    🧭
                  </div>
                  <div className="absolute -bottom-1 -right-1 bg-[#6FAF5F] text-[#FFFDF5] text-[10px] font-extrabold px-1.5 py-0.5 rounded border border-[#2B2118] shadow-[0_1.5px_0_0_#2B2118]">
                    LVL {profile.level}
                  </div>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between mb-0.5">
                    <span className="font-label-sm text-[10px] uppercase tracking-wider text-[#A9784F] font-bold">
                      {profile.preferred_play_style} / REALM RUNNER
                    </span>
                    <span className="font-headline-sm text-[16px] text-[#2B2118] uppercase">
                      LEVEL 0{profile.level}
                    </span>
                  </div>
                  <XPBar currentXp={profile.xp} maxXp={1500} level={profile.level} />
                </div>
              </div>
            </PixelCard>

            {/* Main Hero Callout */}
            <PixelCard shadowSize="lg" className="text-center flex flex-col items-center py-6 h-full justify-center">
              <PixelBadge variant="sky" icon="explore" className="mb-2">
                OVERWORLD EXPEDITION
              </PixelBadge>
              <h1 className="font-headline-lg text-[24px] uppercase text-[#2B2118] tracking-tight mb-2">
                YOUR WORLD IS WAITING.
              </h1>
              <p className="font-body-md text-[14px] text-[#6B5C4D] max-w-[300px] mb-5">
                Step outside your door. The AI Game Master will carve an adventure out of your everyday streets.
              </p>

              <PixelButton
                variant="primary"
                size="lg"
                fullWidth
                onClick={() => navigate('/quest/setup')}
              >
                [ ENTER REALITY ]
              </PixelButton>
            </PixelCard>
          </div>

          {/* Right Column */}
          <div className="flex flex-col gap-4">
            {/* Pixel Art Scene Container */}
            <div className="relative w-full rounded-xl overflow-hidden bg-gradient-to-b from-[#8FC8D8] via-[#BFE5ED] to-[#FFF1E8] p-3 border-2 border-[#2B2118] shadow-[0_6px_0_0_#2B2118]">
              <div className="flex items-center justify-between relative z-10 mb-2">
                <div className="flex items-center gap-1.5 bg-[#FFFDF5]/90 px-2 py-0.5 rounded border border-[#2B2118] shadow-[0_1.5px_0_0_#2B2118]">
                  <span className="w-2 h-2 rounded-full bg-[#6FAF5F] animate-ping" />
                  <span className="font-label-sm text-[10px] text-[#2B2118] uppercase tracking-wide font-bold">
                    SURROUNDINGS: UNCHARTED
                  </span>
                </div>
                <div className="w-7 h-7 bg-[#EEC052] rounded-xs border-2 border-[#2B2118] shadow-[0_0_0_1px_#2B2118] flex items-center justify-center">
                  <div className="w-3 h-3 bg-[#FFDF9B] rounded-xs" />
                </div>
              </div>

              {/* SVG Overworld Landscape */}
              <div className="relative w-full h-44 rounded-lg overflow-hidden bg-gradient-to-b from-[#8fc8d8] via-[#aedbe6] to-[#eaf5d8] border-2 border-[#2B2118]">
                <div className="absolute top-3 left-4 flex gap-1 opacity-90 animate-pulse">
                  <span className="w-8 h-3 bg-white rounded-xs border border-[#2B2118]" />
                  <span className="w-12 h-4 bg-white rounded-xs -mt-1 border border-[#2B2118]" />
                </div>

                <div className="absolute -bottom-4 left-0 right-0 h-28">
                  <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 320 120">
                    <polygon points="0,120 0,60 40,40 100,55 160,28 220,50 280,35 320,60 320,120" fill="#6faf5f" stroke="#231a11" strokeWidth="2" />
                    <polygon points="0,120 0,75 50,65 90,75 140,55 190,65 250,52 320,78 320,120" fill="#3f7042" stroke="#231a11" strokeWidth="2" />
                    <polygon points="0,120 0,90 60,82 120,94 180,80 240,90 320,84 320,120" fill="#2e6b24" stroke="#231a11" strokeWidth="2" />
                  </svg>
                </div>

                <div className="absolute bottom-2 right-4 z-10 flex flex-col items-center">
                  <div className="w-10 h-10 bg-[#3F7042] border-2 border-[#2B2118] rounded-md shadow-[0_2px_0_0_#2B2118]" />
                  <div className="w-3 h-4 bg-[#80552F] border-x-2 border-b-2 border-[#2B2118]" />
                </div>

                {/* Scout Character Silhouette */}
                <div className="absolute bottom-2 left-8 z-10 flex flex-col items-center">
                  <div className="w-6 h-6 bg-[#E5B84B] border-2 border-[#2B2118] rounded-xs text-[12px] flex items-center justify-center">
                    🚶
                  </div>
                  <div className="w-4 h-3 bg-[#3F7042] border-x-2 border-b-2 border-[#2B2118]" />
                </div>
              </div>
            </div>

            {/* 3 Quick Game Stats Cards */}
            <div className="grid grid-cols-3 gap-3 flex-1 h-full">
              <div className="flex flex-col items-center p-3 rounded-lg bg-[#FFFDF5] border-2 border-[#2B2118] shadow-[0_4px_0_0_#2B2118] text-center justify-center">
                <div className="w-8 h-8 rounded-md bg-[#6FAF5F] text-[#FFFDF5] border border-[#2B2118] flex items-center justify-center shadow-[0_1.5px_0_0_#2B2118] mb-1">
                  <span className="material-symbols-outlined text-[18px]">explore</span>
                </div>
                <span className="font-headline-md text-[18px] text-[#2B2118] leading-none">
                  {stats.total_quests_completed}
                </span>
                <span className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold mt-1">
                  QUESTS
                </span>
              </div>

              <div className="flex flex-col items-center p-3 rounded-lg bg-[#FFFDF5] border-2 border-[#2B2118] shadow-[0_4px_0_0_#2B2118] text-center justify-center">
                <div className="w-8 h-8 rounded-md bg-[#C49A2F] text-[#FFFDF5] border border-[#2B2118] flex items-center justify-center shadow-[0_1.5px_0_0_#2B2118] mb-1">
                  <span className="material-symbols-outlined text-[18px]">stars</span>
                </div>
                <span className="font-headline-md text-[18px] text-[#2B2118] leading-none">
                  {stats.total_xp}
                </span>
                <span className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold mt-1">
                  TOTAL XP
                </span>
              </div>

              <div className="flex flex-col items-center p-3 rounded-lg bg-[#FFFDF5] border-2 border-[#2B2118] shadow-[0_4px_0_0_#2B2118] text-center justify-center">
                <div className="w-8 h-8 rounded-md bg-[#FDC394] text-[#2B2118] border border-[#2B2118] flex items-center justify-center shadow-[0_1.5px_0_0_#2B2118] mb-1">
                  <span className="material-symbols-outlined text-[18px]">wb_sunny</span>
                </div>
                <span className="font-headline-md text-[18px] text-[#2B2118] leading-none">
                  {Math.floor(stats.time_outside_minutes / 60)}h {stats.time_outside_minutes % 60}m
                </span>
                <span className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold mt-1">
                  OUTSIDE
                </span>
              </div>
            </div>
          </div>
        </div>
      </main>

      <BottomNavigation />
      <PixelSettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
};
