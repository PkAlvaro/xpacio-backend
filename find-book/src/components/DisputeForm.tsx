import { useState, useRef } from "react";
import { X, Paperclip, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useOpenDispute } from "@/hooks/useDisputes";

interface Props {
  reservationId: string;
  spaceName?: string;
  onClose: () => void;
}

export function DisputeForm({ reservationId, spaceName, onClose }: Props) {
  const [reason, setReason] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const mut = useOpenDispute();

  const handleFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const added = Array.from(e.target.files ?? []).filter(f => f.type.startsWith("image/"));
    setFiles(prev => [...prev, ...added].slice(0, 5));
    e.target.value = "";
  };

  const removeFile = (i: number) => setFiles(prev => prev.filter((_, idx) => idx !== i));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reason.trim().length < 20) {
      toast.error("El motivo debe tener al menos 20 caracteres");
      return;
    }
    try {
      await mut.mutateAsync({ reservationId, reason: reason.trim(), files });
      toast.success("Reclamación enviada correctamente");
      onClose();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Error al enviar reclamación");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-card border border-border rounded-2xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between p-5 border-b border-border">
          <div>
            <h2 className="font-semibold text-lg">Abrir reclamación</h2>
            {spaceName && <p className="text-sm text-muted-foreground">{spaceName}</p>}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-secondary text-muted-foreground">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="flex gap-2 p-3 rounded-xl bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 text-sm text-yellow-800 dark:text-yellow-300">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>Tienes 3 días desde que finalizó la reserva para presentar una reclamación. Un administrador revisará tu caso.</span>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">
              Motivo de la reclamación <span className="text-destructive">*</span>
            </label>
            <textarea
              rows={5}
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="Describe con detalle el problema que tuviste con el espacio o la reserva..."
              className="w-full px-3 py-2.5 rounded-xl border border-border bg-background text-sm resize-none outline-none focus:ring-2 ring-primary/20"
              required
            />
            <p className="text-xs text-muted-foreground mt-1">{reason.trim().length}/20 caracteres mínimo</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">
              Evidencias (imágenes, máx. 5)
            </label>
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-border rounded-xl p-4 text-center cursor-pointer hover:border-primary/50 transition-smooth"
            >
              <Paperclip className="w-5 h-5 mx-auto mb-1.5 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Haz clic para adjuntar imágenes</p>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleFiles}
                className="hidden"
              />
            </div>
            {files.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {files.map((f, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs bg-secondary px-2.5 py-1.5 rounded-lg">
                    <span className="truncate max-w-[120px]">{f.name}</span>
                    <button type="button" onClick={() => removeFile(i)} className="text-muted-foreground hover:text-destructive">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex gap-2 justify-end pt-1">
            <Button type="button" variant="outline" onClick={onClose}>Cancelar</Button>
            <Button
              type="submit"
              variant="hero"
              disabled={mut.isPending || reason.trim().length < 20}
            >
              {mut.isPending ? "Enviando…" : "Enviar reclamación"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
