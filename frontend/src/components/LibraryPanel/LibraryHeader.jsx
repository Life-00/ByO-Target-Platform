import React from 'react';
import { Microscope } from 'lucide-react';

const LibraryHeader = () => {
  return (
    <div className="h-16 flex items-center px-4 border-b border-gray-200 bg-white shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-teal-700 rounded-xl flex items-center justify-center shadow-sm text-white">
          <Microscope size={22} />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-sm text-teal-700">Target Validation</span>
          <span className="font-bold text-sm text-gray-900">Assistant</span>
        </div>
      </div>
    </div>
  );
};

export default React.memo(LibraryHeader);
