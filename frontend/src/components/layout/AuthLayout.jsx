import React from 'react';

const AuthLayout = ({ children, title, subtitle, icon = 'T', footer }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-primary-50 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md animate-fadeIn">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 mb-6 shadow-lg hover:shadow-glow transition-shadow">
            <span className="text-2xl font-bold text-white">{icon}</span>
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary-700 to-primary-600 bg-clip-text text-transparent mb-2">
            {title}
          </h1>
          {subtitle && (
            <p className="text-secondary-500 text-sm">{subtitle}</p>
          )}
        </div>

        {/* Content */}
        {children}

        {/* Footer */}
        {footer && (
          <div className="mt-8 text-center text-sm text-secondary-500">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

export default AuthLayout;
