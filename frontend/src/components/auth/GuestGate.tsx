import React, { useEffect, useState } from 'react';
import { apiFetch } from '../../services/api/client';

/**
 * GuestGate silently authenticates the user as a guest so they can bypass login screens
 * while still satisfying the backend's token requirements.
 */
export const GuestGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializeGuest = async () => {
      const token = localStorage.getItem('reality_auth_token');
      if (token) {
        setIsAuthenticated(true);
        return;
      }

      try {
        const guestId = Math.random().toString(36).substring(2, 10);
        const username = `player_${guestId}`;
        const email = `${username}@guest.reality.exe`;
        const password = `GuestPass${guestId}1!`; // Satisfy backend rules

        const response = await apiFetch<any>('/auth/register', {
          method: 'POST',
          body: JSON.stringify({
            username,
            email,
            password,
            display_name: `Guest ${guestId.substring(0, 4)}`,
          }),
        });

        if (response.access_token) {
          localStorage.setItem('reality_auth_token', response.access_token);
          setIsAuthenticated(true);
        } else {
          throw new Error('No access token returned during guest registration.');
        }
      } catch (err: any) {
        console.warn('Backend guest registration call failed, falling back to local guest session:', err);
        // Fallback to local guest token so player is not blocked by cold-starts or network glitches
        const localGuestToken = `guest_offline_${Math.random().toString(36).substring(2, 10)}`;
        localStorage.setItem('reality_auth_token', localGuestToken);
        setIsAuthenticated(true);
      }
    };

    initializeGuest();
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-neutral-900 flex items-center justify-center text-white">
        <div className="bg-neutral-800 p-8 rounded-xl border border-red-500 max-w-md text-center">
          <h2 className="text-xl text-red-400 mb-4 font-orbitron">Connection Error</h2>
          <p className="text-neutral-300">{error}</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-neutral-900 flex flex-col items-center justify-center text-white font-orbitron">
        <div className="w-16 h-16 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mb-6"></div>
        <div className="text-primary-400 animate-pulse text-lg tracking-widest">INITIALIZING LINK...</div>
      </div>
    );
  }

  return <>{children}</>;
};
