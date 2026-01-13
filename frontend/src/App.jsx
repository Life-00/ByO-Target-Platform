import React, { useState, useEffect } from "react";
import AuthContainer from "./components/Auth/AuthContainer";
import Dashboard from "./components/Dashboard/Dashboard";
import api from "./api";
import "./App.css"; // CSS 파일이 import 되어 있어야 합니다.

const App = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const verifySession = async () => {
      const token = localStorage.getItem("token");

      if (token) {
        console.log("[AUTH] Token found. Verifying with server...");
        try {
          await api.get("/auth/me");

          console.log("[AUTH] Session verified. Welcome back.");
          setIsLoggedIn(true);
        } catch (error) {
          console.error("[AUTH] Session expired or invalid.");
          localStorage.removeItem("token");
          setIsLoggedIn(false);
        }
      } else {
        console.log("[AUTH] No token found. Please login.");
        setIsLoggedIn(false);
      }

      setIsLoading(false);
    };

    verifySession();
  }, []);

  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setIsLoggedIn(false);
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {isLoggedIn ? (
        <Dashboard onLogout={handleLogout} />
      ) : (
        <AuthContainer onLoginSuccess={handleLoginSuccess} />
      )}
    </div>
  );
};

export default App;
