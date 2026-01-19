import React from 'react';
import { AlertCircle, CheckCircle, Info, XCircle } from 'lucide-react';

const variants = {
  error: {
    bg: 'bg-red-50',
    border: 'border-red-500',
    text: 'text-red-700',
    icon: XCircle,
  },
  success: {
    bg: 'bg-green-50',
    border: 'border-green-500',
    text: 'text-green-700',
    icon: CheckCircle,
  },
  warning: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-500',
    text: 'text-yellow-700',
    icon: AlertCircle,
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-500',
    text: 'text-blue-700',
    icon: Info,
  },
};

const Alert = ({ type = 'error', children, className = '' }) => {
  const variant = variants[type];
  const Icon = variant.icon;

  return (
    <div className={`
      ${variant.bg} ${variant.text} ${variant.border}
      border-l-4 px-4 py-3 rounded-lg
      flex items-start gap-3
      animate-shake
      ${className}
    `}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <span className="text-sm flex-1">{children}</span>
    </div>
  );
};

export default Alert;
