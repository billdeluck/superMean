import React from 'react';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: 'primary' | 'secondary' | 'white' | 'gray';
  className?: string;
  label?: string;
}

/**
 * Loading Spinner Component
 * Displays an animated loading spinner with customizable size and color
 */
const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  color = 'primary',
  className = '',
  label = 'Loading...'
}) => {
  const getSizeClasses = () => {
    switch (size) {
      case 'small':
        return 'h-4 w-4';
      case 'medium':
        return 'h-8 w-8';
      case 'large':
        return 'h-12 w-12';
      default:
        return 'h-8 w-8';
    }
  };

  const getColorClasses = () => {
    switch (color) {
      case 'primary':
        return 'text-indigo-600';
      case 'secondary':
        return 'text-gray-600';
      case 'white':
        return 'text-white';
      case 'gray':
        return 'text-gray-400';
      default:
        return 'text-indigo-600';
    }
  };

  return (
    <div 
      className={`inline-flex items-center justify-center ${className}`}
      role="status" 
      aria-label={label}
    >
      <svg
        className={`animate-spin ${getSizeClasses()} ${getColorClasses()}`}
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <span className="sr-only">{label}</span>
    </div>
  );
};

/**
 * Full Page Loading Spinner
 * Displays a centered loading spinner that covers the entire viewport
 */
interface FullPageLoadingProps {
  message?: string;
  showBackground?: boolean;
}

export const FullPageLoading: React.FC<FullPageLoadingProps> = ({
  message = 'Loading...',
  showBackground = true
}) => {
  return (
    <div 
      className={`fixed inset-0 z-50 flex items-center justify-center ${
        showBackground ? 'bg-gray-50 bg-opacity-75' : ''
      }`}
      role="status"
      aria-label={message}
    >
      <div className="flex flex-col items-center space-y-4">
        <LoadingSpinner size="large" color="primary" />
        {message && (
          <p className="text-sm text-gray-600 font-medium">
            {message}
          </p>
        )}
      </div>
    </div>
  );
};

/**
 * Button Loading Spinner
 * Small spinner designed to be used inside buttons
 */
interface ButtonLoadingProps {
  className?: string;
}

export const ButtonLoading: React.FC<ButtonLoadingProps> = ({ 
  className = '' 
}) => {
  return (
    <LoadingSpinner 
      size="small" 
      color="white" 
      className={className}
      label="Processing..."
    />
  );
};

/**
 * Inline Loading Spinner
 * Small spinner for inline loading states
 */
interface InlineLoadingProps {
  text?: string;
  className?: string;
}

export const InlineLoading: React.FC<InlineLoadingProps> = ({ 
  text = 'Loading...', 
  className = '' 
}) => {
  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <LoadingSpinner size="small" color="gray" />
      <span className="text-sm text-gray-600">{text}</span>
    </div>
  );
};

export default LoadingSpinner;