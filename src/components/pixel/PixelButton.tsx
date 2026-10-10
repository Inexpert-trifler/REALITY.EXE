import React from 'react';

interface PixelButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'xp' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  disabled?: boolean;
  loading?: boolean;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
}

export const PixelButton: React.FC<PixelButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  disabled = false,
  loading = false,
  onClick,
  type = 'button',
  className = '',
}) => {
  const baseClasses =
    'relative inline-flex items-center justify-center font-headline-sm uppercase tracking-wider border-2 border-[#2B2118] rounded-lg transition-all cursor-pointer select-none font-bold';

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-[12px] min-h-[36px]',
    md: 'px-4 py-2.5 text-[14px] min-h-[44px]',
    lg: 'px-6 py-3.5 text-[16px] min-h-[52px]',
  }[size];

  const variantClasses = {
    primary:
      'bg-[#6FAF5F] text-[#FFFDF5] shadow-[0_4px_0_0_#3F7042] hover:bg-[#6FAF5F]/90 active:translate-y-[4px] active:shadow-none',
    secondary:
      'bg-[#D8B892] text-[#2B2118] shadow-[0_4px_0_0_#A9784F] hover:bg-[#D8B892]/90 active:translate-y-[4px] active:shadow-none',
    xp:
      'bg-[#E5B84B] text-[#2B2118] shadow-[0_4px_0_0_#B88526] hover:bg-[#E5B84B]/90 active:translate-y-[4px] active:shadow-none',
    ghost:
      'bg-[#F8E5D6] text-[#2B2118] shadow-[0_3px_0_0_#2B2118] hover:bg-[#F2DFD1] active:translate-y-[3px] active:shadow-none',
    danger:
      'bg-[#FFDAD6] text-[#93000A] shadow-[0_4px_0_0_#93000A] hover:bg-[#FFDAD6]/90 active:translate-y-[4px] active:shadow-none',
  }[variant];

  const disabledClasses = disabled || loading ? 'opacity-50 pointer-events-none' : '';
  const widthClasses = fullWidth ? 'w-full' : '';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseClasses} ${sizeClasses} ${variantClasses} ${widthClasses} ${disabledClasses} ${className}`}
    >
      {loading ? (
        <span className="inline-flex items-center gap-2">
          <span className="w-4 h-4 rounded-xs bg-current animate-spin" />
          <span>LOADING...</span>
        </span>
      ) : (
        children
      )}
    </button>
  );
};
