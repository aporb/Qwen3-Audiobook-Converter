import { Button } from "@/components/shared/Button";
import { GlassPanel } from "@/components/shared/GlassPanel";
import { Badge } from "@/components/shared/Badge";
import { useCastingStore } from "@/stores/useCastingStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { apiFetch } from "@/lib/api";
import { useState } from "react";

export function VoiceAssigner() {
  const bookId = useProjectStore((s) => s.bookId);
  const assignments = useCastingStore((s) => s.assignments);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const assigned = assignments.filter((a) => a.voice);

  const handleSave = async () => {
    if (!bookId || assigned.length === 0) return;
    setSaving(true);
    try {
      await apiFetch("/casting/assign-voices", {
        method: "POST",
        body: JSON.stringify({
          book_id: bookId,
          assignments: assigned,
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (assigned.length === 0) return null;

  return (
    <GlassPanel solid className="animate-slide-up">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
          Voice Assignments ({assigned.length})
        </h3>
        <Button
          variant="primary"
          size="sm"
          loading={saving}
          onClick={handleSave}
        >
          {saved ? "Saved!" : "Save Assignments"}
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {assigned.map((a) => (
          <Badge key={a.character_name} variant="active">
            {a.character_name} → {a.voice}
          </Badge>
        ))}
      </div>
    </GlassPanel>
  );
}
