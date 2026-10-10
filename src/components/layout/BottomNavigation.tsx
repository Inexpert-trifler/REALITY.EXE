import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

export const BottomNavigation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const navItems = [
    { path: '/', label: 'HOME', icon: 'home' },
    { path: '/quest/setup', label: 'QUEST', icon: 'swords', activePaths: ['/quest/setup', '/quest/ready', '/quest/welcome', '/quest/complete'] },
    { path: '/profile', label: 'PROFILE', icon: 'person' },
  ];

  const isPathActive = (item: typeof navItems[0]) => {
    if (location.pathname === item.path) return true;
    if (item.activePaths?.includes(location.pathname)) return true;
    return false;
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-[#F7F3E8]/90 backdrop-blur-xl border-t-2 border-[#2B2118] pb-safe shadow-[0_-2px_12px_rgba(0,0,0,0.06)] md:top-0 md:right-auto md:w-64 md:border-t-0 md:border-r-2 md:pb-0 md:shadow-[2px_0_12px_rgba(0,0,0,0.06)]">
      <div className="max-w-[480px] mx-auto flex items-center justify-around h-16 px-4 md:max-w-none md:flex-col md:h-full md:justify-start md:pt-24 md:gap-4 md:w-full">
        {navItems.map((item) => {
          const active = isPathActive(item);
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`flex flex-col md:flex-row md:justify-start md:w-full md:px-6 md:py-3 md:rounded-lg items-center justify-center min-w-[64px] py-1 transition-transform active:translate-y-0.5 ${
                active ? 'text-[#6FAF5F] md:bg-[#6FAF5F]/10' : 'text-[#6B5C4D] hover:text-[#2B2118]'
              }`}
            >
              <div
                className={`w-9 h-8 rounded-md flex items-center justify-center transition-all md:w-10 md:h-10 md:mr-3 ${
                  active ? 'bg-[#6FAF5F]/15 border-2 border-[#6FAF5F]' : ''
                }`}
              >
                <span className="material-symbols-outlined text-[24px]">
                  {item.icon}
                </span>
              </div>
              <span
                className={`font-label-sm text-[10px] tracking-wider uppercase mt-0.5 md:mt-0 md:text-[14px] ${
                  active ? 'font-extrabold text-[#3F7042]' : 'font-bold'
                }`}
              >
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
