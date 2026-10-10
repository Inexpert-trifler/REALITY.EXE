import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';
import { PixelCard } from '../components/pixel/PixelCard';
import { PixelButton } from '../components/pixel/PixelButton';
import { PixelBadge } from '../components/pixel/PixelBadge';
import { PixelLoader } from '../components/pixel/PixelLoader';
import { useGame } from '../context/GameContext';

export const VerificationPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentQuest, verificationStatus, verificationMessage, submitQuest } = useGame();

  useEffect(() => {
    if (verificationStatus === 'SUCCESS') {
      const timer = setTimeout(() => {
        navigate('/quest/complete');
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [verificationStatus, navigate]);

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F3E8] relative justify-between p-4 pt-20 pb-8 max-w-[480px] md:max-w-3xl md:pl-[17rem] mx-auto w-full select-none">
      <AppHeader variant="focused" title="VERIFICATION" />

      <div className="flex flex-col items-center justify-center my-auto w-full gap-6 text-center">
        {verificationStatus === 'VERIFYING' && (
          <PixelCard shadowSize="lg" className="w-full flex flex-col items-center py-8">
            <PixelLoader message="GAME MASTER IS CHECKING..." />
            <span className="font-label-sm text-[11px] text-[#A9784F] uppercase font-bold tracking-widest mt-4">
              ANALYZING EXPEDITION DATA
            </span>
            <p className="font-body-sm text-[13px] text-[#6B5C4D] mt-1">
              Quest: {currentQuest?.title || 'THE HIDDEN PATCH'}
            </p>
          </PixelCard>
        )}

        {verificationStatus === 'SUCCESS' && (
          <PixelCard shadowSize="lg" className="w-full flex flex-col items-center py-8 bg-[#FFFDF5]">
            <div className="w-16 h-16 rounded-xl bg-[#6FAF5F] border-2 border-[#2B2118] text-[#FFFDF5] flex items-center justify-center text-[32px] shadow-[0_4px_0_0_#3F7042] mb-3 animate-bounce">
              ✓
            </div>
            <PixelBadge variant="primary" size="md" icon="verified" className="mb-2">
              VERIFIED SUCCESSFUL
            </PixelBadge>
            <h1 className="font-headline-lg text-[22px] uppercase text-[#2B2118]">
              EXPEDITION APPROVED!
            </h1>
            <p className="font-body-md text-[14px] text-[#3F7042] font-bold mt-1">
              {verificationMessage}
            </p>
          </PixelCard>
        )}

        {(verificationStatus === 'UNCERTAIN' || verificationStatus === 'ERROR') && (
          <PixelCard shadowSize="lg" className="w-full flex flex-col items-center py-6 bg-[#FFFDF5]">
            <div className="w-14 h-14 rounded-xl bg-[#FFDCC2] border-2 border-[#2B2118] text-[#2B2118] flex items-center justify-center text-[28px] shadow-[0_4px_0_0_#A9784F] mb-3">
              🤔
            </div>
            <PixelBadge variant="secondary" size="md" className="mb-2">
              NEED ANOTHER LOOK
            </PixelBadge>
            <h1 className="font-headline-lg text-[20px] uppercase text-[#2B2118]">
              VERIFICATION UNCERTAIN
            </h1>
            <p className="font-body-sm text-[13px] text-[#6B5C4D] max-w-[280px] my-3">
              {verificationMessage || "Hmm. The Game Master needs a clearer view of your finding."}
            </p>
            <div className="flex gap-2 w-full mt-2">
              <PixelButton variant="primary" fullWidth onClick={() => submitQuest()}>
                TRY AGAIN
              </PixelButton>
              <PixelButton variant="ghost" fullWidth onClick={() => navigate('/quest/complete')}>
                SKIP TO RESULTS
              </PixelButton>
            </div>
          </PixelCard>
        )}
      </div>
    </div>
  );
};
