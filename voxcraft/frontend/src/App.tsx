import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { LandingOverlay } from "@/components/landing/LandingOverlay";
import { LicenseGate } from "@/components/license/LicenseGate";
import { TourOverlay } from "@/components/onboarding/TourOverlay";
import { QuickClipPage } from "@/pages/QuickClipPage";
import { AudiobookPage } from "@/pages/AudiobookPage";
import { StudioPage } from "@/pages/StudioPage";
import { ExportPage } from "@/pages/ExportPage";
import { URLReaderPage } from "@/pages/URLReaderPage";

export default function App() {
  return (
    <>
      {/* z-100: Landing shows every visit, slides away */}
      <LandingOverlay />
      {/* z-90: License gate shows if !licenseValid */}
      <LicenseGate />
      {/* z-80: Tour shows if !hasCompletedOnboarding */}
      <TourOverlay />
      {/* z-0: Always mounted behind overlays */}
      <AppShell>
        <Routes>
          <Route path="/" element={<QuickClipPage />} />
          <Route path="/url-reader" element={<URLReaderPage />} />
          <Route path="/studio" element={<StudioPage />} />
          <Route path="/audiobook" element={<AudiobookPage />} />
          <Route path="/export/:projectId" element={<ExportPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </>
  );
}
