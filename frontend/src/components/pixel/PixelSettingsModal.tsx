import React, { useState } from 'react';
import { PixelButton } from './PixelButton';

interface PixelSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PixelSettingsModal: React.FC<PixelSettingsModalProps> = ({ isOpen, onClose }) => {
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [particlesEnabled, setParticlesEnabled] = useState(true);
  const [proximityEnabled, setProximityEnabled] = useState(true);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-end justify-center sm:items-center p-0 sm:p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-[#FFFDF5] rounded-t-2xl sm:rounded-2xl border-2 border-[#2B2118] shadow-[0_-6px_0_0_#2B2118] sm:shadow-[0_8px_0_0_#2B2118] p-5 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="w-10 h-1 rounded-full bg-[#C1C9B9] self-center mb-1 sm:hidden" />
        
        <div className="flex items-center justify-between pb-2 border-b-2 border-[#F8E5D6]">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[20px] text-[#A9784F]">tune</span>
            <span className="font-headline-md text-[20px] uppercase text-[#2B2118] tracking-tight">
              SYSTEM SETTINGS
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-md bg-[#FEEADC] border border-[#2B2118] flex items-center justify-center text-[#2B2118] shadow-[0_2px_0_0_#2B2118]"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        <div className="flex flex-col gap-3">
          {/* Sound FX */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-[#FFF1E8] border border-[#2B2118] shadow-[0_2px_0_0_#2B2118]">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-[22px] text-[#6FAF5F]">volume_up</span>
              <div className="flex flex-col">
                <span className="font-headline-sm text-[14px] text-[#2B2118] uppercase">8-BIT AUDIO CHIMES</span>
                <span className="font-body-sm text-[12px] text-[#6B5C4D]">Haptic chimes upon milestone trigger</span>
              </div>
            </div>
            <button
              onClick={() => setAudioEnabled(!audioEnabled)}
              className={`w-12 h-6 rounded-full p-0.5 border border-[#2B2118] transition-colors flex items-center ${
                audioEnabled ? 'bg-[#6FAF5F] justify-end' : 'bg-[#E9D7C8] justify-start'
              }`}
            >
              <span className="w-4 h-4 rounded-full bg-[#FFFDF5] border border-[#2B2118] shadow-[0_1px_0_0_#2B2118]" />
            </button>
          </div>

          {/* Emitters */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-[#FFF1E8] border border-[#2B2118] shadow-[0_2px_0_0_#2B2118]">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-[22px] text-[#E5B84B]">animation</span>
              <div className="flex flex-col">
                <span className="font-headline-sm text-[14px] text-[#2B2118] uppercase">PIXEL EMITTERS</span>
                <span className="font-body-sm text-[12px] text-[#6B5C4D]">Leaves, starbursts, and dust motes</span>
              </div>
            </div>
            <button
              onClick={() => setParticlesEnabled(!particlesEnabled)}
              className={`w-12 h-6 rounded-full p-0.5 border border-[#2B2118] transition-colors flex items-center ${
                particlesEnabled ? 'bg-[#6FAF5F] justify-end' : 'bg-[#E9D7C8] justify-start'
              }`}
            >
              <span className="w-4 h-4 rounded-full bg-[#FFFDF5] border border-[#2B2118] shadow-[0_1px_0_0_#2B2118]" />
            </button>
          </div>

          {/* Proximity */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-[#FFF1E8] border border-[#2B2118] shadow-[0_2px_0_0_#2B2118]">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-[22px] text-[#A9784F]">notifications_active</span>
              <div className="flex flex-col">
                <span className="font-headline-sm text-[14px] text-[#2B2118] uppercase">PROXIMITY PINGS</span>
                <span className="font-body-sm text-[12px] text-[#6B5C4D]">Alert when near uncharted waypoints</span>
              </div>
            </div>
            <button
              onClick={() => setProximityEnabled(!proximityEnabled)}
              className={`w-12 h-6 rounded-full p-0.5 border border-[#2B2118] transition-colors flex items-center ${
                proximityEnabled ? 'bg-[#6FAF5F] justify-end' : 'bg-[#E9D7C8] justify-start'
              }`}
            >
              <span className="w-4 h-4 rounded-full bg-[#FFFDF5] border border-[#2B2118] shadow-[0_1px_0_0_#2B2118]" />
            </button>
          </div>
        </div>

        <div className="pt-2 flex flex-col gap-2">
          <div className="flex items-center justify-between px-1">
            <span className="font-label-sm text-[10px] text-[#6B5C4D] uppercase font-bold">REALITY.EXE v2.4.0-PROD</span>
            <span className="font-label-sm text-[10px] text-[#3F7042] font-bold">BUILD 8904</span>
          </div>

          <PixelButton variant="danger" fullWidth onClick={onClose}>
            DISCONNECT (CLOSE SETTINGS)
          </PixelButton>
        </div>
      </div>
    </div>
  );
};
