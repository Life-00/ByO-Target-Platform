import React, { useState } from "react";
import { Microscope, ArrowRight, Loader2 } from "lucide-react";
import api from "../../api";
import "./AuthContainer.css";

const AuthContainer = ({ onLoginSuccess }) => {
  const [mode, setMode] = useState("login");
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    name: "",
  });

  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    console.log(`[FRONT] Attempting ${mode} via centralized API client`);

    try {
      if (mode === "signup") {
        await api.post("/auth/signup", formData);
        alert("회원가입 성공! 로그인해 주세요.");
        setMode("login");
      } else {
        const response = await api.post("/auth/login", {
          email: formData.email,
          password: formData.password,
        });

        localStorage.setItem("token", response.data.access_token);
        onLoginSuccess();
      }
    } catch (error) {
      console.error("[FRONT-ERROR]", error.response?.data || error.message);
      alert("이메일을 확인해주세요");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-icon-box">
          <Microscope size={40} />
        </div>
        <h2 className="auth-title">Target Validation Assistant</h2>
        <p style={{ color: "#64748b", fontSize: "14px", marginBottom: "32px" }}>
          Team 5: ByO
        </p>

        <form onSubmit={handleSubmit}>
          {mode === "signup" && (
            <div className="auth-input-group">
              <input
                className="auth-input"
                type="text"
                placeholder="이름"
                required
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
              />
            </div>
          )}
          <div className="auth-input-group">
            <input
              className="auth-input"
              type="email"
              placeholder="이메일"
              required
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
            />
          </div>
          <div className="auth-input-group">
            <input
              className="auth-input"
              type="password"
              placeholder="비밀번호"
              required
              onChange={(e) =>
                setFormData({ ...formData, password: e.target.value })
              }
            />
          </div>

          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <>{mode === "login" ? "로그인" : "회원 가입"}</>
            )}
            {!isLoading && <ArrowRight size={20} />}
          </button>
        </form>

        <div
          style={{
            marginTop: "24px",
            paddingTop: "20px",
            borderTop: "1px solid #f1f5f9",
          }}
        >
          <button
            onClick={() => setMode(mode === "login" ? "signup" : "login")}
            style={{
              background: "none",
              border: "none",
              color: "var(--bio-primary)",
              cursor: "pointer",
              fontWeight: "600",
            }}
          >
            {mode === "login" ? "회원가입" : "기존 계정으로 로그인"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthContainer;
