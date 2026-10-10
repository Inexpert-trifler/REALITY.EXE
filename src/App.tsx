import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { GameProvider } from './context/GameContext';
import { AppShell } from './components/layout/AppShell';

import { HomePage } from './pages/HomePage';
import { QuestSetupPage } from './pages/QuestSetupPage';
import { QuestReadyPage } from './pages/QuestReadyPage';
import { PocketModePage } from './pages/PocketModePage';
import { WelcomeBackPage } from './pages/WelcomeBackPage';
import { VerificationPage } from './pages/VerificationPage';
import { QuestCompletePage } from './pages/QuestCompletePage';
import { ProfilePage } from './pages/ProfilePage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <GameProvider>
        <AppShell>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/quest/setup" element={<QuestSetupPage />} />
            <Route path="/quest/ready" element={<QuestReadyPage />} />
            <Route path="/quest/pocket" element={<PocketModePage />} />
            <Route path="/quest/return" element={<WelcomeBackPage />} />
            <Route path="/quest/welcome" element={<WelcomeBackPage />} />
            <Route path="/quest/verify" element={<VerificationPage />} />
            <Route path="/quest/complete" element={<QuestCompletePage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppShell>
      </GameProvider>
    </BrowserRouter>
  );
};

export default App;
