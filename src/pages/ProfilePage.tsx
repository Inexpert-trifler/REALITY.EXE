import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';
import { BottomNavigation } from '../components/layout/BottomNavigation';
import { PixelCard } from '../components/pixel/PixelCard';
import { PixelButton } from '../components/pixel/PixelButton';
import { PixelBadge } from '../components/pixel/PixelBadge';
import { XPBar } from '../components/player/XPBar';
import { GameMasterMessage } from '../components/gamemaster/GameMasterMessage';
import { PixelSettingsModal } from '../components/pixel/PixelSettingsModal';
import { useGame } from '../context/GameContext';
import { Achievement } from '../types/player';

export const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const { profile, stats, achievements, adventureLog } = useGame();

  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [selectedBadge, setSelectedBadge] = useState<Achievement | null>(null);
  const [showEmptyLog, setShowEmptyLog] = useState(false);

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F3E8] relative pb-20 pt-16 select-none md:pl-64 md:pb-0">
      <AppHeader onOpenSettings={() => setIsSettingsOpen(true)} />

      <main className="flex-1 p-4 flex flex-col gap-4 max-w-[480px] md:max-w-5xl mx-auto w-full">
        {/* SCOUT DOSSIER SUB-BAR */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-5 h-5 rounded-sm bg-[#6FAF5F] text-[#FFFDF5] font-label-sm text-[10px] shadow-[0_2px_0_0_#2B2118] border border-[#2B2118]">
              #
            </span>
            <div className="flex flex-col">
              <span className="font-headline-sm text-[18px] uppercase text-[#2B2118] tracking-tight leading-none">
                SCOUT DOSSIER
              </span>
              <span className="font-label-sm text-[10px] text-[#A9784F] uppercase font-bold tracking-widest mt-0.5">
                SECTOR: SOL-TERRA // GRID 42
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setIsSettingsOpen(true)}
            className="group flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[#F8E5D6] hover:bg-[#F2DFD1] active:translate-y-0.5 border-2 border-[#2B2118] shadow-[0_3px_0_0_#2B2118] transition-all text-[#2B2118] cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px] text-[#A9784F] group-hover:rotate-45 transition-transform duration-300">
              settings
            </span>
            <span className="font-label-md text-[12px] uppercase tracking-wider text-[#2B2118]">
              SYS.CFG
            </span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-8 mt-2">
          {/* Left Column */}
          <div className="flex flex-col gap-4">
            {/* RETRO RPG CHARACTER CARD (Centerpiece) */}
            <PixelCard shadowSize="lg" className="flex flex-col gap-3">
              <div className="flex items-center justify-between pb-3 border-b-2 border-[#F8E5D6]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-xs bg-[#6FAF5F] border border-[#2B2118] shadow-[0_1px_0_0_#2B2118]" />
                  <span className="font-label-md text-[12px] text-[#6B5C4D] uppercase tracking-widest font-bold">
                    SCOUT ID #{profile.scout_id}
                  </span>
                </div>
                <PixelBadge variant="secondary" icon="nature_people" size="sm">
                  OVERWORLD
                </PixelBadge>
              </div>

              <div className="pt-1 flex items-start gap-3">
                {/* Pixel Avatar Illustration Frame */}
                <div className="relative shrink-0">
                  <div className="w-24 h-24 rounded-lg bg-[#FEEADC] border-2 border-[#2B2118] p-1 shadow-[0_4px_0_0_#2B2118] relative overflow-hidden flex items-center justify-center">
                    <svg className="w-full h-full" viewBox="0 0 64 64" fill="none">
                      <rect width="64" height="64" fill="#8FC8D8" />
                      <rect x="8" y="10" width="16" height="4" fill="#FFFFFF" fillOpacity="0.8" />
                      <rect x="12" y="6" width="8" height="4" fill="#FFFFFF" fillOpacity="0.8" />
                      <rect x="0" y="44" width="64" height="20" fill="#6FAF5F" />
                      <rect x="14" y="40" width="36" height="4" fill="#6FAF5F" />
                      <rect x="22" y="36" width="20" height="4" fill="#2E6B24" />
                      <rect x="16" y="28" width="10" height="20" fill="#80552F" />
                      <rect x="22" y="26" width="20" height="22" fill="#2E6B24" />
                      <rect x="26" y="28" width="12" height="18" fill="#6FAF5F" />
                      <rect x="28" y="32" width="8" height="6" fill="#231A11" />
                      <rect x="29" y="34" width="2" height="3" fill="#E5B84B" />
                      <rect x="33" y="34" width="2" height="3" fill="#E5B84B" />
                      <rect x="26" y="16" width="12" height="12" fill="#F4BB8D" />
                      <rect x="28" y="20" width="2" height="2" fill="#231A11" />
                      <rect x="34" y="20" width="2" height="2" fill="#231A11" />
                      <rect x="24" y="12" width="16" height="6" fill="#80552F" />
                      <rect x="22" y="15" width="20" height="3" fill="#2E1500" />
                      <rect x="30" y="10" width="4" height="3" fill="#E5B84B" />
                    </svg>
                  </div>
                  <div className="absolute -bottom-2 -right-1 px-1.5 py-0.5 rounded-xs bg-[#C49A2F] text-[#473400] border border-[#2B2118] shadow-[0_2px_0_0_#2B2118] flex items-center gap-0.5">
                    <span className="material-symbols-outlined text-[10px]">shield</span>
                    <span className="font-label-sm text-[10px] font-extrabold leading-none">MK.IV</span>
                  </div>
                </div>

                {/* Rank Title & Class */}
                <div className="flex-1 min-w-0 flex flex-col justify-center">
                  <span className="font-headline-md text-[20px] tracking-tight uppercase text-[#2B2118]">
                    LEVEL 0{profile.level}
                  </span>
                  <div className="mt-1 flex items-center gap-1.5 flex-wrap">
                    <PixelBadge variant="primary" icon="park">
                      {profile.preferred_play_style}
                    </PixelBadge>
                    <span className="font-label-sm text-[10px] text-[#6B5C4D] font-bold uppercase tracking-wider bg-[#FEEADC] border border-[#2B2118] px-1.5 py-0.5 rounded-xs">
                      TIER 2 SCOUT
                    </span>
                  </div>
                  <p className="font-body-sm text-[12px] text-[#6B5C4D] mt-2 line-clamp-2">
                    Calibrated for real-world foot travel, urban flora discovery, and off-grid wandering.
                  </p>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t-2 border-[#F8E5D6]">
                <XPBar currentXp={profile.xp} maxXp={1500} level={profile.level} />
              </div>
            </PixelCard>

            {/* QUICK GAME STATS ROW (3 Compact Tactile Cards) */}
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col items-center justify-center p-2.5 rounded-lg bg-[#FFFDF5] border-2 border-[#2B2118] shadow-[0_4px_0_0_#2B2118] text-center active:translate-y-0.5 transition-transform">
                <div className="w-8 h-8 rounded-md bg-[#6FAF5F] text-[#FFFDF5] border border-[#2B2118] flex items-center justify-center shadow-[0_2px_0_0_#2B2118] mb-1">
                  <span className="material-symbols-outlined text-[18px]">explore</span>
                </div>
                <span className="font-headline-md text-[18px] text-[#2B2118] leading-none mt-1">
                  {stats.total_quests_completed}
                </span>
                <span className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold tracking-tight mt-1">
                  QUESTS
                </span>
              </div>

              <div className="flex flex-col items-center justify-center p-2.5 rounded-lg bg-[#FFFDF5] border-2 border-[#2B2118] shadow-[0_4px_0_0_#2B2118] text-center active:translate-y-0.5 transition-transform">
                <div className="w-8 h-8 rounded-md bg-[#C49A2F] text-[#FFFDF5] border border-[#2B2118] flex items-center justify-center shadow-[0_2px_0_0_#2B2118] mb-1">
                  <span className="material-symbols-outlined text-[18px]">stars</span>
                </div>
                <span className="font-headline-md text-[18px] text-[#2B2118] leading-none mt-1">
                  {profile.xp.toLocaleString()}
                </span>
                <span className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold tracking-tight mt-1">
                  TOTAL XP
                </span>
              </div>

              <div className="flex flex-col items-center justify-center p-2.5 rounded-lg bg-[#FFFDF5] border-2 border-[#2B2118] shadow-[0_4px_0_0_#2B2118] text-center active:translate-y-0.5 transition-transform">
                <div className="w-8 h-8 rounded-md bg-[#FDC394] text-[#2B2118] border border-[#2B2118] flex items-center justify-center shadow-[0_2px_0_0_#2B2118] mb-1">
                  <span className="material-symbols-outlined text-[18px]">wb_sunny</span>
                </div>
                <span className="font-headline-md text-[18px] text-[#2B2118] leading-none mt-1">
                  4h 35m
                </span>
                <span className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold tracking-tight mt-1">
                  OUTSIDE
                </span>
              </div>
            </div>

            {/* AI GAME MASTER DISPATCH BUBBLE */}
            <GameMasterMessage
              message="Scout #4092, your moss perception streak is exceptional. Reach Level 05 to unlock the Riverbank audio synth frequency."
            />
          </div>

          {/* Right Column */}
          <div className="flex flex-col gap-4">
            {/* COLLECTIBLE ACHIEVEMENTS SECTION */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="font-headline-sm text-[16px] uppercase text-[#2B2118] tracking-tight">
                    ACHIEVEMENTS
                  </span>
                  <span className="font-label-md text-[11px] text-[#3F7042] font-extrabold bg-[#B0F49C] border border-[#2B2118] px-2 py-0.5 rounded-md shadow-[0_2px_0_0_#2B2118]">
                    4/16
                  </span>
                </div>
                <button
                  type="button"
                  className="font-label-md text-[12px] text-[#A9784F] hover:text-[#2B2118] uppercase tracking-wider font-bold flex items-center gap-0.5 cursor-pointer"
                >
                  <span>VIEW ALL</span>
                  <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                </button>
              </div>

              {/* 6 Badge Showcase Grid */}
              <div className="grid grid-cols-2 gap-3">
                {achievements.map((badge) => {
                  const isUnlocked = badge.status === 'UNLOCKED';
                  return (
                    <div
                      key={badge.id}
                      onClick={() => setSelectedBadge(badge)}
                      className={`p-3 rounded-lg border-2 border-[#2B2118] shadow-[0_4px_0_0_#2B2118] cursor-pointer hover:bg-[#FFF1E8] active:translate-y-0.5 transition-all flex flex-col justify-between ${
                        isUnlocked ? 'bg-[#FFFDF5]' : 'bg-[#E9D7C8] opacity-85'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div
                          className={`w-9 h-9 rounded-md border border-[#2B2118] flex items-center justify-center text-[18px] shadow-[0_2px_0_0_#2B2118] ${
                            isUnlocked ? 'bg-[#B0F49C]' : 'bg-[#E9D7C8]'
                          }`}
                        >
                          {isUnlocked ? badge.icon : '🔒'}
                        </div>
                        {badge.is_new ? (
                          <span className="font-label-sm text-[9px] uppercase font-extrabold text-[#3F7042] bg-[#B0F49C] border border-[#2B2118] px-1.5 py-0.5 rounded-xs">
                            NEW
                          </span>
                        ) : isUnlocked ? (
                          <span className="material-symbols-outlined text-[16px] text-[#C49A2F]">
                            check_circle
                          </span>
                        ) : (
                          <span className="font-label-sm text-[10px] text-[#6B5C4D] font-bold">???</span>
                        )}
                      </div>
                      <div className="mt-2">
                        <span className="font-headline-sm text-[14px] text-[#2B2118] tracking-tight block truncate">
                          {badge.name}
                        </span>
                        <p className="font-body-sm text-[11px] text-[#6B5C4D] line-clamp-1 mt-0.5">
                          {badge.description}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ADVENTURE LOG (RECENT EXPEDITIONS) */}
            <div className="flex flex-col gap-2 mt-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="font-headline-sm text-[16px] uppercase text-[#2B2118] tracking-tight">
                    ADVENTURE LOG
                  </span>
                  <span className="font-label-sm text-[10px] text-[#6B5C4D] font-bold">
                    RECENT EXPEDITIONS
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowEmptyLog(!showEmptyLog)}
                  className="px-2 py-1 rounded-sm bg-[#FEEADC] border border-[#2B2118] text-[#2B2118] font-label-sm text-[10px] uppercase tracking-wider font-bold shadow-[0_2px_0_0_#2B2118] active:translate-y-0.5 transition-all cursor-pointer"
                >
                  {showEmptyLog ? 'RESTORE LOG' : 'TOGGLE EMPTY'}
                </button>
              </div>

              {!showEmptyLog ? (
                <div className="flex flex-col gap-2">
                  {adventureLog.map((log) => (
                    <div
                      key={log.id}
                      className="p-3 rounded-lg bg-[#FFFDF5] border-2 border-[#2B2118] shadow-[0_4px_0_0_#2B2118] flex items-center justify-between hover:bg-[#FFF1E8] transition-colors cursor-pointer"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-md bg-[#B0F49C] border border-[#2B2118] shrink-0 flex items-center justify-center text-[20px] shadow-[0_2px_0_0_#2B2118]">
                          {log.icon}
                        </div>
                        <div className="flex flex-col min-w-0">
                          <span className="font-headline-sm text-[14px] text-[#2B2118] uppercase tracking-tight truncate">
                            {log.title}
                          </span>
                          <div className="flex items-center gap-1.5 flex-wrap mt-0.5">
                            <span className="font-label-sm text-[10px] text-[#3F7042] font-extrabold uppercase">
                              {log.play_style}
                            </span>
                            <span className="text-[#6B5C4D] text-[10px]">•</span>
                            <span className="font-body-sm text-[11px] text-[#6B5C4D]">
                              {log.completed_at} • {log.duration_minutes} min
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0 pl-2">
                        <span className="font-headline-sm text-[14px] text-[#C49A2F] uppercase font-bold">
                          +{log.xp_earned} XP
                        </span>
                        <span className="material-symbols-outlined text-[18px] text-[#6B5C4D]">
                          chevron_right
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <PixelCard shadowSize="md" className="flex flex-col items-center text-center py-6">
                  <div className="w-14 h-14 rounded-lg bg-[#F8E5D6] border-2 border-[#2B2118] flex items-center justify-center shadow-[0_3px_0_0_#2B2118] mb-2 text-[#6FAF5F]">
                    🗺️
                  </div>
                  <span className="font-headline-sm text-[16px] uppercase text-[#2B2118]">
                    YOUR ADVENTURE LOG IS EMPTY
                  </span>
                  <p className="font-body-md text-[13px] text-[#6B5C4D] mt-1 max-w-[280px]">
                    The physical world is brimming with unexplored nodes. Step outside.
                  </p>
                  <PixelButton variant="primary" className="mt-4" onClick={() => navigate('/quest/setup')}>
                    [ ENTER REALITY ]
                  </PixelButton>
                </PixelCard>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* BADGE INSPECTOR MODAL */}
      {selectedBadge && (
        <div
          className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-end justify-center p-0 sm:p-4"
          onClick={() => setSelectedBadge(null)}
        >
          <div
            className="w-full max-w-md bg-[#FFFDF5] rounded-t-2xl sm:rounded-2xl border-2 border-[#2B2118] shadow-[0_-6px_0_0_#2B2118] p-4 flex flex-col gap-3"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-10 h-1 rounded-full bg-[#C1C9B9] self-center mb-1" />
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-lg bg-[#B0F49C] border-2 border-[#2B2118] flex items-center justify-center text-[24px] shadow-[0_3px_0_0_#2B2118]">
                  {selectedBadge.status === 'UNLOCKED' ? selectedBadge.icon : '🔒'}
                </div>
                <div className="flex flex-col">
                  <span className="font-headline-md text-[18px] uppercase text-[#2B2118] tracking-tight">
                    {selectedBadge.name}
                  </span>
                  <span className="font-label-sm text-[10px] uppercase font-bold text-[#A9784F]">
                    {selectedBadge.rarity}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedBadge(null)}
                className="w-8 h-8 rounded-md bg-[#FEEADC] border border-[#2B2118] flex items-center justify-center text-[#2B2118] shadow-[0_2px_0_0_#2B2118]"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>

            <div className="p-3 rounded-lg bg-[#FFF1E8] border border-[#2B2118]">
              <p className="font-body-md text-[13px] text-[#2B2118]">
                {selectedBadge.description}
              </p>
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="font-label-sm text-[10px] uppercase font-extrabold text-[#3F7042] flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">verified</span>
                <span>RECORDED TO SCOUT DOSSIER</span>
              </span>
              <PixelButton
                variant="secondary"
                size="sm"
                disabled={selectedBadge.status === 'LOCKED'}
                onClick={() => setSelectedBadge(null)}
              >
                {selectedBadge.status === 'LOCKED' ? 'LOCKED' : 'EQUIP TITLE'}
              </PixelButton>
            </div>
          </div>
        </div>
      )}

      <BottomNavigation />
      <PixelSettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
};
