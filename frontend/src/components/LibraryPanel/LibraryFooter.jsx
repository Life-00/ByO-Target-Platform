import React from 'react';
import { Settings, LogOut } from 'lucide-react';

const LibraryFooter = ({ onSettings, onLogout }) => {
  return (
    <div className="p-4 border-t border-gray-200 bg-white shrink-0 flex justify-between items-center">
      <button
        onClick={onSettings}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors p-2 rounded-lg hover:bg-gray-50"
      >
        <Settings size={18} />
        <span>설정</span>
      </button>
      <button
        onClick={onLogout}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-red-600 transition-colors p-2 rounded-lg hover:bg-red-50"
      >
        <LogOut size={18} />
        <span>로그아웃</span>
      </button>
    </div>
  );
};

export default React.memo(LibraryFooter);
