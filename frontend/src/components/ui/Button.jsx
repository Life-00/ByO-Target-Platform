import React from 'react';
import { Loader } from 'lucide-react';

const Button = ({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  isLoading = false, 
  disabled = false,
  icon: Icon,
  iconPosition = 'right',
  className = '',
  ...props 
}) => {
  const baseStyles = 'font-semibold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-gradient-to-r from-teal-600 to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white shadow-lg hover:shadow-xl transform hover:scale-[1.02] active:scale-95 disabled:from-gray-400 disabled:to-gray-500 disabled:shadow-none',
    secondary: 'border-2 border-teal-600 text-teal-600 hover:bg-teal-50 disabled:border-gray-300 disabled:text-gray-400',
    ghost: 'text-gray-600 hover:bg-gray-100 disabled:text-gray-400',
  };
  
  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3',
    lg: 'px-8 py-4 text-lg',
  };
  
  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader className={`${iconSizes[size]} animate-spin`} />
          로딩 중...
        </>
      ) : (
        <>
          {Icon && iconPosition === 'left' && <Icon className={iconSizes[size]} />}
          {children}
          {Icon && iconPosition === 'right' && <Icon className={iconSizes[size]} />}
        </>
      )}
    </button>
  );
};

export default Button;
