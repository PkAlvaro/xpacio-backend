import { useRef, useState, useEffect } from "react";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import type { DatesSetArg, DateSelectArg } from "@fullcalendar/core";
import { useSpaceCalendar } from "@/hooks/useSpaces";

interface Props {
  spaceId: string;
  schedules: { day_of_week: number; open_time: string; close_time: string }[];
  onSelect?: (startDate: string, startTime: string, endDate: string, endTime: string) => void;
  selectedDate?: string;
  selectedEndDate?: string;
  selectedStart?: string;
  selectedEnd?: string;
}

export function SpaceCalendar({
  spaceId,
  schedules,
  onSelect,
  selectedDate,
  selectedEndDate,
  selectedStart,
  selectedEnd,
}: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const [range, setRange] = useState({ start: today, end: today });
  const calRef = useRef<FullCalendar>(null);

  const now = new Date();
  const scrollHour = Math.max(7, now.getHours() - 1);
  const scrollTime = `${String(scrollHour).padStart(2, "0")}:00:00`;

  const { data: events = [] } = useSpaceCalendar(spaceId, range.start, range.end);

  useEffect(() => {
    if (!selectedDate || !calRef.current) return;
    calRef.current.getApi().gotoDate(selectedDate);
  }, [selectedDate]);

  const businessHours = schedules.map((s) => ({
    daysOfWeek: [s.day_of_week === 6 ? 0 : s.day_of_week + 1],
    startTime: s.open_time,
    endTime: s.close_time,
  }));

  const effectiveEndDate = selectedEndDate || selectedDate;
  const selectionEvent =
    selectedDate && selectedStart && selectedEnd
      ? [
          {
            id: "__selected__",
            start: `${selectedDate}T${selectedStart}`,
            end: `${effectiveEndDate}T${selectedEnd}`,
            display: "background",
            color: "hsl(var(--primary) / 0.35)",
          },
        ]
      : [];

  function handleDatesSet(arg: DatesSetArg) {
    setRange({
      start: arg.startStr.slice(0, 10),
      end: arg.endStr.slice(0, 10),
    });
  }

  function handleSelect(info: DateSelectArg) {
    if (!onSelect) return;
    const startDate = info.startStr.slice(0, 10);
    const startTime = info.startStr.slice(11, 16) || "09:00";

    // FullCalendar end es exclusivo: si seleccionas hasta las 12:00 devuelve "12:00"
    // Para multi-día: end apunta al inicio del día siguiente → retrocedemos un día
    let endDate = info.endStr.slice(0, 10);
    let endTime = info.endStr.slice(11, 16);

    if (!endTime) {
      // Selección de días completos (vista mes) — sin tiempo
      const d = new Date(endDate);
      d.setDate(d.getDate() - 1);
      endDate = d.toISOString().slice(0, 10);
      endTime = "23:00";
    }

    onSelect(startDate, startTime, endDate, endTime);
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
        .fc-timegrid-slot { height: 32px !important; }
        .fc-non-business { background: rgba(0,0,0,0.03) !important; }
        .fc-day-today { background: hsl(var(--primary) / 0.04) !important; }
        .fc-event { border-radius: 6px !important; font-size: 11px !important; padding: 1px 4px !important; }
        .fc-highlight { background: hsl(var(--primary) / 0.2) !important; }
        .fc .fc-icon { font-family: inherit !important; font-style: normal !important; font-size: 14px !important; }
        .fc .fc-icon-chevron-left::before { content: "‹" !important; }
        .fc .fc-icon-chevron-right::before { content: "›" !important; }
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
        events={[...events, ...selectionEvent]}
        businessHours={businessHours.length > 0 ? businessHours : undefined}
        slotMinTime="07:00:00"
        slotMaxTime="23:00:00"
        slotDuration="01:00:00"
        slotLabelInterval="01:00"
        scrollTime={scrollTime}
        allDaySlot={false}
        nowIndicator
        selectable={!!onSelect}
        selectMirror
        unselectAuto={false}
        select={handleSelect}
        datesSet={handleDatesSet}
        height={480}
        expandRows
      />
    </div>
  );
}
