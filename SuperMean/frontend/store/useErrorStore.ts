import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

/**
 * Error Item Interface
 * Represents a single error in the application
 */
export interface ErrorItem {
  id: string;
  type: 'network' | 'validation' | 'runtime' | 'auth' | 'api' | 'unknown';
  message: string;
  details?: string;
  timestamp: Date;
  severity: 'low' | 'medium' | 'high' | 'critical';
  component?: string;
  action?: string;
  dismissible?: boolean;
  autoHide?: boolean;
  duration?: number; // milliseconds for auto-hide
}

/**
 * Error Store State Interface
 */
interface ErrorState {
  errors: ErrorItem[];
  maxErrors: number;
  
  // Actions
  addError: (error: Omit<ErrorItem, 'id'>) => void;
  removeError: (id: string) => void;
  clearErrors: () => void;
  clearErrorsByType: (type: ErrorItem['type']) => void;
  updateError: (id: string, updates: Partial<ErrorItem>) => void;
  
  // Helper methods
  getErrorsByType: (type: ErrorItem['type']) => ErrorItem[];
  getErrorsBySeverity: (severity: ErrorItem['severity']) => ErrorItem[];
  hasErrors: () => boolean;
  hasErrorsOfType: (type: ErrorItem['type']) => boolean;
}

/**
 * Error Utility Functions
 */
export const createErrorId = (): string => {
  return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const createNetworkError = (message: string, details?: string): Omit<ErrorItem, 'id'> => ({
  type: 'network',
  message,
  details,
  timestamp: new Date(),
  severity: 'high',
  dismissible: true,
  autoHide: false
});

export const createValidationError = (message: string, component?: string): Omit<ErrorItem, 'id'> => ({
  type: 'validation',
  message,
  timestamp: new Date(),
  severity: 'medium',
  component,
  dismissible: true,
  autoHide: true,
  duration: 5000
});

export const createApiError = (message: string, action?: string): Omit<ErrorItem, 'id'> => ({
  type: 'api',
  message,
  timestamp: new Date(),
  severity: 'high',
  action,
  dismissible: true,
  autoHide: false
});

export const createAuthError = (message: string): Omit<ErrorItem, 'id'> => ({
  type: 'auth',
  message,
  timestamp: new Date(),
  severity: 'critical',
  dismissible: true,
  autoHide: false
});

/**
 * Global Error Store
 * Manages application-wide error state with Zustand
 */
export const useErrorStore = create<ErrorState>()(
  devtools(
    (set, get) => ({
      errors: [],
      maxErrors: 10, // Limit number of stored errors to prevent memory issues

      addError: (errorData) => {
        const newError: ErrorItem = {
          id: createErrorId(),
          dismissible: true,
          autoHide: false,
          ...errorData
        };

        set((state) => {
          const newErrors = [...state.errors, newError];
          
          // Keep only the most recent errors if we exceed maxErrors
          if (newErrors.length > state.maxErrors) {
            newErrors.splice(0, newErrors.length - state.maxErrors);
          }
          
          return { errors: newErrors };
        });

        // Auto-hide error if configured
        if (newError.autoHide && newError.duration) {
          setTimeout(() => {
            get().removeError(newError.id);
          }, newError.duration);
        }

        // Log error for debugging
        console.error(`[${newError.severity.toUpperCase()}] ${newError.type}: ${newError.message}`, {
          details: newError.details,
          component: newError.component,
          action: newError.action,
          timestamp: newError.timestamp
        });
      },

      removeError: (id) => {
        set((state) => ({
          errors: state.errors.filter(error => error.id !== id)
        }));
      },

      clearErrors: () => {
        set({ errors: [] });
      },

      clearErrorsByType: (type) => {
        set((state) => ({
          errors: state.errors.filter(error => error.type !== type)
        }));
      },

      updateError: (id, updates) => {
        set((state) => ({
          errors: state.errors.map(error => 
            error.id === id ? { ...error, ...updates } : error
          )
        }));
      },

      getErrorsByType: (type) => {
        return get().errors.filter(error => error.type === type);
      },

      getErrorsBySeverity: (severity) => {
        return get().errors.filter(error => error.severity === severity);
      },

      hasErrors: () => {
        return get().errors.length > 0;
      },

      hasErrorsOfType: (type) => {
        return get().errors.some(error => error.type === type);
      }
    }),
    {
      name: 'error-store',
      // Only store errors in devtools, not in localStorage to avoid persistence
      partialize: () => ({})
    }
  )
);

/**
 * Error Store Hooks for Common Use Cases
 */

// Hook to get errors of a specific type
export const useErrorsOfType = (type: ErrorItem['type']) => {
  return useErrorStore((state) => state.getErrorsByType(type));
};

// Hook to get errors of a specific severity
export const useErrorsOfSeverity = (severity: ErrorItem['severity']) => {
  return useErrorStore((state) => state.getErrorsBySeverity(severity));
};

// Hook to check if there are any errors
export const useHasErrors = () => {
  return useErrorStore((state) => state.hasErrors());
};

// Hook to get the latest error
export const useLatestError = () => {
  return useErrorStore((state) => {
    const errors = state.errors;
    return errors.length > 0 ? errors[errors.length - 1] : null;
  });
};

// Hook for common error operations
export const useErrorOperations = () => {
  const addError = useErrorStore((state) => state.addError);
  const removeError = useErrorStore((state) => state.removeError);
  const clearErrors = useErrorStore((state) => state.clearErrors);

  return {
    addError,
    removeError,
    clearErrors,
    // Helper functions for common error types
    addNetworkError: (message: string, details?: string) => 
      addError(createNetworkError(message, details)),
    addValidationError: (message: string, component?: string) => 
      addError(createValidationError(message, component)),
    addApiError: (message: string, action?: string) => 
      addError(createApiError(message, action)),
    addAuthError: (message: string) => 
      addError(createAuthError(message))
  };
};