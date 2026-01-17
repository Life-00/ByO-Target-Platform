import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Session from './pages/Session';
import Workspace from './pages/Workspace';
import NotFound from './pages/NotFound';
import { useAuthStore } from './stores/authStore';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const hasToken = localStorage.getItem('access_token');
  
  // 토큰이 있으면 인증된 것으로 간주
  return (isAuthenticated || hasToken) ? children : <Navigate to="/" />;
};

function App() {
  const { restoreUser } = useAuthStore();

  // 앱 로드 시 로컬 스토리지에서 사용자 복원
  useEffect(() => {
    restoreUser();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/session"
          element={
            <ProtectedRoute>
              <Session />
            </ProtectedRoute>
          }
        />
        <Route
          path="/workspace/:sessionId"
          element={
            <ProtectedRoute>
              <Workspace />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
