import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

const TIMES: string[] = (() => {
  const t: string[] = [];
  for (let h = 7; h <= 23; h++) {
    t.push(`${String(h).padStart(2, "0")}:00`);
    if (h < 23) t.push(`${String(h).padStart(2, "0")}:30`);
  }
  return t;
})();

const BLOCKS = TIMES.slice(0, TIMES.length - 1); // 32 bloques

function idxFromPoint(x: number, y: number): number | null {
  const el = document.elementFromPoint(x, y);
  const raw = el?.getAttribute("data-idx") ?? el?.closest("[data-idx]")?.getAttribute("data-idx");
  return raw != null ? Number(raw) : null;
}

interface TimeGridProps {
  start: string;
  end: string;
  onChange: (start: string, end: string) => void;
  unavailable?: Set<string>;
}

export function TimeGrid({ start, end, onChange, unavailable = new Set() }: TimeGridProps) {
  // refs for sync access — no stale closures
  const anchorRef = useRef<number | null>(null);
  const hoverRef = useRef<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // state only for re-renders
  const [anchor, setAnchor] = useState<number | null>(null);
  const [hover, setHover] = useState<number | null>(null);

  const selLo = TIMES.indexOf(start);
  const selHi = TIMES.indexOf(end) - 1;

  const isDragging = anchor !== null;
  const dragLo = isDragging && hover !== null ? Math.min(anchor, hover) : null;
  const dragHi = isDragging && hover !== null ? Math.max(anchor, hover) : null;

  const commit = useCallback(
    (a: number, b: number) => {
      const lo = Math.min(a, b);
      const hi = Math.max(a, b);
      onChange(BLOCKS[lo], TIMES[hi + 1]);
    },
    [onChange],
  );

  // Global mouseup / touchend — always fires even outside container
  useEffect(() => {
    const onUp = () => {
      const a = anchorRef.current;
      const h = hoverRef.current;
      if (a !== null && h !== null) commit(a, h);
      anchorRef.current = null;
      hoverRef.current = null;
      setAnchor(null);
      setHover(null);
    };
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchend", onUp);
    return () => {
      window.removeEventListener("mouseup", onUp);
      window.removeEventListener("touchend", onUp);
    };
  }, [commit]);

  // Non-passive touchmove to allow preventDefault
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onTouchMove = (e: TouchEvent) => {
      if (anchorRef.current === null) return;
      e.preventDefault();
      const t = e.touches[0];
      const idx = idxFromPoint(t.clientX, t.clientY);
      if (idx !== null) {
        hoverRef.current = idx;
        setHover(idx);
      }
    };
    el.addEventListener("touchmove", onTouchMove, { passive: false });
    return () => el.removeEventListener("touchmove", onTouchMove);
  }, []);

  function onContainerMouseMove(e: React.MouseEvent) {
    if (anchorRef.current === null) return;
    const idx = idxFromPoint(e.clientX, e.clientY);
    if (idx !== null && idx !== hoverRef.current) {
      hoverRef.current = idx;
      setHover(idx);
    }
  }

  function onDown(i: number) {
    if (unavailable.has(BLOCKS[i])) return;
    anchorRef.current = i;
    hoverRef.current = i;
    setAnchor(i);
    setHover(i);
  }

  function blockState(i: number): "selected" | "preview" | "unavail" | "free" {
    if (unavailable.has(BLOCKS[i])) return "unavail";
    if (dragLo !== null && dragHi !== null && i >= dragLo && i <= dragHi) return "preview";
    if (!isDragging && selLo !== -1 && selHi >= selLo && i >= selLo && i <= selHi) return "selected";
    return "free";
  }

  const hours =
    selLo !== -1 && selHi >= selLo ? Math.round((selHi - selLo + 1) * 5) / 10 : 0;

  return (
    <div className="select-none">
      <div
        ref={containerRef}
        className="rounded-xl border border-border overflow-y-auto"
        style={{ maxHeight: 272 }}
        onMouseMove={onContainerMouseMove}
        onMouseDown={(e) => e.preventDefault()}
      >
        {BLOCKS.map((time, i) => {
          const s = blockState(i);
          const isHour = time.endsWith(":00");
          return (
            <div
              key={time}
              data-idx={i}
              style={{ height: 17 }}
              className={cn(
                "flex items-center gap-1.5 pl-2 pr-1",
                s !== "unavail" ? "cursor-pointer" : "cursor-not-allowed",
                isHour && "border-t border-border/40",
              )}
              onMouseDown={() => onDown(i)}
              onTouchStart={(e) => { e.preventDefault(); onDown(i); }}
            >
              <span
                className={cn(
                  "text-[10px] w-8 shrink-0 font-mono leading-none tabular-nums pointer-events-none",
                  isHour ? "text-muted-foreground" : "invisible",
                )}
              >
                {isHour ? time : ""}
              </span>
              <div
                className={cn(
                  "flex-1 rounded-sm transition-colors duration-75 pointer-events-none",
                  s === "free" && "h-2 bg-border/50",
                  s === "selected" && "h-3 bg-primary/70",
                  s === "preview" && "h-3 bg-primary",
                  s === "unavail" && "h-2 bg-destructive/30",
                )}
              />
            </div>
          );
        })}
      </div>

      <p className="mt-1.5 text-center text-xs">
        {hours > 0 ? (
          <>
            <span className="font-semibold text-foreground">
              {start} → {end}
            </span>
            <span className="text-muted-foreground ml-1.5">
              ({hours} hora{hours !== 1 ? "s" : ""})
            </span>
          </>
        ) : (
          <span className="text-muted-foreground">
            Arrastra para seleccionar horario
          </span>
        )}
      </p>
    </div>
  );
}
