import React from 'react';

const Divider = ({ children, className = '' }) => {
  if (!children) {
    return <div className={`h-px bg-secondary-200 ${className}`} />;
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="flex-1 h-px bg-secondary-200" />
      <span className="text-xs text-secondary-500 font-medium">{children}</span>
      <div className="flex-1 h-px bg-secondary-200" />
    </div>
  );
};

export default Divider;
