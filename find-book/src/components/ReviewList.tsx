import { Star } from "lucide-react";
import type { Review } from "@/types/api";

interface Props {
  reviews: Review[];
  total: number;
  isLoading: boolean;
}

const StarDisplay = ({ rating }: { rating: number }) => (
  <div className="flex gap-0.5">
    {Array.from({ length: 5 }).map((_, i) => (
      <Star
        key={i}
        className={`w-4 h-4 ${i < rating ? "fill-amber-400 text-amber-400" : "fill-muted text-muted"}`}
      />
    ))}
  </div>
);

const ReviewList = ({ reviews, total, isLoading }: Props) => {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-20 bg-muted rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <p className="text-muted-foreground text-sm py-4">
        Aún no hay reseñas para este espacio.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">{total} reseña{total !== 1 ? "s" : ""}</p>
      {reviews.map((r) => (
        <div key={r.id} className="border border-border rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-medium text-sm">{r.client_name}</span>
            <span className="text-xs text-muted-foreground">
              {new Date(r.created_at).toLocaleDateString("es-CL")}
            </span>
          </div>
          <StarDisplay rating={r.rating} />
          {r.comment && <p className="text-sm text-foreground">{r.comment}</p>}
        </div>
      ))}
    </div>
  );
};

export default ReviewList;
