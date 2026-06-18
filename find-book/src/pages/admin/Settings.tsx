import { useState, useEffect } from "react";
import { Settings2, Save, RotateCcw, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useSystemConfig, useUpdateSystemConfig } from "@/hooks/useAdmin";
import type { SystemConfig } from "@/types/api";

function SettingRow({
  label,
  description,
  children,
}: {
  label: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-6 py-5 border-b border-border last:border-0">
      <div className="min-w-0">
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

export default function Settings() {
  const { data: config, isLoading } = useSystemConfig();
  const updateConfig = useUpdateSystemConfig();

  const [form, setForm] = useState<Partial<SystemConfig>>({});
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (config) {
      setForm(config);
      setDirty(false);
    }
  }, [config]);

  const set = <K extends keyof SystemConfig>(key: K, value: SystemConfig[K]) => {
    setForm(prev => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const handleReset = () => {
    if (config) {
      setForm(config);
      setDirty(false);
    }
  };

  const handleSave = async () => {
    await updateConfig.mutateAsync(form);
    toast.success("Configuración guardada");
    setDirty(false);
  };

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground text-sm">Cargando configuración…</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8 gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-3xl font-bold">Configuración</h1>
          <p className="text-muted-foreground mt-1">Parámetros globales del sistema Xpacio</p>
        </div>
        <div className="flex gap-2">
          {dirty && (
            <Button variant="outline" size="sm" onClick={handleReset}>
              <RotateCcw className="w-4 h-4" /> Descartar
            </Button>
          )}
          <Button variant="hero" size="sm" onClick={handleSave} disabled={!dirty || updateConfig.isPending}>
            <Save className="w-4 h-4" />
            {updateConfig.isPending ? "Guardando…" : "Guardar cambios"}
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <section className="bg-card border border-border rounded-2xl px-6">
            <div className="py-5 border-b border-border">
              <div className="flex items-center gap-2">
                <Settings2 className="w-4 h-4 text-muted-foreground" />
                <h2 className="font-semibold text-sm">Parámetros de negocio</h2>
              </div>
            </div>

            <SettingRow
              label="Comisión de plataforma (%)"
              description="Porcentaje que Xpacio cobra sobre cada reserva como cargo de servicio."
            >
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.5}
                  value={form.platform_fee_percent ?? ""}
                  onChange={e => set("platform_fee_percent", parseFloat(e.target.value))}
                  className="w-24 px-3 py-2 rounded-xl border border-border bg-background text-sm text-right outline-none focus:ring-2 ring-primary/20"
                />
                <span className="text-sm text-muted-foreground">%</span>
              </div>
            </SettingRow>

            <SettingRow
              label="Ventana de reclamaciones (días)"
              description="Días después de finalizada una reserva en que el cliente puede abrir una disputa."
            >
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={30}
                  value={form.dispute_window_days ?? ""}
                  onChange={e => set("dispute_window_days", parseInt(e.target.value))}
                  className="w-24 px-3 py-2 rounded-xl border border-border bg-background text-sm text-right outline-none focus:ring-2 ring-primary/20"
                />
                <span className="text-sm text-muted-foreground">días</span>
              </div>
            </SettingRow>

            <SettingRow
              label="TTL de reservas pendientes (min)"
              description="Minutos que tiene el cliente para pagar antes de que la reserva expire automáticamente."
            >
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={5}
                  max={120}
                  value={form.pending_reservation_ttl_minutes ?? ""}
                  onChange={e => set("pending_reservation_ttl_minutes", parseInt(e.target.value))}
                  className="w-24 px-3 py-2 rounded-xl border border-border bg-background text-sm text-right outline-none focus:ring-2 ring-primary/20"
                />
                <span className="text-sm text-muted-foreground">min</span>
              </div>
            </SettingRow>
          </section>

          <section className="bg-card border border-border rounded-2xl px-6">
            <div className="py-5 border-b border-border">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                <h2 className="font-semibold text-sm">Estado de la plataforma</h2>
              </div>
            </div>

            <SettingRow
              label="Modo mantenimiento"
              description="Suspende el acceso público a la plataforma. Los administradores siguen teniendo acceso."
            >
              <button
                type="button"
                role="switch"
                aria-checked={form.maintenance_mode ?? false}
                onClick={() => set("maintenance_mode", !(form.maintenance_mode ?? false))}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
                  form.maintenance_mode ? "bg-yellow-500" : "bg-border"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                    form.maintenance_mode ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </SettingRow>
          </section>
        </div>

        <aside className="space-y-4">
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-2">Valores actuales</h3>
            <dl className="space-y-2 text-xs text-blue-700 dark:text-blue-400">
              <div className="flex justify-between">
                <dt>Comisión:</dt>
                <dd className="font-mono font-semibold">{config?.platform_fee_percent ?? "—"}%</dd>
              </div>
              <div className="flex justify-between">
                <dt>Ventana disputas:</dt>
                <dd className="font-mono font-semibold">{config?.dispute_window_days ?? "—"} días</dd>
              </div>
              <div className="flex justify-between">
                <dt>TTL reservas:</dt>
                <dd className="font-mono font-semibold">{config?.pending_reservation_ttl_minutes ?? "—"} min</dd>
              </div>
              <div className="flex justify-between">
                <dt>Mantenimiento:</dt>
                <dd className="font-mono font-semibold">{config?.maintenance_mode ? "Sí" : "No"}</dd>
              </div>
            </dl>
          </div>

          <div className="bg-card border border-border rounded-2xl p-5">
            <h3 className="text-sm font-semibold mb-2">Notas</h3>
            <ul className="text-xs text-muted-foreground space-y-2">
              <li>• Los cambios en la comisión aplican solo a nuevas reservas.</li>
              <li>• La ventana de disputas no afecta reclamaciones ya abiertas.</li>
              <li>• El TTL solo afecta reservas pendientes de pago nuevas.</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
