import React from 'react';

interface PixelLoaderProps {
  message?: string;
}

export const PixelLoader: React.FC<PixelLoaderProps> = ({ message = 'GAME MASTER THINKING...' }) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center">
      <div className="relative w-16 h-16 mb-4">
        {/* Animated Pixel Grid Spinning Box */}
        <div className="w-16 h-16 bg-[#6FAF5F] border-4 border-[#2B2118] rounded-md shadow-[0_6px_0_0_#2B2118] animate-bounce flex items-center justify-center">
          <div className="w-6 h-6 bg-[#E5B84B] border-2 border-[#2B2118] rounded-xs animate-pulse" />
        </div>
        {/* Shadow floor */}
        <div className="w-12 h-2 bg-[#2B2118]/20 rounded-full mx-auto mt-2 blur-xs animate-pulse" />
      </div>
      <span className="font-headline-sm text-[16px] uppercase tracking-wider text-[#2B2118]">
        {message}
      </span>
    </div>
  );
};
