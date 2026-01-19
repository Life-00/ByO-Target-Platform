import React, { forwardRef, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

const Input = forwardRef(({
  label,
  type = 'text',
  error,
  hint,
  icon: Icon,
  className = '',
  showPasswordToggle = false,
  ...props
}, ref) => {
  const [showPassword, setShowPassword] = useState(false);
  const inputType = showPasswordToggle ? (showPassword ? 'text' : 'password') : type;

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-semibold text-secondary-700 mb-2.5">
          {label}
        </label>
      )}
      
      <div className="relative group">
        {Icon && (
          <Icon className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-primary-500 transition group-focus-within:text-primary-600" />
        )}
        
        <input
          ref={ref}
          type={inputType}
          className={`
            w-full py-3 border-2 rounded-xl transition
            bg-secondary-50 focus:bg-white
            border-secondary-200 focus:border-primary-500
            focus:outline-none focus:ring-2 focus:ring-primary-200
            disabled:opacity-50 disabled:cursor-not-allowed
            ${Icon ? 'pl-12' : 'pl-4'}
            ${showPasswordToggle ? 'pr-10' : 'pr-4'}
            ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-200' : ''}
            ${className}
          `}
          {...props}
        />
        
        {showPasswordToggle && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-4 top-1/2 transform -translate-y-1/2 text-secondary-400 hover:text-secondary-600 transition"
          >
            {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        )}
      </div>
      
      {error && (
        <p className="mt-1.5 text-sm text-red-600 animate-shake">{error}</p>
      )}
      
      {hint && !error && (
        <p className="mt-1.5 text-xs text-secondary-500">{hint}</p>
      )}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;
