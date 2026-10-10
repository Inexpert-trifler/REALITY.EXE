import React, { useRef } from 'react';
import { PixelButton } from '../pixel/PixelButton';

interface EvidenceUploaderProps {
  selectedFile: File | null;
  previewUrl: string | null;
  onFileSelect: (file: File | null) => void;
}

export const EvidenceUploader: React.FC<EvidenceUploaderProps> = ({
  selectedFile,
  previewUrl,
  onFileSelect,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      onFileSelect(file);
    }
  };

  return (
    <div className="flex flex-col gap-3 w-full">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="image/*"
        className="hidden"
      />

      {previewUrl ? (
        <div className="relative w-full rounded-xl bg-[#FFFDF5] border-2 border-[#2B2118] p-3 shadow-[0_4px_0_0_#2B2118] flex flex-col items-center gap-3">
          <div className="relative w-full h-48 rounded-lg overflow-hidden border-2 border-[#2B2118] bg-[#2B2118]">
            <img
              src={previewUrl}
              alt="Expedition Evidence Preview"
              className="w-full h-full object-cover"
            />
            <div className="absolute top-2 left-2 bg-[#6FAF5F] text-[#FFFDF5] text-[10px] font-bold px-2 py-0.5 rounded border border-[#2B2118] shadow-[0_2px_0_0_#2B2118] uppercase">
              EVIDENCE ATTACHED
            </div>
          </div>
          <div className="flex items-center justify-between w-full">
            <span className="font-label-sm text-[10px] text-[#6B5C4D] font-bold truncate max-w-[200px]">
              {selectedFile?.name || 'photo_evidence.jpg'}
            </span>
            <PixelButton
              variant="danger"
              size="sm"
              onClick={() => onFileSelect(null)}
            >
              REMOVE PHOTO
            </PixelButton>
          </div>
        </div>
      ) : (
        <div
          onClick={() => fileInputRef.current?.click()}
          className="w-full p-6 rounded-xl bg-[#FFFDF5] border-2 border-dashed border-[#A9784F] hover:border-[#6FAF5F] shadow-[0_4px_0_0_#2B2118] flex flex-col items-center justify-center text-center cursor-pointer transition-all active:translate-y-0.5"
        >
          <div className="w-12 h-12 rounded-lg bg-[#FFDCC2] border-2 border-[#2B2118] flex items-center justify-center text-[#2B2118] mb-2 shadow-[0_2px_0_0_#2B2118]">
            <span className="material-symbols-outlined text-[24px]">add_a_photo</span>
          </div>
          <span className="font-headline-sm text-[16px] uppercase tracking-tight text-[#2B2118]">
            ADD EXPEDITION PHOTO
          </span>
          <span className="font-body-sm text-[12px] text-[#6B5C4D] mt-1 max-w-[240px]">
            Optional photo evidence to verify objective completion with the Game Master.
          </span>
        </div>
      )}
    </div>
  );
};
