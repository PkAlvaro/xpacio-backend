import { Link } from "react-router-dom";
import { MapPin, Star, Users, Tag } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { SpaceListItem } from "@/types/api";

const formatCLP = (n: number) =>
  new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" }).format(n);

const PLACEHOLDER = "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&q=80";

export const SpaceCard = ({ space, index = 0 }: { space: SpaceListItem; index?: number }) => {
  const image = space.primary_image ?? PLACEHOLDER;
  const hasDiscount = space.discount_active && !!space.discount_value;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
    >
      <Link to={`/espacio/${space.slug ?? space.id}`} className="group block">
        <div className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-muted shadow-soft">
          <img
            src={image}
            alt={space.name}
            loading="lazy"
            className="w-full h-full object-cover transition-smooth group-hover:scale-105"
          />
          <div className="absolute top-3 left-3">
            <span className={cn(
              "px-2.5 py-1 rounded-full text-xs font-medium backdrop-blur-md",
              space.is_active ? "bg-success/90 text-success-foreground" : "bg-muted/90 text-muted-foreground"
            )}>
              <span className={cn("inline-block w-1.5 h-1.5 rounded-full mr-1.5",
                space.is_active ? "bg-white animate-pulse-soft" : "bg-muted-foreground")} />
              {space.is_active ? "Disponible" : "Ocupado"}
            </span>
            {hasDiscount && (
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold backdrop-blur-md bg-primary text-primary-foreground inline-flex items-center gap-1">
                <Tag className="w-3 h-3" />
                {space.discountValue ? `-${Math.round(space.discountValue)}%` : "Oferta"}
              </span>
            )}
          </div>
        </div>
        <div className="pt-3 space-y-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold leading-tight">{space.name}</h3>
            <div className="flex items-center gap-1 text-sm shrink-0">
              <Star className="w-3.5 h-3.5 fill-foreground" />
              <span className="font-medium">{space.rating.toFixed(1)}</span>
            </div>
          </div>
          <p className="text-sm text-muted-foreground flex items-center gap-1">
            <MapPin className="w-3.5 h-3.5" /> {space.address}
            {space.distance_km != null && (
              <span className="ml-1 text-xs">· {space.distance_km} km</span>
            )}
          </p>
          <p className="text-sm text-muted-foreground flex items-center gap-1">
            <Users className="w-3.5 h-3.5" /> Hasta {space.capacity} personas · {space.type}
          </p>
          <p className="pt-1">
            <span className="font-semibold">{formatCLP(space.price_per_hour)}</span>
            <span className="text-muted-foreground text-sm"> / hora</span>
          </p>
        </div>
      </Link>
    </motion.div>
  );
};
