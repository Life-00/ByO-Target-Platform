import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Microscope, ArrowRight, Loader2 } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import authService from '../services/authService';

const Register = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const navigate = useNavigate();
  const { setUser } = useAuthStore();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!username || !email || !password || !confirmPassword) {
      setError('모든 필수 필드를 입력하세요.');
      return;
    }

    if (username.length < 3 || username.length > 50) {
      setError('사용자명은 3자 이상 50자 이하여야 합니다.');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('유효한 이메일을 입력하세요.');
      return;
    }

    if (password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다.');
      return;
    }

    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }

    setIsLoading(true);

    try {
      await authService.register({
        username,
        email,
        password,
      });

      // 회원가입 성공 후 로그인 페이지로 이동
      navigate('/', { state: { message: '회원가입이 완료되었습니다. 로그인해주세요.' } });
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
        <p className="text-slate-500 text-sm mb-8">TVA와 함께 시작하세요</p>

        <form onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 p-3 rounded-lg mb-4 text-sm text-left">
              {error}
            </div>
          )}

          <div className="mb-4 text-left">
            <input
              className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-base outline-none transition-all focus:border-teal-700 focus:bg-white"
              type="text"
              placeholder="사용자명"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>

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
              autoComplete="new-password"
            />
          </div>

          <div className="mb-4 text-left">
            <input
              className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-base outline-none transition-all focus:border-teal-700 focus:bg-white"
              type="password"
              placeholder="비밀번호 확인"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
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
              <>회원가입</>
            )}
            {!isLoading && <ArrowRight size={20} />}
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-slate-100">
          <Link to="/">
            <button className="bg-transparent border-none text-teal-700 cursor-pointer font-semibold text-sm hover:opacity-80 transition-opacity">
              기존 계정으로 로그인
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Register;
