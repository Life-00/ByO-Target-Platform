import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, LogOut, Folder, Microscope, FileText, Calendar, Loader2 } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import sessionService from '../services/sessionService';

const Session = () => {
  const [sessions, setSessions] = useState([]);
  const [newSessionName, setNewSessionName] = useState('');
  const [newSessionDesc, setNewSessionDesc] = useState('');
  const [showNewForm, setShowNewForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const navigate = useNavigate();
  const { user, clearUser } = useAuthStore();

  // 세션 목록 로드
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    console.log('[Session] useEffect - Token exists:', !!token);
    console.log('[Session] useEffect - Token value:', token ? `${token.substring(0, 20)}...` : 'null');
    
    if (!token) {
      console.log('[Session] No token found, redirecting to login');
      navigate('/');
      return;
    }
    
    console.log('[Session] Token found, loading sessions...');
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSessions = async () => {
    console.log('[Session] loadSessions called');
    setIsLoading(true);
    setError('');
    try {
      const response = await sessionService.getSessions();
      console.log('[Session] Sessions loaded successfully:', response);
      setSessions(response.sessions || []);
    } catch (err) {
      console.error('[Session] Error loading sessions:', err);
      console.error('[Session] Error status:', err.status);
      console.error('[Session] Error message:', err.message);
      
      // 401 에러면 로그인 페이지로 리다이렉트
      if (err.status === 401 || err.message.includes('인증') || err.message.includes('토큰')) {
        console.log('[Session] Auth error detected, clearing token and redirecting');
        localStorage.removeItem('access_token');
        clearUser();
        navigate('/');
        return;
      }
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateSession = async (e) => {
    e.preventDefault();
    if (!newSessionName.trim()) return;

    setError('');
    try {
      const newSession = await sessionService.createSession({
        title: newSessionName,
        description: newSessionDesc || '',
      });
      setSessions([newSession, ...sessions]);
      setNewSessionName('');
      setNewSessionDesc('');
      setShowNewForm(false);
    } catch (err) {
      setError(err.message);
      console.error('Failed to create session:', err);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    if (!window.confirm('정말 이 세션을 삭제하시겠습니까?')) return;

    setError('');
    try {
      await sessionService.deleteSession(sessionId);
      setSessions(sessions.filter((s) => s.id !== sessionId));
    } catch (err) {
      setError(err.message);
      console.error('Failed to delete session:', err);
    }
  };

  const handleSelectSession = (sessionId) => {
    navigate(`/workspace/${sessionId}`);
  };

  const handleLogout = () => {
    clearUser();
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-teal-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-teal-100 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-5 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-teal-600 to-teal-700 rounded-xl flex items-center justify-center shadow-lg">
              <Microscope size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-teal-700 to-teal-600 bg-clip-text text-transparent">
                Target Validation Assistant
              </h1>
              <p className="text-sm text-slate-500">
                {user?.username || user?.email}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-slate-500 hover:text-red-600 px-2 py-1 transition font-semibold"
          >
            <LogOut className="w-4 h-4" />
            로그아웃
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-10">
        {/* Title Section */}
        <div className="mb-10">
          <h2 className="text-4xl font-bold text-slate-800 mb-3">연구 세션</h2>
          <p className="text-slate-600 text-lg">
            연구 주제별로 세션을 만들고 관리하세요
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl">
            {error}
          </div>
        )}

        {/* Loading State */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-12 h-12 text-teal-600 animate-spin mb-4" />
            <p className="text-slate-600">세션 목록을 불러오는 중...</p>
          </div>
        ) : (
          <>
            {/* Create New Session */}
        {!showNewForm ? (
          <button
            onClick={() => setShowNewForm(true)}
            className="mb-10 flex items-center gap-3 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white px-8 py-4 rounded-2xl transition font-bold shadow-lg hover:shadow-xl transform hover:scale-105"
          >
            <Plus className="w-6 h-6" />
            새 세션 만들기
          </button>
        ) : (
          <form onSubmit={handleCreateSession} className="mb-10 bg-white rounded-2xl shadow-xl p-8 border border-teal-100">
            <h3 className="text-2xl font-bold text-slate-800 mb-6 flex items-center gap-2">
              <Folder className="w-6 h-6 text-teal-600" />
              새 세션 만들기
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">세션 이름</label>
                <input
                  type="text"
                  value={newSessionName}
                  onChange={(e) => setNewSessionName(e.target.value)}
                  placeholder="예: COVID-19 치료제 연구"
                  className="w-full px-4 py-3 border-2 border-slate-200 rounded-xl focus:border-teal-600 focus:ring-2 focus:ring-teal-200 outline-none transition bg-slate-50 focus:bg-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">설명 (선택)</label>
                <input
                  type="text"
                  value={newSessionDesc}
                  onChange={(e) => setNewSessionDesc(e.target.value)}
                  placeholder="세션에 대한 간단한 설명"
                  className="w-full px-4 py-3 border-2 border-slate-200 rounded-xl focus:border-teal-600 focus:ring-2 focus:ring-teal-200 outline-none transition bg-slate-50 focus:bg-white"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  className="flex-1 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white px-6 py-3 rounded-xl transition font-bold shadow-lg"
                >
                  생성하기
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowNewForm(false);
                    setNewSessionName('');
                    setNewSessionDesc('');
                  }}
                  className="px-6 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition font-bold"
                >
                  취소
                </button>
              </div>
            </div>
          </form>
        )}

        {/* Sessions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="bg-white rounded-2xl shadow-lg hover:shadow-2xl transition-all overflow-hidden border border-teal-100 group hover:-translate-y-1"
            >
              {/* Card Header */}
              <div className="bg-gradient-to-br from-teal-600 to-teal-700 p-6 text-white relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16"></div>
                <div className="relative">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center backdrop-blur-sm">
                      <Folder className="w-5 h-5" />
                    </div>
                    <h3 className="font-bold text-xl flex-1">{session.title}</h3>
                  </div>
                  <p className="text-teal-100 text-sm leading-relaxed">{session.description || '설명 없음'}</p>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-6">
                <div className="space-y-3 mb-5">
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <Calendar className="w-4 h-4 text-teal-600" />
                    <span>{new Date(session.created_at).toLocaleDateString('ko-KR')}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <FileText className="w-4 h-4 text-teal-600" />
                    <span>문서 0개</span>
                  </div>
                </div>

                {/* Buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => handleSelectSession(session.id)}
                    className="flex-1 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white px-4 py-3 rounded-xl transition font-bold shadow-md hover:shadow-lg text-sm"
                  >
                    열기
                  </button>
                  <button
                    onClick={() => handleDeleteSession(session.id)}
                    className="text-slate-400 hover:text-red-600 px-3 py-3 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {sessions.length === 0 && !isLoading && (
          <div className="text-center py-20 bg-white rounded-2xl shadow-xl border border-teal-100">
            <div className="w-20 h-20 bg-teal-50 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Folder className="w-10 h-10 text-teal-600" />
            </div>
            <h3 className="text-2xl font-bold text-slate-800 mb-3">
              아직 세션이 없습니다
            </h3>
            <p className="text-slate-600 mb-8 text-lg">
              첫 번째 연구 세션을 만들어보세요
            </p>
            <button
              onClick={() => setShowNewForm(true)}
              className="inline-flex items-center gap-3 bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white px-8 py-4 rounded-2xl transition font-bold shadow-lg hover:shadow-xl transform hover:scale-105"
            >
              <Plus className="w-5 h-5" />
              첫 세션 만들기
            </button>
          </div>
        )}
          </>
        )}
      </main>
    </div>
  );
};

export default Session;
