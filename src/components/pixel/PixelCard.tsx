import React from 'react';

interface PixelCardProps {
  children: React.ReactNode;
  className?: string;
  shadowSize?: 'sm' | 'md' | 'lg' | 'xl';
  showBevel?: boolean;
  onClick?: () => void;
}

export const PixelCard: React.FC<PixelCardProps> = ({
  children,
  className = '',
  shadowSize = 'md',
  showBevel = true,
  onClick,
}) => {
  const shadowClasses = {
    sm: 'shadow-[0_2px_0_0_#2B2118]',
    md: 'shadow-[0_4px_0_0_#2B2118]',
    lg: 'shadow-[0_6px_0_0_#2B2118]',
    xl: 'shadow-[0_8px_0_0_#2B2118]',
  }[shadowSize];

  return (
    <div
      onClick={onClick}
      className={`relative w-full rounded-xl bg-[#FFFDF5] border-2 border-[#2B2118] p-4 ${shadowClasses} overflow-hidden ${
        onClick ? 'cursor-pointer hover:bg-[#FFFDF5]/90 active:translate-y-0.5 transition-all' : ''
      } ${className}`}
    >
      {showBevel && (
        <div className="absolute inset-x-0 top-0 h-1 bg-[#FFF1E8] opacity-80 pointer-events-none" />
      )}
      {children}
    </div>
  );
};
