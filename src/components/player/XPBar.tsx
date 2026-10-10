import React from 'react';

interface XPBarProps {
  currentXp: number;
  maxXp: number;
  level: number;
  nextLevelName?: string;
  className?: string;
}

export const XPBar: React.FC<XPBarProps> = ({
  currentXp,
  maxXp,
  level,
  nextLevelName = 'VANGUARD',
  className = '',
}) => {
  const percentage = Math.min(100, Math.max(0, (currentXp / maxXp) * 100));
  const filledBlocks = Math.round((percentage / 100) * 10);
  const xpNeeded = Math.max(0, maxXp - currentXp);

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <span className="text-[#E5B84B] font-headline-sm text-[16px]">⭐</span>
          <span className="font-headline-sm text-[16px] text-[#E5B84B] uppercase tracking-tight font-bold">
            {currentXp.toLocaleString()} XP
          </span>
        </div>
        <span className="font-label-md text-[12px] text-[#6B5C4D] font-bold">
          {currentXp} / {maxXp}{' '}
          <span className="text-[#3F7042] font-bold">(+{xpNeeded} TO LVL {String(level + 1).padStart(2, '0')})</span>
        </span>
      </div>

      {/* Segmented 10-Block Pixel Progress Trough */}
      <div className="relative w-full h-5 rounded-md bg-[#EFE8D3] border-2 border-[#2B2118] p-0.5 shadow-[inset_0_2px_0_0_rgba(43,33,24,0.15)] flex gap-1">
        {Array.from({ length: 10 }).map((_, index) => (
          <div
            key={index}
            className={`flex-1 h-full rounded-xs transition-all duration-300 ${
              index < filledBlocks
                ? 'bg-[#E5B84B] border border-[#2B2118] shadow-[0_1px_0_0_#2B2118]'
                : 'bg-[#F2DFD1]/60'
            }`}
          />
        ))}
      </div>

      <div className="flex items-center justify-between text-[#6B5C4D] pt-0.5">
        <span className="font-label-sm text-[10px] uppercase font-bold tracking-wider">
          LVL {String(level).padStart(2, '0')} SCOUT
        </span>
        <span className="font-label-sm text-[10px] uppercase font-bold tracking-wider text-[#A9784F]">
          LVL {String(level + 1).padStart(2, '0')}: {nextLevelName} ➔
        </span>
      </div>
    </div>
  );
};
