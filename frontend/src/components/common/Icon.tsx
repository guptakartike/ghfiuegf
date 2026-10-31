import React from 'react';

interface IconProps {
  name: string;
  className?: string;
}

export const Icon: React.FC<IconProps> = ({ name, className = '' }) => {
  return (
    <span
      className={`material-symbols-outlined select-none text-[18px] leading-none ${className}`}
      aria-hidden="true"
    >
      {name}
    </span>
  );
};

