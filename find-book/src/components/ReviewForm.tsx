import { useState } from "react";
import { Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useCreateReview } from "@/hooks/useReviews";
import { ApiError } from "@/lib/api";

interface Props {
  reservationId: string;
  onSuccess?: () => void;
}

const ReviewForm = ({ reservationId, onSuccess }: Props) => {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [comment, setComment] = useState("");
  const mutation = useCreateReview(reservationId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating === 0) {
      toast.error("Selecciona una puntuación");
      return;
    }
    try {
      await mutation.mutateAsync({ rating, comment: comment.trim() || undefined });
      toast.success("¡Reseña publicada!");
      onSuccess?.();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Error al publicar reseña");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="border border-border rounded-xl p-4 space-y-4 bg-card">
      <h3 className="font-semibold text-sm">Dejar reseña</h3>
      <div className="flex gap-1">
        {Array.from({ length: 5 }).map((_, i) => {
          const val = i + 1;
          return (
            <button
              key={i}
              type="button"
              onMouseEnter={() => setHovered(val)}
              onMouseLeave={() => setHovered(0)}
              onClick={() => setRating(val)}
            >
              <Star
                className={`w-6 h-6 transition-colors ${
                  val <= (hovered || rating)
                    ? "fill-amber-400 text-amber-400"
                    : "fill-muted text-muted"
                }`}
              />
            </button>
          );
        })}
      </div>
      <textarea
        className="w-full border border-input bg-background rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        rows={3}
        placeholder="Cuéntanos tu experiencia (opcional)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        maxLength={500}
      />
      <Button type="submit" size="sm" disabled={mutation.isPending}>
        {mutation.isPending ? "Publicando…" : "Publicar reseña"}
      </Button>
    </form>
  );
};

export default ReviewForm;
