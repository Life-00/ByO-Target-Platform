import React from 'react';

const Card = ({ children, className = '', glass = false }) => {
  return (
    <div className={`
      bg-white rounded-2xl border border-primary-100
      ${glass ? 'backdrop-blur-sm shadow-glass' : 'shadow-xl'}
      ${className}
    `}>
      {children}
    </div>
  );
};

export default Card;
