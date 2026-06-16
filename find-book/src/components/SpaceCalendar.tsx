import { useRef, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import type { DatesSetArg } from "@fullcalendar/core";
import { useSpaceCalendar } from "@/hooks/useSpaces";

interface Props {
  spaceId: string;
  schedules: { day_of_week: number; open_time: string; close_time: string }[];
  onDateSelect?: (date: string, start: string) => void;
}

export function SpaceCalendar({ spaceId, schedules, onDateSelect }: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const [range, setRange] = useState({ start: today, end: today });
  const calRef = useRef<FullCalendar>(null);

  const { data: events = [] } = useSpaceCalendar(spaceId, range.start, range.end);

  const businessHours = schedules.map((s) => ({
    daysOfWeek: [s.day_of_week === 6 ? 0 : s.day_of_week + 1],
    startTime: s.open_time,
    endTime: s.close_time,
  }));

  function handleDatesSet(arg: DatesSetArg) {
    setRange({
      start: arg.startStr.slice(0, 10),
      end: arg.endStr.slice(0, 10),
    });
  }

  function handleDateClick(info: { dateStr: string; date: Date }) {
    if (onDateSelect) {
      const date = info.dateStr.slice(0, 10);
      const time = info.dateStr.slice(11, 16) || "10:00";
      onDateSelect(date, time);
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-card overflow-hidden">
      <style>{`
        .fc { font-family: inherit; font-size: 13px; }
        .fc-toolbar-title { font-size: 15px !important; font-weight: 600 !important; }
        .fc-button { background: hsl(var(--primary)) !important; border-color: hsl(var(--primary)) !important; border-radius: 8px !important; font-size: 12px !important; padding: 4px 10px !important; }
        .fc-button:hover { opacity: 0.9 !important; }
        .fc-button-active { opacity: 0.8 !important; }
        .fc-today-button { background: hsl(var(--secondary)) !important; border-color: hsl(var(--border)) !important; color: hsl(var(--foreground)) !important; }
        .fc-col-header-cell { background: hsl(var(--muted)) !important; }
        .fc-timegrid-slot { height: 28px !important; }
        .fc-non-business { background: rgba(0,0,0,0.03) !important; }
        .fc-day-today { background: hsl(var(--primary) / 0.04) !important; }
        .fc-event { border-radius: 6px !important; font-size: 11px !important; padding: 1px 4px !important; }
        .fc-daygrid-day-number { font-size: 13px !important; }
      `}</style>
      <FullCalendar
        ref={calRef}
        plugins={[timeGridPlugin, dayGridPlugin, interactionPlugin]}
        initialView="timeGridWeek"
        locale="es"
        firstDay={1}
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,timeGridWeek",
        }}
        buttonText={{ today: "Hoy", month: "Mes", week: "Semana" }}
        events={events}
        businessHours={businessHours.length > 0 ? businessHours : undefined}
        slotMinTime="07:00:00"
        slotMaxTime="23:30:00"
        slotDuration="00:30:00"
        allDaySlot={false}
        nowIndicator
        selectable={!!onDateSelect}
        dateClick={handleDateClick}
        datesSet={handleDatesSet}
        height={480}
        expandRows
      />
    </div>
  );
}
