import { createContext, useContext, useEffect, useState, ReactNode } from "react";

// Las reservas ahora viven en el backend (GET/POST /reservations).
// Este store solo conserva los FAVORITOS, que no tienen endpoint propio y se
// persisten localmente en localStorage.
interface Ctx {
  favorites: string[];
  toggleFavorite: (id: string) => void;
}

const ReservationsContext = createContext<Ctx | null>(null);

export const ReservationsProvider = ({ children }: { children: ReactNode }) => {
  const [favorites, setFavorites] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("favorites") || "[]");
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem("favorites", JSON.stringify(favorites));
  }, [favorites]);

  const toggleFavorite = (id: string) =>
    setFavorites((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  return (
    <ReservationsContext.Provider value={{ favorites, toggleFavorite }}>
      {children}
    </ReservationsContext.Provider>
  );
};

export const useReservations = () => {
  const ctx = useContext(ReservationsContext);
  if (!ctx) throw new Error("useReservations must be used inside ReservationsProvider");
  return ctx;
};
