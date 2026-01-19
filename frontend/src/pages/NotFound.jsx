import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, AlertCircle } from 'lucide-react';

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        {/* Icon */}
        <div className="mb-6">
          <AlertCircle className="w-20 h-20 text-red-500 mx-auto animate-bounce" />
        </div>

        {/* Title */}
        <h1 className="text-6xl font-bold text-gray-900 mb-2">404</h1>
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">
          페이지를 찾을 수 없습니다.
        </h2>

        {/* Description */}
        <p className="text-gray-600 mb-8">
          요청하신 페이지가 존재하지 않거나 이동되었을 수 있습니다.
          <br />
          홈페이지로 돌아가서 다시 시작해주세요.
        </p>

        {/* Action Buttons */}
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={() => navigate('/')}
            className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition font-semibold"
          >
            <Home className="w-5 h-5" />
            홈으로 이동
          </button>
          <button
            onClick={() => window.history.back()}
            className="flex items-center justify-center gap-2 bg-gray-200 hover:bg-gray-300 text-gray-800 px-6 py-3 rounded-lg transition font-semibold"
          >
            이전 페이지
          </button>
        </div>

        {/* Additional Info */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>문제가 지속되면 고객 지원팀에 문의하세요.</p>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
