import React from 'react';

const AuthLayout = ({ children, title, subtitle }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-teal-50 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-10 animate-fadeIn">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-teal-500 to-teal-700 mb-6 shadow-2xl transform hover:scale-105 transition-transform duration-300">
            <span className="text-3xl font-bold text-white">T</span>
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-teal-700 via-teal-600 to-teal-700 bg-clip-text text-transparent mb-3 animate-slideDown">
            {title}
          </h1>
          <p className="text-gray-500 animate-slideDown" style={{ animationDelay: '0.1s' }}>
            {subtitle}
          </p>
        </div>

        {/* Content */}
        <div className="animate-slideUp">
          {children}
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
