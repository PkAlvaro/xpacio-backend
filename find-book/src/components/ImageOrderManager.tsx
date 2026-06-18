import { useRef } from "react";
import { Upload, Trash2, Star, Plus, ArrowUp, ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { SpaceImage } from "@/types/api";

interface Props {
  spaceId: string | undefined;
  images: SpaceImage[];
  uploading: boolean;
  onUpload: (files: File[]) => void;
  onDelete: (imageId: string) => void;
  onSetPrimary: (imageId: string) => void;
  onReorder: (order: { id: string; display_order: number }[]) => void;
}

export function ImageOrderManager({
  spaceId,
  images,
  uploading,
  onUpload,
  onDelete,
  onSetPrimary,
  onReorder,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const isNew = !spaceId;

  const sorted = [...images].sort((a, b) => a.display_order - b.display_order);

  const move = (index: number, dir: -1 | 1) => {
    const next = index + dir;
    if (next < 0 || next >= sorted.length) return;
    const updated = sorted.map((img, i) => ({
      id: img.id,
      display_order: i === index ? next : i === next ? index : i,
    }));
    onReorder(updated);
  };

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onUpload(files);
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Fotos del espacio</h3>
        <Button variant="outline" onClick={() => fileRef.current?.click()} disabled={isNew || uploading}>
          <Upload className="w-4 h-4" /> Subir imágenes
        </Button>
        <input ref={fileRef} type="file" multiple accept="image/*" className="hidden" onChange={handleFiles} />
      </div>

      {isNew && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 text-sm text-yellow-700 dark:text-yellow-400 mb-4">
          Guarda el espacio primero para poder subir imágenes.
        </div>
      )}

      {sorted.length === 0 ? (
        <div
          onClick={() => !isNew && fileRef.current?.click()}
          className="border-2 border-dashed border-border rounded-2xl p-16 text-center text-muted-foreground cursor-pointer hover:border-primary/50 transition-smooth">
          <Upload className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Arrastra imágenes aquí o haz clic para seleccionar</p>
          <p className="text-xs opacity-60 mt-1">JPG, PNG, WebP</p>
        </div>
      ) : (
        <>
          <p className="text-xs text-muted-foreground mb-3">
            La primera imagen es la principal del carrusel. Usa las flechas para cambiar el orden.
          </p>
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-4">
            {sorted.map((img, i) => (
              <div key={img.id} className="relative group rounded-xl overflow-hidden border border-border">
                <div className="aspect-square">
                  <img src={img.url} alt="" className="w-full h-full object-cover" />
                </div>

                {/* Orden + badge principal */}
                <div className="absolute top-2 left-2 flex items-center gap-1.5">
                  <span className="bg-black/60 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                    #{i + 1}
                  </span>
                  {img.is_primary && (
                    <span className="bg-yellow-400 text-yellow-900 text-xs font-bold px-2 py-0.5 rounded-full">
                      Principal
                    </span>
                  )}
                </div>

                {/* Controles hover */}
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-smooth flex items-center justify-center gap-2">
                  <button
                    onClick={() => move(i, -1)}
                    disabled={i === 0}
                    title="Mover arriba"
                    className="p-2 rounded-full bg-white/20 hover:bg-white/40 transition-smooth disabled:opacity-30">
                    <ArrowUp className="w-4 h-4 text-white" />
                  </button>
                  <button
                    onClick={() => move(i, 1)}
                    disabled={i === sorted.length - 1}
                    title="Mover abajo"
                    className="p-2 rounded-full bg-white/20 hover:bg-white/40 transition-smooth disabled:opacity-30">
                    <ArrowDown className="w-4 h-4 text-white" />
                  </button>
                  <button
                    onClick={() => onSetPrimary(img.id)}
                    title="Marcar como principal"
                    className="p-2 rounded-full bg-white/20 hover:bg-white/40 transition-smooth">
                    <Star className={cn("w-4 h-4", img.is_primary ? "fill-yellow-400 text-yellow-400" : "text-white")} />
                  </button>
                  <button
                    onClick={() => onDelete(img.id)}
                    className="p-2 rounded-full bg-white/20 hover:bg-red-500/60 transition-smooth">
                    <Trash2 className="w-4 h-4 text-white" />
                  </button>
                </div>
              </div>
            ))}

            <button
              onClick={() => fileRef.current?.click()}
              className="aspect-square rounded-xl border-2 border-dashed border-border hover:border-primary/50 flex flex-col items-center justify-center gap-2 text-muted-foreground hover:text-primary transition-smooth">
              <Plus className="w-6 h-6" />
              <span className="text-xs">Agregar</span>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
