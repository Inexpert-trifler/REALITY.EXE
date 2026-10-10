import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AppHeader } from '../components/layout/AppHeader';
import { BottomNavigation } from '../components/layout/BottomNavigation';
import { PixelCard } from '../components/pixel/PixelCard';
import { PixelButton } from '../components/pixel/PixelButton';
import { PixelBadge } from '../components/pixel/PixelBadge';
import { EvidenceUploader } from '../components/evidence/EvidenceUploader';
import { GameMasterMessage } from '../components/gamemaster/GameMasterMessage';
import { useGame } from '../context/GameContext';

export const WelcomeBackPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentQuest, selectedEvidenceFile, evidencePreviewUrl, setEvidenceFile, submitQuest } = useGame();

  const handleSubmit = async () => {
    submitQuest();
    navigate('/quest/verify');
  };

  const handleSkip = () => {
    setEvidenceFile(null);
    submitQuest();
    navigate('/quest/verify');
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#F7F3E8] relative pb-20 pt-16 select-none md:pl-64 md:pb-0">
      <AppHeader title="WELCOME BACK" />

      <main className="flex-1 p-4 flex flex-col gap-4 max-w-[480px] md:max-w-3xl mx-auto w-full">
        {/* Top Header Title */}
        <div className="flex items-center justify-between">
          <div className="flex flex-col">
            <h1 className="font-headline-lg text-[22px] uppercase text-[#2B2118] tracking-tight">
              WELCOME BACK!
            </h1>
            <span className="font-body-sm text-[12px] text-[#6B5C4D]">
              Your expedition step counts and timing have been logged.
            </span>
          </div>
          <PixelBadge variant="sky" icon="assignment_turned_in">
            RETURNED
          </PixelBadge>
        </div>

        {/* Quest Summary Card */}
        <PixelCard shadowSize="md" className="flex flex-col gap-2">
          <div className="flex items-center justify-between pb-2 border-b-2 border-[#F8E5D6]">
            <span className="font-headline-sm text-[14px] uppercase text-[#2B2118]">
              {currentQuest?.title || 'THE HIDDEN PATCH'}
            </span>
            <PixelBadge variant="secondary" size="sm">
              PENDING VERIFICATION
            </PixelBadge>
          </div>

          <p className="font-body-sm text-[13px] text-[#6B5C4D]">
            {currentQuest?.brief || 'Expedition objectives completed.'}
          </p>

          <div className="flex items-center gap-2 mt-1">
            <PixelBadge variant="outline" size="sm" icon="schedule">
              {currentQuest?.duration_minutes || 20} MIN COMPLETED
            </PixelBadge>
            <PixelBadge variant="xp" size="sm" icon="stars">
              +{currentQuest?.xp_reward || 250} XP
            </PixelBadge>
          </div>
        </PixelCard>

        {/* Evidence Photo Section */}
        <div className="flex flex-col gap-2">
          <span className="font-label-sm text-[11px] uppercase font-bold text-[#A9784F] tracking-wider flex items-center gap-1.5">
            <span className="material-symbols-outlined text-[16px]">photo_camera</span>
            <span>EXPEDITION EVIDENCE (OPTIONAL)</span>
          </span>

          <EvidenceUploader
            selectedFile={selectedEvidenceFile}
            previewUrl={evidencePreviewUrl}
            onFileSelect={setEvidenceFile}
          />
        </div>

        {/* AI Game Master Guidance */}
        <GameMasterMessage
          message="Attach a photo if you captured your objective. If you just observed it with your own eyes, you can skip and submit directly!"
        />

        {/* Action Buttons */}
        <div className="flex flex-col gap-2 mt-2">
          <PixelButton variant="primary" size="lg" fullWidth onClick={handleSubmit}>
            [ SUBMIT QUEST ]
          </PixelButton>
          <PixelButton variant="ghost" size="md" fullWidth onClick={handleSkip}>
            SKIP EVIDENCE & SUBMIT
          </PixelButton>
        </div>
      </main>

      <BottomNavigation />
    </div>
  );
};
