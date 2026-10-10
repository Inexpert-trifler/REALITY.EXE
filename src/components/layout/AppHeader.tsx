import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useGame } from '../../context/GameContext';

interface AppHeaderProps {
  variant?: 'normal' | 'focused';
  title?: string;
  onOpenSettings?: () => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  variant = 'normal',
  title = 'REALITY.EXE',
  onOpenSettings,
}) => {
  const navigate = useNavigate();
  const { profile } = useGame();

  if (variant === 'focused') {
    return (
      <header className="fixed top-0 left-0 right-0 z-50 bg-[#F7F3E8]/90 backdrop-blur-md border-b-2 border-[#2B2118] px-4 h-14 flex items-center justify-between shadow-[0_2px_0_0_#2B2118] md:left-64">
        <div className="flex items-center gap-2">
          {/* Pixel Leaf SVG Logo */}
          <div className="w-6 h-6 bg-[#6FAF5F] rounded-xs border-2 border-[#2B2118] flex items-center justify-center text-[12px] text-[#FFFDF5] font-bold shadow-[0_1px_0_0_#2B2118]">
            🌿
          </div>
          <span className="font-headline-sm text-[16px] uppercase tracking-tight text-[#2B2118]">
            {title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#6FAF5F] animate-pulse"></span>
          <span className="font-label-sm text-[10px] text-[#3F7042] uppercase font-bold tracking-wider">
            QUEST ACTIVE
          </span>
        </div>
      </header>
    );
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#F7F3E8]/85 backdrop-blur-xl border-b-2 border-[#2B2118]/20 px-4 h-16 flex items-center justify-between shadow-[0_2px_8px_rgba(0,0,0,0.04)] md:left-64">
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
        {/* Pixel Leaf Logo Icon */}
        <div className="w-8 h-8 rounded-md bg-[#6FAF5F] border-2 border-[#2B2118] flex items-center justify-center text-[16px] text-[#FFFDF5] font-bold shadow-[0_2px_0_0_#3F7042]">
          🌱
        </div>
        <div className="flex flex-col">
          <span className="font-headline-sm text-[18px] uppercase tracking-tight text-[#2B2118] leading-none">
            REALITY.EXE
          </span>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="w-2 h-2 rounded-full bg-[#6FAF5F] animate-pulse"></span>
            <span className="font-label-sm text-[10px] text-[#3F7042] uppercase font-bold tracking-wider">
              WORLD: ONLINE
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {onOpenSettings && (
          <button
            onClick={onOpenSettings}
            className="w-10 h-10 rounded-md bg-[#F8E5D6] border-2 border-[#2B2118] flex items-center justify-center text-[#2B2118] hover:bg-[#F2DFD1] active:translate-y-0.5 shadow-[0_2px_0_0_#2B2118] transition-all"
            title="System Settings"
          >
            <span className="material-symbols-outlined text-[20px]">settings</span>
          </button>
        )}
        <div
          onClick={() => navigate('/profile')}
          className="w-9 h-9 rounded-full bg-[#6FAF5F] border-2 border-[#2B2118] shadow-[0_2px_0_0_#2B2118] overflow-hidden cursor-pointer flex items-center justify-center text-[14px] font-bold text-[#FFFDF5]"
          title="Scout Profile"
        >
          <span className="material-symbols-outlined text-[20px]">person</span>
        </div>
      </div>
    </header>
  );
};
