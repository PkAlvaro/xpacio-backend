import { Building2, Users, CalendarCheck, TrendingUp } from "lucide-react";
import { useAdminStats } from "@/hooks/useAdmin";

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number | undefined; icon: any; color: string }) {
  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <div className={`w-12 h-12 rounded-xl grid place-items-center mb-4 ${color}`}>
        <Icon className="w-6 h-6" />
      </div>
      <p className="text-3xl font-bold font-display">{value ?? "—"}</p>
      <p className="text-sm text-muted-foreground mt-1">{label}</p>
    </div>
  );
}

export default function Dashboard() {
  const { data: stats } = useAdminStats();

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-display text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Vista general del sistema Xpacio</p>
      </div>

      <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-5">
        <StatCard label="Espacios totales" value={stats?.total_spaces} icon={Building2} color="bg-primary/10 text-primary" />
        <StatCard label="Espacios activos" value={stats?.active_spaces} icon={TrendingUp} color="bg-success/10 text-success" />
        <StatCard label="Usuarios registrados" value={stats?.total_users} icon={Users} color="bg-blue-500/10 text-blue-500" />
        <StatCard label="Reservas realizadas" value={stats?.total_reservations} icon={CalendarCheck} color="bg-orange-500/10 text-orange-500" />
      </div>
    </div>
  );
}
