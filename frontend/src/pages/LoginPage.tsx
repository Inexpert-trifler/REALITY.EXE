import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { PixelCard } from '../components/pixel/PixelCard';
import { PixelButton } from '../components/pixel/PixelButton';

export const LoginPage: React.FC = () => {
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password, displayName || `Scout_${Math.floor(Math.random() * 1000)}`);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F3E8] relative justify-center items-center p-4 select-none">
      <main className="w-full max-w-[400px]">
        <div className="text-center mb-8 flex flex-col items-center">
           <div className="w-16 h-16 rounded-xl bg-[#6FAF5F] border-2 border-[#2B2118] shadow-[0_4px_0_0_#2B2118] flex items-center justify-center mb-4">
             <span className="material-symbols-outlined text-[#FFFDF5] text-[32px]">public</span>
           </div>
           <h1 className="font-headline-lg text-[32px] text-[#2B2118] uppercase tracking-tight">REALITY.EXE</h1>
           <p className="font-body-md text-[#6B5C4D]">Reclaim your attention.</p>
        </div>

        <PixelCard shadowSize="lg" className="flex flex-col gap-4">
          <h2 className="font-headline-sm text-[18px] text-[#2B2118] uppercase text-center border-b-2 border-[#F8E5D6] pb-2 mb-2">
            {isLogin ? 'SYSTEM LOGIN' : 'SCOUT REGISTRATION'}
          </h2>

          {error && (
            <div className="p-2 bg-[#FFDCC2] border border-[#2B2118] text-[#2E1500] font-label-sm text-[10px] text-center uppercase tracking-wider rounded-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {!isLogin && (
              <div className="flex flex-col gap-1.5">
                <label className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold tracking-wider">
                  DISPLAY NAME
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="p-2 bg-[#FFFDF5] border-2 border-[#2B2118] rounded-md font-body-md text-[14px] text-[#2B2118] focus:outline-none focus:border-[#6FAF5F]"
                  placeholder="Scout Name"
                />
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold tracking-wider">
                EMAIL
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="p-2 bg-[#FFFDF5] border-2 border-[#2B2118] rounded-md font-body-md text-[14px] text-[#2B2118] focus:outline-none focus:border-[#6FAF5F]"
                placeholder="scout@reality.exe"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold tracking-wider">
                PASSWORD
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="p-2 bg-[#FFFDF5] border-2 border-[#2B2118] rounded-md font-body-md text-[14px] text-[#2B2118] focus:outline-none focus:border-[#6FAF5F]"
                placeholder="••••••••"
              />
            </div>

            <PixelButton
              variant="primary"
              size="lg"
              fullWidth
              loading={loading}
              className="mt-2"
              type="submit"
            >
              {isLogin ? '[ INITIALIZE ]' : '[ JOIN NETWORK ]'}
            </PixelButton>
          </form>

          <div className="text-center mt-2 border-t-2 border-[#F8E5D6] pt-3">
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="font-label-sm text-[11px] text-[#A9784F] hover:text-[#2B2118] uppercase tracking-wider font-bold transition-colors cursor-pointer"
            >
              {isLogin ? 'CREATE NEW SCOUT PROFILE' : 'EXISTING SCOUTS LOGIN HERE'}
            </button>
          </div>
        </PixelCard>
      </main>
    </div>
  );
};
