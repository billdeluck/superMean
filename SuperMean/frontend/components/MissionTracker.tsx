import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import LoadingSpinner, { ButtonLoading, InlineLoading } from './LoadingSpinner';
import { useErrorHandler } from '../hooks/useErrorHandler';

export interface Mission {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused';
  priority: 'low' | 'medium' | 'high' | 'critical';
  progress?: number; // 0-100
  assignedAgents?: string[];
  createdAt: string;
  updatedAt?: string;
  completedAt?: string;
  estimatedDuration?: number; // in minutes
  actualDuration?: number; // in minutes
  tags?: string[];
  results?: {
    success: boolean;
    output?: string;
    errors?: string[];
  };
}

interface MissionTrackerProps {
  mission: Mission;
  onPause?: (missionId: string) => Promise<void>;
  onResume?: (missionId: string) => Promise<void>;
  onCancel?: (missionId: string) => Promise<void>;
  onRetry?: (missionId: string) => Promise<void>;
  isLoading?: boolean;
  className?: string;
  showActions?: boolean;
  compact?: boolean;
  showProgress?: boolean;
}

/**
 * Mission Tracker Component
 * Displays mission information with real-time status tracking and progress
 */
const MissionTracker: React.FC<MissionTrackerProps> = ({
  mission,
  onPause,
  onResume,
  onCancel,
  onRetry,
  isLoading = false,
  className = '',
  showActions = true,
  compact = false,
  showProgress = true
}) => {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [realTimeProgress, setRealTimeProgress] = useState(mission.progress || 0);
  const { handleAsyncError, withErrorHandling } = useErrorHandler();

  // Simulate real-time progress updates for running missions
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (mission.status === 'running' && mission.progress !== undefined) {
      interval = setInterval(() => {
        setRealTimeProgress(prev => {
          const increment = Math.random() * 2; // Random increment
          const newProgress = Math.min(prev + increment, 100);
          return newProgress;
        });
      }, 2000);
    } else {
      setRealTimeProgress(mission.progress || 0);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [mission.status, mission.progress]);

  const getStatusColor = (status: Mission['status']) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'running':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'paused':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getPriorityColor = (priority: Mission['priority']) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'high':
        return 'bg-orange-50 text-orange-700 border-orange-200';
      case 'medium':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'low':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  const getStatusIcon = (status: Mission['status']) => {
    switch (status) {
      case 'pending':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'running':
        return <LoadingSpinner size="small" color="primary" />;
      case 'completed':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'paused':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const handleAction = async (action: string, callback: () => Promise<void>) => {
    setActionLoading(action);
    try {
      await withErrorHandling(callback, {
        operation: action,
        component: 'MissionTracker'
      })();
    } finally {
      setActionLoading(null);
    }
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const getElapsedTime = () => {
    if (!mission.createdAt) return null;
    const now = new Date();
    const created = new Date(mission.createdAt);
    const elapsed = Math.floor((now.getTime() - created.getTime()) / (1000 * 60)); // minutes
    return formatDuration(elapsed);
  };

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse ${className}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="h-6 bg-gray-200 rounded w-3/4"></div>
          <div className="h-6 bg-gray-200 rounded w-20"></div>
        </div>
        {showProgress && (
          <div className="mb-4">
            <div className="h-2 bg-gray-200 rounded w-full"></div>
          </div>
        )}
        {!compact && (
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200 ${className}`}>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-3 mb-2">
              <h3 className="text-lg font-semibold text-gray-900 truncate">
                {mission.title}
              </h3>
              <span className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(mission.status)}`}>
                {getStatusIcon(mission.status)}
                <span className="capitalize">{mission.status}</span>
              </span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getPriorityColor(mission.priority)}`}>
                <span className="capitalize">{mission.priority}</span>
              </span>
            </div>
            
            {/* Time Information */}
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <span>Created: {new Date(mission.createdAt).toLocaleDateString()}</span>
              {mission.status === 'running' && (
                <span>Elapsed: {getElapsedTime()}</span>
              )}
              {mission.estimatedDuration && (
                <span>Est: {formatDuration(mission.estimatedDuration)}</span>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center space-x-2">
            <Link href={`/missions/${mission.id}`}>
              <button className="text-gray-400 hover:text-gray-500 p-1 rounded-full hover:bg-gray-100 transition-colors">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </button>
            </Link>
          </div>
        </div>

        {/* Progress Bar */}
        {showProgress && (mission.status === 'running' || mission.status === 'completed') && (
          <div className="mb-4">
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-gray-700">Progress</span>
              <span className="text-sm text-gray-500">
                {Math.round(realTimeProgress)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${
                  mission.status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
                }`}
                style={{ width: `${realTimeProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Description */}
        {!compact && mission.description && (
          <p className="text-sm text-gray-600 mb-4 line-clamp-2">
            {mission.description}
          </p>
        )}

        {/* Assigned Agents */}
        {!compact && mission.assignedAgents && mission.assignedAgents.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-gray-700">Agents:</span>
              <div className="flex flex-wrap gap-1">
                {mission.assignedAgents.slice(0, 3).map((agentId, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800"
                  >
                    {agentId}
                  </span>
                ))}
                {mission.assignedAgents.length > 3 && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    +{mission.assignedAgents.length - 3}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tags */}
        {!compact && mission.tags && mission.tags.length > 0 && (
          <div className="mb-4">
            <div className="flex flex-wrap gap-2">
              {mission.tags.map((tag, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {mission.status === 'completed' && mission.results && (
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <svg className="h-4 w-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium text-gray-700">Results</span>
            </div>
            {mission.results.output && (
              <p className="text-sm text-gray-600">{mission.results.output}</p>
            )}
          </div>
        )}

        {/* Error Results */}
        {mission.status === 'failed' && mission.results?.errors && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <svg className="h-4 w-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium text-red-700">Error</span>
            </div>
            {mission.results.errors.map((error, index) => (
              <p key={index} className="text-sm text-red-600">{error}</p>
            ))}
          </div>
        )}

        {/* Actions */}
        {showActions && (
          <div className="flex space-x-3">
            {mission.status === 'running' && onPause && (
              <button
                onClick={() => handleAction('pause', () => onPause(mission.id))}
                disabled={actionLoading === 'pause'}
                className="flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading === 'pause' ? (
                  <LoadingSpinner size="small" color="gray" />
                ) : (
                  <>
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Pause
                  </>
                )}
              </button>
            )}

            {mission.status === 'paused' && onResume && (
              <button
                onClick={() => handleAction('resume', () => onResume(mission.id))}
                disabled={actionLoading === 'resume'}
                className="flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading === 'resume' ? (
                  <ButtonLoading />
                ) : (
                  <>
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1" />
                    </svg>
                    Resume
                  </>
                )}
              </button>
            )}

            {mission.status === 'failed' && onRetry && (
              <button
                onClick={() => handleAction('retry', () => onRetry(mission.id))}
                disabled={actionLoading === 'retry'}
                className="flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading === 'retry' ? (
                  <ButtonLoading />
                ) : (
                  <>
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Retry
                  </>
                )}
              </button>
            )}

            {(mission.status === 'running' || mission.status === 'pending') && onCancel && (
              <button
                onClick={() => handleAction('cancel', () => onCancel(mission.id))}
                disabled={actionLoading === 'cancel'}
                className="flex items-center justify-center px-4 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading === 'cancel' ? (
                  <LoadingSpinner size="small" color="gray" />
                ) : (
                  <>
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Cancel
                  </>
                )}
              </button>
            )}

            <Link href={`/missions/${mission.id}`}>
              <button className="flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors">
                <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                Details
              </button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default MissionTracker;