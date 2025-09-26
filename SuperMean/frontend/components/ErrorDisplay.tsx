import React from 'react';
import { ErrorItem } from '../store/useErrorStore';

interface ErrorDisplayProps {
  error: ErrorItem;
  onDismiss?: () => void;
  onRetry?: () => void;
  className?: string;
  showDetails?: boolean;
}

/**
 * Error Display Component
 * Displays individual error messages with appropriate styling based on severity
 */
const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onDismiss,
  onRetry,
  className = '',
  showDetails = false
}) => {
  const getSeverityStyles = (severity: ErrorItem['severity']) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'high':
        return 'bg-red-50 border-red-200 text-red-700';
      case 'medium':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'low':
        return 'bg-blue-50 border-blue-200 text-blue-700';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-700';
    }
  };

  const getIconBySeverity = (severity: ErrorItem['severity']) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return (
          <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'medium':
        return (
          <svg className="h-5 w-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
      case 'low':
        return (
          <svg className="h-5 w-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return (
          <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  return (
    <div className={`border rounded-lg p-4 ${getSeverityStyles(error.severity)} ${className}`}>
      <div className="flex">
        <div className="flex-shrink-0">
          {getIconBySeverity(error.severity)}
        </div>
        
        <div className="ml-3 flex-1">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <h3 className="text-sm font-medium capitalize">
                {error.type} Error
              </h3>
              <p className="mt-1 text-sm">
                {error.message}
              </p>
              
              {error.component && (
                <p className="mt-1 text-xs opacity-75">
                  Component: {error.component}
                </p>
              )}
              
              {error.action && (
                <p className="mt-1 text-xs opacity-75">
                  Action: {error.action}
                </p>
              )}
              
              {showDetails && error.details && (
                <details className="mt-2">
                  <summary className="text-xs cursor-pointer opacity-75 hover:opacity-100">
                    Show Details
                  </summary>
                  <pre className="mt-1 text-xs opacity-75 whitespace-pre-wrap">
                    {error.details}
                  </pre>
                </details>
              )}
              
              <p className="mt-1 text-xs opacity-60">
                {error.timestamp.toLocaleString()}
              </p>
            </div>
            
            <div className="flex space-x-2 ml-4">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="text-sm underline hover:no-underline focus:outline-none"
                  aria-label="Retry action"
                >
                  Retry
                </button>
              )}
              
              {error.dismissible && onDismiss && (
                <button
                  onClick={onDismiss}
                  className="text-sm underline hover:no-underline focus:outline-none"
                  aria-label="Dismiss error"
                >
                  Dismiss
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ErrorDisplay;