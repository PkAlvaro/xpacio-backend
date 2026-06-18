import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { lazy, Suspense } from "react";
import { Layout } from "./components/Layout";
import { ReservationsProvider } from "./store/reservations";
import Home from "./pages/Home";

const NotFound = lazy(() => import("./pages/NotFound.tsx"));
const Search = lazy(() => import("./pages/Search"));
const SpaceDetail = lazy(() => import("./pages/SpaceDetail"));
const Booking = lazy(() => import("./pages/Booking"));
const Payment = lazy(() => import("./pages/Payment"));
const MyReservations = lazy(() => import("./pages/MyReservations"));
const PaymentConfirmation = lazy(() => import("./pages/PaymentConfirmation"));
const Login = lazy(() => import("./pages/Auth").then(m => ({ default: m.Login })));
const Register = lazy(() => import("./pages/Auth").then(m => ({ default: m.Register })));

const MySpaces = lazy(() => import("./pages/MySpaces"));
const PaymentReturn = lazy(() => import("./pages/PaymentReturn").then(m => ({ default: m.PaymentReturn })));
const PaymentSuccess = lazy(() => import("./pages/PaymentReturn").then(m => ({ default: m.PaymentSuccess })));
const PaymentCancelled = lazy(() => import("./pages/PaymentReturn").then(m => ({ default: m.PaymentCancelled })));

const AdminLayout = lazy(() => import("./pages/admin/AdminLayout"));
const AdminDashboard = lazy(() => import("./pages/admin/Dashboard"));
const AdminSpaces = lazy(() => import("./pages/admin/Spaces"));
const AdminSpaceEditor = lazy(() => import("./pages/admin/SpaceEditor"));
const AdminUsers = lazy(() => import("./pages/admin/Users"));
const AdminReservations = lazy(() => import("./pages/admin/Reservations"));
const AdminDisputes = lazy(() => import("./pages/admin/Disputes"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 5 * 60_000,
    },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <ReservationsProvider>
        <BrowserRouter>
          <Suspense fallback={<div className="min-h-screen bg-background" />}>
            <Routes>
              <Route element={<Layout />}>
                <Route path="/" element={<Home />} />
                <Route path="/buscar" element={<Search />} />
                <Route path="/espacio/:id" element={<SpaceDetail />} />
                <Route path="/reserva" element={<Booking />} />
                <Route path="/pago" element={<Payment />} />
                <Route path="/mis-reservas" element={<MyReservations />} />
                <Route path="/mis-espacios" element={<MySpaces />} />
                <Route path="/reserva/confirmacion" element={<PaymentConfirmation />} />
                <Route path="/pago/retorno" element={<PaymentReturn />} />
                <Route path="/pago/exito" element={<PaymentSuccess />} />
                <Route path="/pago/cancelado" element={<PaymentCancelled />} />
              </Route>
              <Route path="/login" element={<Login />} />
              <Route path="/registro" element={<Register />} />
              <Route path="/admin" element={<AdminLayout />}>
                <Route index element={<AdminDashboard />} />
                <Route path="espacios" element={<AdminSpaces />} />
                <Route path="espacios/nuevo" element={<AdminSpaceEditor />} />
                <Route path="espacios/:id/editar" element={<AdminSpaceEditor />} />
                <Route path="reservaciones" element={<AdminReservations />} />
                <Route path="reclamaciones" element={<AdminDisputes />} />
                <Route path="usuarios" element={<AdminUsers />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ReservationsProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
