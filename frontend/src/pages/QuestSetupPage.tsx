import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';
import { BottomNavigation } from '../components/layout/BottomNavigation';
import { PixelCard } from '../components/pixel/PixelCard';
import { PixelButton } from '../components/pixel/PixelButton';
import { PixelBadge } from '../components/pixel/PixelBadge';
import { useGame } from '../context/GameContext';

export const QuestSetupPage: React.FC = () => {
  const navigate = useNavigate();
  const { generateQuest } = useGame();

  const [selectedDuration, setSelectedDuration] = useState<number>(20);
  const [selectedEnvironment, setSelectedEnvironment] = useState<string>('PARK');
  const [selectedPlayStyle, setSelectedPlayStyle] = useState<string>('EXPLORER');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  const durationOptions = [10, 20, 45, 60];
  const environmentOptions = [
    { id: 'PARK', label: 'PARK', icon: 'park' },
    { id: 'CAMPUS', label: 'CAMPUS', icon: 'school' },
    { id: 'CITY', label: 'CITY', icon: 'location_city' },
    { id: 'SURPRISE', label: 'SURPRISE', icon: 'casino' },
  ];

  const playStyleOptions = [
    { id: 'EXPLORER', label: 'EXPLORER', icon: 'explore', desc: 'Find forgotten corners and flora' },
    { id: 'DETECTIVE', label: 'DETECTIVE', icon: 'search', desc: 'Decode patterns and oddities' },
    { id: 'OBSERVER', label: 'OBSERVER', icon: 'visibility', desc: 'Listen to ambient city rhythms' },
    { id: 'ADVENTURER', label: 'ADVENTURER', icon: 'hiking', desc: 'Push distance and stamina' },
    { id: 'CHAOS', label: 'CHAOS', icon: 'bolt', desc: 'Unpredictable random prompts' },
  ];

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      await generateQuest({
        duration: selectedDuration,
        environment: selectedEnvironment,
        playStyle: selectedPlayStyle,
      });
      navigate('/quest/ready');
    } catch {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F3E8] relative pb-20 pt-16 md:pl-64 md:pb-0">
      <AppHeader title="QUEST SETUP" />

      <main className="flex-1 p-4 flex flex-col gap-5 max-w-[480px] md:max-w-3xl mx-auto w-full select-none">
        {/* Header Title Banner */}
        <div className="flex items-center justify-between">
          <div className="flex flex-col">
            <span className="font-headline-md text-[20px] uppercase text-[#2B2118] tracking-tight">
              CALIBRATE EXPEDITION
            </span>
            <span className="font-body-sm text-[12px] text-[#6B5C4D]">
              Configure parameters for the AI Game Master.
            </span>
          </div>
          <PixelBadge variant="sky" icon="tune">
            CONFIG
          </PixelBadge>
        </div>

        {/* SECTION 1: HOW MUCH TIME? */}
        <div className="flex flex-col gap-2">
          <label className="font-label-sm text-[12px] uppercase font-bold text-[#A9784F] tracking-wider flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px]">schedule</span>
            <span>1. HOW MUCH TIME?</span>
          </label>

          <div className="grid grid-cols-4 gap-2">
            {durationOptions.map((time) => {
              const isSelected = selectedDuration === time;
              return (
                <button
                  key={time}
                  type="button"
                  onClick={() => setSelectedDuration(time)}
                  className={`p-3 rounded-lg border-2 border-[#2B2118] font-headline-sm text-[14px] uppercase text-center transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#6FAF5F] text-[#FFFDF5] shadow-[0_4px_0_0_#3F7042] font-bold'
                      : 'bg-[#FFFDF5] text-[#2B2118] shadow-[0_2px_0_0_#2B2118] hover:bg-[#FFFDF5]/80'
                  }`}
                >
                  {time} MIN
                </button>
              );
            })}
          </div>
        </div>

        {/* SECTION 2: WHERE ARE YOU? */}
        <div className="flex flex-col gap-2">
          <label className="font-label-sm text-[12px] uppercase font-bold text-[#A9784F] tracking-wider flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px]">map</span>
            <span>2. WHERE ARE YOU?</span>
          </label>

          <div className="grid grid-cols-2 gap-2">
            {environmentOptions.map((env) => {
              const isSelected = selectedEnvironment === env.id;
              return (
                <button
                  key={env.id}
                  type="button"
                  onClick={() => setSelectedEnvironment(env.id)}
                  className={`p-3 rounded-lg border-2 border-[#2B2118] flex items-center gap-2 transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[#FFDCC2] text-[#2E1500] shadow-[0_4px_0_0_#A9784F] font-bold'
                      : 'bg-[#FFFDF5] text-[#2B2118] shadow-[0_2px_0_0_#2B2118] hover:bg-[#FFFDF5]/80'
                  }`}
                >
                  <span className="material-symbols-outlined text-[20px]">{env.icon}</span>
                  <span className="font-headline-sm text-[14px] uppercase">{env.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* SECTION 3: WHO ARE YOU TODAY? */}
        <div className="flex flex-col gap-2">
          <label className="font-label-sm text-[12px] uppercase font-bold text-[#A9784F] tracking-wider flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px]">person</span>
            <span>3. WHO ARE YOU TODAY?</span>
          </label>

          <div className="flex flex-col gap-2">
            {playStyleOptions.map((style) => {
              const isSelected = selectedPlayStyle === style.id;
              return (
                <div
                  key={style.id}
                  onClick={() => setSelectedPlayStyle(style.id)}
                  className={`p-3 rounded-lg border-2 border-[#2B2118] flex items-center justify-between cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-[#FFFDF5] shadow-[0_4px_0_0_#3F7042] border-[#3F7042]'
                      : 'bg-[#FFFDF5] shadow-[0_2px_0_0_#2B2118] hover:bg-[#FFFDF5]/90'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-9 h-9 rounded-md border-2 border-[#2B2118] flex items-center justify-center ${
                        isSelected ? 'bg-[#6FAF5F] text-[#FFFDF5]' : 'bg-[#F8E5D6] text-[#2B2118]'
                      }`}
                    >
                      <span className="material-symbols-outlined text-[20px]">{style.icon}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="font-headline-sm text-[14px] uppercase text-[#2B2118]">
                        {style.label}
                      </span>
                      <span className="font-body-sm text-[11px] text-[#6B5C4D]">
                        {style.desc}
                      </span>
                    </div>
                  </div>
                  <div
                    className={`w-5 h-5 rounded-full border-2 border-[#2B2118] flex items-center justify-center ${
                      isSelected ? 'bg-[#6FAF5F]' : 'bg-transparent'
                    }`}
                  >
                    {isSelected && <span className="w-2 h-2 rounded-full bg-[#FFFDF5]" />}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Action button */}
        <PixelCard shadowSize="md" className="mt-2 text-center">
          <PixelButton
            variant="primary"
            size="lg"
            fullWidth
            loading={isGenerating}
            onClick={handleGenerate}
          >
            [ GENERATE QUEST ]
          </PixelButton>
        </PixelCard>
      </main>

      <BottomNavigation />
    </div>
  );
};
