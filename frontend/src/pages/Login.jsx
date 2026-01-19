import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Microscope, ArrowRight, Loader2 } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import authService from '../services/authService';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const navigate = useNavigate();
  const { setUser } = useAuthStore();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('이메일과 비밀번호를 입력하세요.');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('유효한 이메일을 입력하세요.');
      return;
    }

    setIsLoading(true);

    try {
      const response = await authService.login(email, password);
      
      console.log('Login response:', response);
      
      setUser({
        id: response.user.id,
        email: response.user.email,
        username: response.user.username,
      });

      console.log('Navigating to /session');
      navigate('/session');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-5 bg-slate-50">
      <div className="bg-white w-full max-w-[420px] p-10 rounded-3xl shadow-lg border border-slate-100 text-center">
        <div className="w-20 h-20 bg-teal-700 rounded-2xl inline-flex items-center justify-center mb-6 text-white rotate-3 hover:rotate-0 transition-transform">
          <Microscope size={40} />
        </div>
        <h2 className="text-2xl font-extrabold text-slate-800 mb-2">Target Validation Assistant</h2>
        <p className="text-slate-500 text-sm mb-8">TVA에 접속하세요</p>

        <form onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 p-3 rounded-lg mb-4 text-sm text-left">
              {error}
            </div>
          )}

          <div className="mb-4 text-left">
            <input
              className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-base outline-none transition-all focus:border-teal-700 focus:bg-white"
              type="email"
              placeholder="이메일"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>

          <div className="mb-4 text-left">
            <input
              className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-base outline-none transition-all focus:border-teal-700 focus:bg-white"
              type="password"
              placeholder="비밀번호"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          <button 
            type="submit" 
            className="w-full px-4 py-3.5 bg-teal-700 text-white border-none rounded-xl text-base font-bold cursor-pointer flex items-center justify-center gap-2.5 transition-opacity hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed mt-2"
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <>로그인</>
            )}
            {!isLoading && <ArrowRight size={20} />}
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-slate-100">
          <Link to="/register">
            <button className="bg-transparent border-none text-teal-700 cursor-pointer font-semibold text-sm hover:opacity-80 transition-opacity">
              회원가입
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Login;
