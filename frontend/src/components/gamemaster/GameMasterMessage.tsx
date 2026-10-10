import React from 'react';

interface GameMasterMessageProps {
  message: string;
  title?: string;
  className?: string;
}

export const GameMasterMessage: React.FC<GameMasterMessageProps> = ({
  message,
  title = '[ AI GAME MASTER ]',
  className = '',
}) => {
  return (
    <div className={`relative p-4 rounded-xl bg-[#FFFDF5] border-2 border-[#2B2118] shadow-[0_6px_0_0_#2B2118] overflow-hidden ${className}`}>
      {/* Sky Blue Pixel Top Ridge Stripe */}
      <div className="absolute inset-x-0 top-0 h-1.5 bg-[#8FC8D8]" />

      <div className="flex items-start gap-3 pt-1">
        <div className="w-8 h-8 rounded-md bg-[#8FC8D8] border border-[#2B2118] text-[#2B2118] flex items-center justify-center font-bold shadow-[0_2px_0_0_#2B2118] shrink-0">
          <span className="material-symbols-outlined text-[18px]">smart_toy</span>
        </div>
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="font-label-sm text-[10px] font-extrabold uppercase text-[#A9784F] tracking-widest">
              {title}
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-[#6FAF5F] animate-pulse" />
          </div>
          <p className="font-body-md text-[14px] text-[#2B2118] mt-1 leading-relaxed">
            "{message}"
          </p>
        </div>
      </div>
    </div>
  );
};
