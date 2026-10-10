import { apiFetch } from './client';

export interface EvidenceUploadResponse {
  evidence_id: string;
  attempt_id: string;
  status: string;
  mime_type: string;
  size_bytes: number;
  checksum: string;
  created_at: string;
}

export interface VerificationResponse {
  verified: boolean;
  confidence: number;
  message: string;
  earned_xp?: number;
}

export const evidenceApi = {
  async upload(attemptId: string, file: File): Promise<EvidenceUploadResponse> {
    const formData = new FormData();
    formData.append('attempt_id', attemptId);
    formData.append('file', file);

    return apiFetch<EvidenceUploadResponse>('/evidence/upload', {
      method: 'POST',
      body: formData,
    });
  },

  async analyze(evidenceId: string): Promise<VerificationResponse> {
    return apiFetch<VerificationResponse>(`/evidence/${evidenceId}/analyze`, {
      method: 'POST',
    });
  }
};
