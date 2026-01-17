import React from 'react';

const Card = ({ children, className = '', ...props }) => {
  return (
    <div
      className={`
        bg-white rounded-2xl shadow-xl backdrop-blur-sm 
        border border-teal-100 p-8
        ${className}
      `}
      {...props}
    >
      {children}
    </div>
  );
};

export default Card;
