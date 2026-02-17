import { useState, useCallback, useEffect } from "react";
import { useAppStore } from "@/stores/useAppStore";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { Button } from "@/components/shared/Button";
import { Badge } from "@/components/shared/Badge";
import { validateLicenseKey, checkLicenseKey } from "@/lib/license";
import { detectDeploymentMode } from "@/lib/mode";

export function LicenseGate() {
  const hasSeenLanding = useAppStore((s) => s.hasSeenLanding);
  const licenseValid = useAppStore((s) => s.licenseValid);
  const licenseKey = useAppStore((s) => s.licenseKey);
  const setLicense = useAppStore((s) => s.setLicense);
  const setLicenseValid = useAppStore((s) => s.setLicenseValid);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [licenseRequired, setLicenseRequired] = useState(true);

  // Check deployment mode to know if license is required
  useEffect(() => {
    detectDeploymentMode()
      .then((mode) => setLicenseRequired(mode.license_required))
      .catch(() => setLicenseRequired(false)); // Default: don't block if backend unreachable
  }, []);

  // Re-validate stored key on mount
  useEffect(() => {
    if (licenseKey && !licenseValid) {
      checkLicenseKey(licenseKey).then((res) => {
        if (res.valid) {
          setLicense(licenseKey, res.license_type ?? "annual", res.expires_at);
        }
      }).catch(() => {});
    }
  }, [licenseKey, licenseValid, setLicense]);

  const handleValidate = useCallback(async () => {
    const key = input.trim();
    if (!key) return;
    setLoading(true);
    setError(null);
    try {
      const res = await validateLicenseKey(key);
      if (res.valid) {
        setLicense(key, res.license_type ?? "annual", res.expires_at);
      } else {
        setError("Invalid license key. Please check and try again.");
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [input, setLicense]);

  // Don't show if: license is valid, landing not dismissed, or license not required
  if (licenseValid || !hasSeenLanding || !licenseRequired) return null;

  return (
    <div className="fixed inset-0 z-[90] bg-obsidian/95 backdrop-blur-lg flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        <GlassPanel solid className="p-8">
          {/* Header */}
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-white">
              Activate VoxCraft
            </h2>
            <p className="text-sm text-text-secondary mt-2">
              Enter your license key to unlock the full experience.
            </p>
          </div>

          {/* License key input */}
          <div className="mb-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="VXCR-XXXX-XXXX-XXXX"
              className="w-full bg-surface border border-glass-border rounded-lg px-4 py-3 text-sm text-text-primary placeholder:text-text-muted font-mono text-center tracking-wider"
              onKeyDown={(e) => e.key === "Enter" && handleValidate()}
            />
          </div>

          {/* Error */}
          {error && (
            <p className="text-xs text-red-400 text-center mb-4">{error}</p>
          )}

          {/* Validate button */}
          <Button
            variant="primary"
            size="lg"
            loading={loading}
            disabled={!input.trim()}
            onClick={handleValidate}
            className="w-full mb-4"
          >
            Activate
          </Button>

          {/* Purchase link */}
          <div className="text-center">
            <p className="text-xs text-text-muted mb-2">
              Don't have a key yet?
            </p>
            <div className="flex justify-center gap-3">
              <Badge variant="cloud">Annual</Badge>
              <Badge variant="local">Lifetime</Badge>
            </div>
          </div>

          {/* Skip in dev mode */}
          {!licenseRequired && (
            <button
              onClick={() => setLicenseValid(true)}
              className="mt-4 w-full text-xs text-text-muted hover:text-text-secondary transition-colors py-2"
            >
              Skip (dev mode)
            </button>
          )}
        </GlassPanel>
      </div>
    </div>
  );
}
