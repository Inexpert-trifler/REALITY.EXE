import React from 'react';

interface PixelBadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'xp' | 'sky' | 'dark' | 'outline';
  icon?: string;
  size?: 'sm' | 'md';
  className?: string;
}

export const PixelBadge: React.FC<PixelBadgeProps> = ({
  children,
  variant = 'primary',
  icon,
  size = 'md',
  className = '',
}) => {
  const sizeClasses = size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-[12px]';

  const variantClasses = {
    primary: 'bg-[#6FAF5F] text-[#FFFDF5] border border-[#2B2118] shadow-[0_2px_0_0_#2B2118]',
    secondary: 'bg-[#FFDCC2] text-[#2E1500] border border-[#2B2118] shadow-[0_2px_0_0_#2B2118]',
    xp: 'bg-[#C49A2F] text-[#473400] border border-[#2B2118] shadow-[0_2px_0_0_#2B2118]',
    sky: 'bg-[#8FC8D8] text-[#2B2118] border border-[#2B2118] shadow-[0_2px_0_0_#2B2118]',
    dark: 'bg-[#2B2118] text-[#FFFDF5] shadow-[0_2px_0_0_#2B2118]',
    outline: 'bg-[#EFE8D3] text-[#2B2118] border border-[#2B2118] shadow-[0_1.5px_0_0_#2B2118]',
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md font-label-md uppercase font-extrabold tracking-wider leading-none select-none ${sizeClasses} ${variantClasses} ${className}`}
    >
      {icon && <span className="material-symbols-outlined text-[14px]">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
