import { useCallback } from 'react';
import { useErrorOperations, ErrorItem, createNetworkError, createApiError } from '../store/useErrorStore';

/**
 * Enhanced Error Handler Hook
 * Provides utilities for handling different types of errors with context
 */
export const useErrorHandler = () => {
  const { addError, addNetworkError, addValidationError, addApiError, addAuthError } = useErrorOperations();

  /**
   * Handle async operation errors with automatic error type detection
   */
  const handleAsyncError = useCallback((error: unknown, context?: {
    operation?: string;
    component?: string;
    action?: string;
  }) => {
    if (error instanceof Error) {
      // Network/Connection errors
      if (error.message.includes('fetch') || error.message.includes('network') || error.name === 'NetworkError') {
        addNetworkError(
          error.message || 'Network connection error',
          JSON.stringify({ stack: error.stack, context })
        );
        return;
      }

      // API errors (if error contains status codes or API-related messages)
      if (error.message.includes('40') || error.message.includes('50') || error.message.includes('API')) {
        addApiError(
          error.message || 'API request failed',
          context?.action || context?.operation
        );
        return;
      }

      // Authentication errors
      if (error.message.includes('auth') || error.message.includes('unauthorized') || error.message.includes('403')) {
        addAuthError(error.message || 'Authentication failed');
        return;
      }

      // Generic runtime error
      addError({
        type: 'runtime',
        message: error.message || 'An unexpected error occurred',
        details: JSON.stringify({ 
          name: error.name,
          stack: error.stack,
          context 
        }),
        timestamp: new Date(),
        severity: 'medium',
        component: context?.component,
        action: context?.action,
        dismissible: true,
        autoHide: false
      });
    } else {
      // Handle non-Error objects
      addError({
        type: 'unknown',
        message: typeof error === 'string' ? error : 'An unknown error occurred',
        details: JSON.stringify({ error, context }),
        timestamp: new Date(),
        severity: 'medium',
        component: context?.component,
        dismissible: true,
        autoHide: true,
        duration: 5000
      });
    }
  }, [addError, addNetworkError, addApiError, addAuthError]);

  /**
   * Handle API response errors with status code handling
   */
  const handleApiResponse = useCallback(async (response: Response, context?: {
    endpoint?: string;
    method?: string;
    component?: string;
  }) => {
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      let errorDetails = '';

      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorData.detail || errorMessage;
        errorDetails = JSON.stringify({ ...errorData, context });
      } catch {
        // Response doesn't contain JSON, use default message
        errorDetails = JSON.stringify({ 
          status: response.status,
          statusText: response.statusText,
          url: response.url,
          context
        });
      }

      const severity: ErrorItem['severity'] = 
        response.status >= 500 ? 'critical' :
        response.status >= 400 ? 'high' : 'medium';

      if (response.status === 401 || response.status === 403) {
        addAuthError(errorMessage);
      } else {
        addApiError(errorMessage, context?.endpoint);
      }

      throw new Error(errorMessage);
    }
    return response;
  }, [addApiError, addAuthError]);

  /**
   * Wrapper for API calls with automatic error handling
   */
  const withErrorHandling = useCallback(<T>(
    apiCall: () => Promise<T>,
    context?: {
      operation?: string;
      component?: string;
      onError?: (error: Error) => void;
    }
  ) => {
    return async (): Promise<T | null> => {
      try {
        return await apiCall();
      } catch (error) {
        handleAsyncError(error, {
          operation: context?.operation,
          component: context?.component
        });

        if (context?.onError && error instanceof Error) {
          context.onError(error);
        }

        return null;
      }
    };
  }, [handleAsyncError]);

  /**
   * Enhanced fetch wrapper with automatic error handling
   */
  const fetchWithErrorHandling = useCallback(async (
    url: string, 
    options?: RequestInit,
    context?: {
      operation?: string;
      component?: string;
    }
  ) => {
    try {
      const response = await fetch(url, options);
      await handleApiResponse(response, {
        endpoint: url,
        method: options?.method || 'GET',
        component: context?.component
      });
      return response;
    } catch (error) {
      // If it's not already handled by handleApiResponse, handle it here
      if (error instanceof TypeError && error.message.includes('fetch')) {
        addNetworkError(
          'Failed to connect to server. Please check your internet connection.',
          JSON.stringify({ url, options, context })
        );
      } else {
        handleAsyncError(error, context);
      }
      throw error;
    }
  }, [handleApiResponse, addNetworkError, handleAsyncError]);

  /**
   * Form validation error handler
   */
  const handleValidationErrors = useCallback((
    validationErrors: Record<string, string | string[]>,
    component?: string
  ) => {
    Object.entries(validationErrors).forEach(([field, messages]) => {
      const messageArray = Array.isArray(messages) ? messages : [messages];
      messageArray.forEach(message => {
        addValidationError(`${field}: ${message}`, component);
      });
    });
  }, [addValidationError]);

  /**
   * Retry mechanism for failed operations
   */
  const withRetry = useCallback(<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    delay: number = 1000,
    context?: { component?: string; operation?: string }
  ) => {
    return async (): Promise<T | null> => {
      let lastError: Error | null = null;

      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          return await operation();
        } catch (error) {
          lastError = error instanceof Error ? error : new Error(String(error));
          
          if (attempt === maxRetries) {
            // Final attempt failed, log error
            handleAsyncError(lastError, {
              ...context,
              action: `Failed after ${maxRetries} attempts`
            });
            break;
          }

          // Wait before retry (exponential backoff)
          await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt - 1)));
        }
      }

      return null;
    };
  }, [handleAsyncError]);

  return {
    handleAsyncError,
    handleApiResponse,
    withErrorHandling,
    fetchWithErrorHandling,
    handleValidationErrors,
    withRetry,
    // Direct access to error operations
    addError,
    addNetworkError,
    addValidationError,
    addApiError,
    addAuthError
  };
};