import React, { useEffect, useState } from 'react';
import { ErrorItem, useErrorStore } from '../store/useErrorStore';

interface ToastProps {
  error: ErrorItem;
  onClose: () => void;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
}

/**
 * Individual Toast Component
 * Displays a single toast notification for an error
 */
const Toast: React.FC<ToastProps> = ({ 
  error, 
  onClose, 
  position = 'top-right' 
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    // Animate in
    setIsVisible(true);

    // Auto-hide if configured
    if (error.autoHide && error.duration) {
      const timer = setTimeout(() => {
        handleClose();
      }, error.duration);
      return () => clearTimeout(timer);
    }
  }, [error.autoHide, error.duration]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => {
      onClose();
    }, 200); // Allow exit animation to complete
  };

  const getToastStyles = () => {
    let baseStyles = 'fixed z-50 max-w-sm w-full shadow-lg rounded-lg pointer-events-auto transform transition-all duration-200 ';
    
    // Position styles
    switch (position) {
      case 'top-right':
        baseStyles += 'top-4 right-4 ';
        break;
      case 'top-left':
        baseStyles += 'top-4 left-4 ';
        break;
      case 'bottom-right':
        baseStyles += 'bottom-4 right-4 ';
        break;
      case 'bottom-left':
        baseStyles += 'bottom-4 left-4 ';
        break;
      case 'top-center':
        baseStyles += 'top-4 left-1/2 transform -translate-x-1/2 ';
        break;
      case 'bottom-center':
        baseStyles += 'bottom-4 left-1/2 transform -translate-x-1/2 ';
        break;
    }

    // Animation states
    if (isExiting) {
      baseStyles += 'opacity-0 scale-95 ';
    } else if (isVisible) {
      baseStyles += 'opacity-100 scale-100 ';
    } else {
      baseStyles += 'opacity-0 scale-95 ';
    }

    // Severity-based styles
    switch (error.severity) {
      case 'critical':
        baseStyles += 'bg-red-600 text-white ';
        break;
      case 'high':
        baseStyles += 'bg-red-500 text-white ';
        break;
      case 'medium':
        baseStyles += 'bg-yellow-500 text-white ';
        break;
      case 'low':
        baseStyles += 'bg-blue-500 text-white ';
        break;
      default:
        baseStyles += 'bg-gray-600 text-white ';
    }

    return baseStyles;
  };

  const getIcon = () => {
    switch (error.severity) {
      case 'critical':
      case 'high':
        return (
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'medium':
        return (
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
      case 'low':
        return (
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className={getToastStyles()} role="alert" aria-live="assertive">
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {getIcon()}
          </div>
          
          <div className="ml-3 flex-1">
            <p className="text-sm font-medium capitalize">
              {error.type} Error
            </p>
            <p className="mt-1 text-sm opacity-90">
              {error.message}
            </p>
          </div>
          
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={handleClose}
              className="inline-flex text-white hover:text-gray-200 focus:outline-none focus:text-gray-200 transition-colors duration-150"
              aria-label="Close notification"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Toast Container Component
 * Manages and displays all active toast notifications
 */
interface ToastContainerProps {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
  maxToasts?: number;
}

const ToastContainer: React.FC<ToastContainerProps> = ({ 
  position = 'top-right',
  maxToasts = 5 
}) => {
  const errors = useErrorStore((state) => state.errors);
  const removeError = useErrorStore((state) => state.removeError);

  // Only show dismissible errors as toasts and limit the number
  const toastErrors = errors
    .filter(error => error.dismissible)
    .slice(-maxToasts); // Show only the most recent toasts

  const getContainerPosition = () => {
    switch (position) {
      case 'top-right':
      case 'top-left':
      case 'top-center':
        return 'flex-col';
      case 'bottom-right':
      case 'bottom-left':
      case 'bottom-center':
        return 'flex-col-reverse';
      default:
        return 'flex-col';
    }
  };

  if (toastErrors.length === 0) {
    return null;
  }

  return (
    <div 
      className={`fixed inset-0 z-40 pointer-events-none overflow-hidden`}
      aria-live="polite"
      aria-label="Notifications"
    >
      <div className={`flex ${getContainerPosition()} space-y-2 p-4`}>
        {toastErrors.map((error) => (
          <Toast
            key={error.id}
            error={error}
            position={position}
            onClose={() => removeError(error.id)}
          />
        ))}
      </div>
    </div>
  );
};

export default ToastContainer;
export { Toast };