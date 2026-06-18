import { Building2, Users, CalendarCheck, AlertTriangle, DollarSign, Server, Database, Cpu } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { useAdminStats, useAdminHealth } from "@/hooks/useAdmin";
import { cn } from "@/lib/utils";

const formatCLP = (n: number) =>
  new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(n);

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  color,
  alert,
}: {
  label: string;
  value: string | number | undefined;
  sub?: string;
  icon: React.ElementType;
  color: string;
  alert?: boolean;
}) {
  return (
    <div className={cn("bg-card border rounded-2xl p-6", alert ? "border-yellow-400/60" : "border-border")}>
      <div className={`w-12 h-12 rounded-xl grid place-items-center mb-4 ${color}`}>
        <Icon className="w-6 h-6" />
      </div>
      <p className="text-3xl font-bold font-display">{value ?? "—"}</p>
      <p className="text-sm text-muted-foreground mt-1">{label}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

function HealthBadge({ status }: { status: "ok" | "fail" | undefined }) {
  if (!status) return <span className="text-xs text-muted-foreground">—</span>;
  return (
    <span
      className={cn(
        "text-xs font-semibold px-2 py-0.5 rounded-full",
        status === "ok"
          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
          : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
      )}
    >
      {status === "ok" ? "OK" : "FALLO"}
    </span>
  );
}

function formatChartDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("es-CL", { day: "numeric", month: "short" });
}

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useAdminStats();
  const { data: health } = useAdminHealth();

  const chartData = stats?.daily_reservations?.map(d => ({
    ...d,
    label: formatChartDate(d.date),
  })) ?? [];

  const overallHealth = health?.status;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Vista general del sistema Xpacio</p>
      </div>

      {stats?.pending_disputes != null && stats.pending_disputes > 0 && (
        <div className="flex items-center gap-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-2xl px-5 py-4">
          <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 shrink-0" />
          <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
            {stats.pending_disputes} reclamaci{stats.pending_disputes === 1 ? "ón pendiente" : "ones pendientes"} sin resolver
          </p>
          <a
            href="/admin/reclamaciones"
            className="ml-auto text-xs font-semibold text-yellow-700 dark:text-yellow-300 underline underline-offset-2 hover:opacity-70"
          >
            Ver reclamaciones →
          </a>
        </div>
      )}

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-5">
        <StatCard
          label="Espacios totales"
          value={stats?.total_spaces}
          sub={`${stats?.active_spaces ?? "—"} activos`}
          icon={Building2}
          color="bg-primary/10 text-primary"
        />
        <StatCard
          label="Usuarios registrados"
          value={stats?.total_users}
          icon={Users}
          color="bg-blue-500/10 text-blue-500"
        />
        <StatCard
          label="Reservas totales"
          value={stats?.total_reservations}
          icon={CalendarCheck}
          color="bg-orange-500/10 text-orange-500"
        />
        <StatCard
          label="Revenue total"
          value={stats ? formatCLP(stats.total_revenue) : undefined}
          sub={stats ? `${formatCLP(stats.revenue_30d)} últimos 30 días` : undefined}
          icon={DollarSign}
          color="bg-green-500/10 text-green-600"
        />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-card border border-border rounded-2xl p-6">
          <h2 className="font-semibold text-base mb-5">Reservas — últimos 30 días</h2>
          {statsLoading ? (
            <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">Cargando…</div>
          ) : chartData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">Sin datos todavía</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  interval="preserveStartEnd"
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "12px",
                    fontSize: "12px",
                  }}
                  labelStyle={{ fontWeight: 600 }}
                  formatter={(v: number) => [v, "reservas"]}
                />
                <Line
                  type="monotone"
                  dataKey="reservations"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-card border border-border rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold text-base">Estado de servicios</h2>
            {overallHealth && (
              <span
                className={cn(
                  "text-xs font-semibold px-2.5 py-1 rounded-full",
                  overallHealth === "healthy"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                )}
              >
                {overallHealth === "healthy" ? "Saludable" : "Degradado"}
              </span>
            )}
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between py-3 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-blue-500/10 grid place-items-center">
                  <Database className="w-4 h-4 text-blue-500" />
                </div>
                <div>
                  <p className="text-sm font-medium">Base de datos</p>
                  <p className="text-xs text-muted-foreground">PostgreSQL</p>
                </div>
              </div>
              <HealthBadge status={health?.checks?.db as "ok" | "fail" | undefined} />
            </div>

            <div className="flex items-center justify-between py-3 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-red-500/10 grid place-items-center">
                  <Server className="w-4 h-4 text-red-500" />
                </div>
                <div>
                  <p className="text-sm font-medium">Cache</p>
                  <p className="text-xs text-muted-foreground">Redis</p>
                </div>
              </div>
              <HealthBadge status={health?.checks?.redis as "ok" | "fail" | undefined} />
            </div>

            <div className="flex items-center justify-between py-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-purple-500/10 grid place-items-center">
                  <Cpu className="w-4 h-4 text-purple-500" />
                </div>
                <div>
                  <p className="text-sm font-medium">API</p>
                  <p className="text-xs text-muted-foreground">FastAPI</p>
                </div>
              </div>
              <HealthBadge status={health ? "ok" : undefined} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
