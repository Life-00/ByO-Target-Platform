import React from 'react';

const PasswordStrength = ({ password }) => {
  const getStrength = (pwd) => {
    if (!pwd) return 0;
    let strength = 0;
    if (pwd.length >= 8) strength++;
    if (pwd.length >= 12) strength++;
    if (/[a-z]/.test(pwd) && /[A-Z]/.test(pwd)) strength++;
    if (/[0-9]/.test(pwd)) strength++;
    if (/[^a-zA-Z0-9]/.test(pwd)) strength++;
    return Math.min(strength, 4);
  };

  const strength = getStrength(password);
  const colors = ['bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-teal-500'];
  const labels = ['약함', '보통', '양호', '강력'];

  if (!password) return null;

  return (
    <div className="space-y-2">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
              i < strength ? colors[strength - 1] : 'bg-gray-200'
            }`}
          />
        ))}
      </div>
      {strength > 0 && (
        <p className={`text-xs font-medium ${
          strength === 1 ? 'text-red-600' :
          strength === 2 ? 'text-orange-600' :
          strength === 3 ? 'text-yellow-600' :
          'text-teal-600'
        }`}>
          비밀번호 강도: {labels[strength - 1]}
        </p>
      )}
    </div>
  );
};

export default PasswordStrength;
