import { Button } from "@/components/shared/Button";

interface PerformButtonProps {
  onClick: () => void;
  loading: boolean;
  disabled?: boolean;
}

export function PerformButton({ onClick, loading, disabled }: PerformButtonProps) {
  return (
    <Button
      variant="primary"
      size="lg"
      loading={loading}
      disabled={disabled}
      onClick={onClick}
      className="w-full"
      data-tour="perform-button"
    >
      {loading ? "Generating..." : "Perform"}
    </Button>
  );
}
