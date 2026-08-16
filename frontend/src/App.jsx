import Landing from './pages/Landing';
import Try from './pages/Try';
import DemoAdminDashboard from './pages/DemoAdminDashboard';
import SupportDashboard from './pages/SupportDashboard';
import AdminDashboard from './pages/AdminDashboard';
import NotFound from './pages/NotFound';
import ProtectedRoute from './components/ProtectedRoute';
import { Navigate, Routes, Route } from "react-router";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/try" element={<Navigate to="/demo/support" replace />} />
      <Route path="/demo/support" element={<Try />} />
      <Route path="/demo/admin" element={<DemoAdminDashboard />} />
      <Route
        path="/support"
        element={
          <ProtectedRoute>
            <SupportDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default App;
