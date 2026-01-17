import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

const Input = ({ 
  label, 
  type = 'text', 
  icon: Icon,
  error,
  helpText,
  showPasswordToggle = false,
  className = '',
  ...props 
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const inputType = showPasswordToggle && showPassword ? 'text' : type;

  return (
    <div className={`space-y-2 ${className}`}>
      {label && (
        <label className="block text-sm font-semibold text-gray-700">
          {label}
        </label>
      )}
      
      <div className="relative group">
        {Icon && (
          <Icon className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-teal-500 transition-colors group-focus-within:text-teal-600" />
        )}
        
        <input
          type={inputType}
          className={`
            w-full ${Icon ? 'pl-12' : 'pl-4'} ${showPasswordToggle ? 'pr-12' : 'pr-4'} py-3
            border-2 rounded-xl transition-all duration-200
            bg-gray-50 focus:bg-white
            ${error 
              ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-200' 
              : 'border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-200'
            }
            outline-none
            placeholder:text-gray-400
          `}
          {...props}
        />
        
        {showPasswordToggle && type === 'password' && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
          >
            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        )}
      </div>
      
      {helpText && !error && (
        <p className="text-xs text-gray-500 ml-1">{helpText}</p>
      )}
      
      {error && (
        <p className="text-xs text-red-600 ml-1 animate-shake">{error}</p>
      )}
    </div>
  );
};

export default Input;
