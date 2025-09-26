import type { AppProps } from 'next/app';
import { useEffect } from 'react';
import ErrorBoundary from '../components/ErrorBoundary';
import ToastContainer from '../components/ToastNotification';
import { useErrorHandler } from '../hooks/useErrorHandler';
import '../styles/globals.css';

/**
 * Global Error Fallback Component
 * Displayed when the error boundary catches an error
 */
const GlobalErrorFallback: React.FC<{ error: Error; resetError: () => void }> = ({ 
  error, 
  resetError 
}) => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4">
      <div className="max-w-md w-full space-y-8 text-center">
        <div>
          <div className="mx-auto h-16 w-16 text-red-500 mb-4">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={1} 
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Application Error
          </h1>
          <p className="text-gray-600 mb-6">
            Something went wrong with the SuperMean application. Please try refreshing the page or contact support if the problem persists.
          </p>
        </div>
        
        <div className="space-y-4">
          <button
            onClick={resetError}
            className="w-full bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors"
          >
            Try Again
          </button>
          
          <button
            onClick={() => window.location.reload()}
            className="w-full bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
          >
            Refresh Page
          </button>
          
          <button
            onClick={() => window.location.href = '/'}
            className="w-full bg-white text-gray-700 px-4 py-2 rounded-md border border-gray-300 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors"
          >
            Go to Home
          </button>
        </div>

        {process.env.NODE_ENV === 'development' && (
          <details className="mt-8 text-left">
            <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-gray-900 mb-2">
              Developer Information
            </summary>
            <div className="bg-gray-100 p-4 rounded-md text-xs">
              <div className="font-semibold text-red-600 mb-2">Error Message:</div>
              <div className="mb-4">{error.message}</div>
              <div className="font-semibold text-red-600 mb-2">Stack Trace:</div>
              <pre className="whitespace-pre-wrap">{error.stack}</pre>
            </div>
          </details>
        )}
      </div>
    </div>
  );
};

/**
 * Main App Component with Global Error Handling
 */
function SuperMeanApp({ Component, pageProps }: AppProps) {
  const { handleAsyncError } = useErrorHandler();

  useEffect(() => {
    // Global error handlers for unhandled errors
    
    // Handle unhandled promise rejections
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error('Unhandled promise rejection:', event.reason);
      handleAsyncError(event.reason, {
        operation: 'unhandled_promise_rejection',
        component: 'global'
      });
    };

    // Handle global JavaScript errors
    const handleGlobalError = (event: ErrorEvent) => {
      console.error('Global error:', event.error);
      handleAsyncError(event.error || new Error(event.message), {
        operation: 'global_error',
        component: 'global'
      });
    };

    // Add event listeners
    window.addEventListener('unhandledrejection', handleUnhandledRejection);
    window.addEventListener('error', handleGlobalError);

    // Cleanup
    return () => {
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
      window.removeEventListener('error', handleGlobalError);
    };
  }, [handleAsyncError]);

  // Handle custom error boundary errors
  const handleErrorBoundaryError = (error: Error, errorInfo: React.ErrorInfo) => {
    // Log to external service in production
    console.error('Error Boundary caught error:', error, errorInfo);
    
    // You can integrate with error reporting services here
    // Example: Sentry.captureException(error, { extra: errorInfo });
  };

  return (
    <ErrorBoundary 
      fallback={GlobalErrorFallback}
      onError={handleErrorBoundaryError}
    >
      <div className="min-h-screen bg-gray-50">
        <Component {...pageProps} />
        
        {/* Global Toast Notifications */}
        <ToastContainer 
          position="top-right" 
          maxToasts={3}
        />
      </div>
    </ErrorBoundary>
  );
}

export default SuperMeanApp;