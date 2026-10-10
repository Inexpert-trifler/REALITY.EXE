import React from 'react';

interface AppShellProps {
  children: React.ReactNode;
  hideHeader?: boolean;
  hideNav?: boolean;
  headerVariant?: 'normal' | 'focused';
  headerTitle?: string;
  onOpenSettings?: () => void;
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
}) => {
  return (
    <div className="min-h-screen w-full bg-[#F7F3E8] relative flex flex-col overflow-x-hidden selection:bg-[#6FAF5F] selection:text-[#FFFDF5]">
      {children}
    </div>
  );
};
