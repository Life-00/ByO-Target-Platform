import React from 'react';

const getPasswordStrength = (password) => {
  if (!password) return 0;
  let strength = 0;
  if (password.length >= 8) strength++;
  if (password.length >= 12) strength++;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
  if (/[0-9]/.test(password)) strength++;
  return strength;
};

const strengthConfig = [
  { color: 'bg-red-500', label: '약함' },
  { color: 'bg-orange-500', label: '보통' },
  { color: 'bg-yellow-500', label: '양호' },
  { color: 'bg-primary-500', label: '강함' },
];

const PasswordStrength = ({ password, className = '' }) => {
  const strength = getPasswordStrength(password);

  if (!password) return null;

  return (
    <div className={`mt-2 ${className}`}>
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-300 ${
              i < strength ? strengthConfig[strength - 1].color : 'bg-secondary-200'
            }`}
          />
        ))}
      </div>
      {strength > 0 && (
        <p className="text-xs text-secondary-500 mt-1.5">
          비밀번호 강도: <span className="font-medium">{strengthConfig[strength - 1].label}</span>
        </p>
      )}
    </div>
  );
};

export default PasswordStrength;
