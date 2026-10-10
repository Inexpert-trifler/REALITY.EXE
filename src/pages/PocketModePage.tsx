import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';
import { PixelCard } from '../components/pixel/PixelCard';
import { PixelButton } from '../components/pixel/PixelButton';
import { PixelBadge } from '../components/pixel/PixelBadge';
import { useGame } from '../context/GameContext';

export const PocketModePage: React.FC = () => {
  const navigate = useNavigate();
  const { currentQuest, enterPocketMode, returnFromPocket } = useGame();

  const durationMinutes = currentQuest?.duration_minutes || 20;
  const [secondsRemaining, setSecondsRemaining] = useState<number>(durationMinutes * 60);

  useEffect(() => {
    enterPocketMode();
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setSecondsRemaining((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const handleReturn = async () => {
    await returnFromPocket();
    navigate('/quest/welcome');
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F3E8] relative select-none md:pl-64">
      {/* Focused Gameplay Header */}
      <AppHeader variant="focused" title="QUEST ACTIVE" />

      <main className="flex-1 p-6 pt-20 pb-8 flex flex-col justify-between items-center max-w-[480px] mx-auto w-full text-center">
        {/* Top Status */}
        <div className="flex flex-col items-center gap-2 mt-4">
          <PixelBadge variant="primary" icon="sensors" size="md">
            POCKET SENSOR ACTIVE
          </PixelBadge>
          <span className="font-label-sm text-[12px] text-[#A9784F] uppercase font-bold tracking-widest mt-1">
            SECTOR-04 // AUDIO GUIDE SYNTH
          </span>
        </div>

        {/* Center Graphic & Countdown */}
        <div className="flex flex-col items-center gap-6 my-auto w-full">
          {/* Animated Glowing Phone Silhouette */}
          <div className="relative">
            <div className="w-28 h-28 rounded-2xl bg-[#6FAF5F] border-4 border-[#2B2118] shadow-[0_8px_0_0_#3F7042] flex items-center justify-center animate-pulse">
              <span className="material-symbols-outlined text-[56px] text-[#FFFDF5]">
                phonelink_off
              </span>
            </div>
            <div className="absolute -bottom-2 -right-2 w-8 h-8 rounded-md bg-[#E5B84B] border-2 border-[#2B2118] flex items-center justify-center font-bold text-[14px]">
              🔒
            </div>
          </div>

          <div className="flex flex-col gap-2 max-w-[320px]">
            <h1 className="font-headline-lg text-[26px] uppercase text-[#2B2118] tracking-tight">
              PUT THE PHONE AWAY.
            </h1>
            <p className="font-body-md text-[15px] text-[#6B5C4D] leading-relaxed">
              Your adventure is happening out there in reality. Keep walking and observe the world.
            </p>
          </div>

          {/* Large Retro Timer Card */}
          <PixelCard shadowSize="lg" className="w-full max-w-[300px] bg-[#FFFDF5] text-center py-4">
            <span className="font-label-sm text-[10px] text-[#A9784F] uppercase font-bold tracking-wider block mb-1">
              ESTIMATED TIME REMAINING
            </span>
            <span className="font-headline-lg text-[42px] text-[#2B2118] tracking-tight font-bold block leading-none">
              {formatTime(secondsRemaining)}
            </span>
            <span className="font-body-sm text-[11px] text-[#3F7042] uppercase font-bold tracking-wider mt-2 block">
              QUEST: {currentQuest?.title || 'THE HIDDEN PATCH'}
            </span>
          </PixelCard>
        </div>

        {/* Bottom CTA */}
        <div className="w-full flex flex-col gap-3 mt-6">
          <PixelCard shadowSize="sm" className="bg-[#FFF1E8] text-center py-2.5">
            <p className="font-body-sm text-[12px] text-[#6B5C4D]">
              Finished your walk? Click below when you return.
            </p>
          </PixelCard>

          <PixelButton
            variant="xp"
            size="lg"
            fullWidth
            onClick={handleReturn}
          >
            [ I'M BACK ]
          </PixelButton>
        </div>
      </main>
    </div>
  );
};
