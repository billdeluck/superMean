import React, { useState } from 'react';
import Link from 'next/link';
import LoadingSpinner, { ButtonLoading } from './LoadingSpinner';
import { useErrorHandler } from '../hooks/useErrorHandler';

export interface Agent {
  id: string;
  name: string;
  type: string;
  status: 'idle' | 'busy' | 'error' | 'offline';
  description?: string;
  lastActivity?: string;
  capabilities?: string[];
  performance?: {
    successRate: number;
    averageResponseTime: number;
    tasksCompleted: number;
  };
  avatar?: string;
}

interface AgentCardProps {
  agent: Agent;
  onStart?: (agentId: string) => Promise<void>;
  onStop?: (agentId: string) => Promise<void>;
  onDelete?: (agentId: string) => Promise<void>;
  isLoading?: boolean;
  className?: string;
  showActions?: boolean;
  compact?: boolean;
}

/**
 * Agent Card Component
 * Displays agent information with actions and real-time status
 */
const AgentCard: React.FC<AgentCardProps> = ({
  agent,
  onStart,
  onStop,
  onDelete,
  isLoading = false,
  className = '',
  showActions = true,
  compact = false
}) => {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const { handleAsyncError, withErrorHandling } = useErrorHandler();

  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'idle':
        return 'bg-green-100 text-green-800';
      case 'busy':
        return 'bg-blue-100 text-blue-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'offline':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: Agent['status']) => {
    switch (status) {
      case 'idle':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'busy':
        return <LoadingSpinner size="small" color="primary" />;
      case 'error':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'offline':
        return (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L18.364 5.636" />
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
        component: 'AgentCard'
      })();
    } finally {
      setActionLoading(null);
    }
  };

  const canStart = agent.status === 'idle' || agent.status === 'offline';
  const canStop = agent.status === 'busy';

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse ${className}`}>
        <div className="flex items-center space-x-4">
          <div className="h-12 w-12 bg-gray-200 rounded-full"></div>
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
        {!compact && (
          <>
            <div className="mt-4 space-y-2">
              <div className="h-3 bg-gray-200 rounded"></div>
              <div className="h-3 bg-gray-200 rounded w-5/6"></div>
            </div>
            <div className="mt-4 flex space-x-2">
              <div className="h-8 bg-gray-200 rounded w-20"></div>
              <div className="h-8 bg-gray-200 rounded w-20"></div>
            </div>
          </>
        )}
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200 ${className}`}>
      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            {/* Avatar */}
            <div className="flex-shrink-0">
              {agent.avatar ? (
                <img
                  className="h-12 w-12 rounded-full"
                  src={agent.avatar}
                  alt={`${agent.name} avatar`}
                />
              ) : (
                <div className="h-12 w-12 rounded-full bg-indigo-100 flex items-center justify-center">
                  <svg className="h-6 w-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
              )}
            </div>

            {/* Agent Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-semibold text-gray-900 truncate">
                  {agent.name}
                </h3>
                <span className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(agent.status)}`}>
                  {getStatusIcon(agent.status)}
                  <span className="capitalize">{agent.status}</span>
                </span>
              </div>
              <p className="text-sm text-gray-500 capitalize">
                {agent.type} Agent
              </p>
              {agent.lastActivity && (
                <p className="text-xs text-gray-400 mt-1">
                  Last active: {agent.lastActivity}
                </p>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          {showActions && (
            <div className="flex items-center space-x-2">
              <Link href={`/agents/${agent.id}`}>
                <button className="text-gray-400 hover:text-gray-500 p-1 rounded-full hover:bg-gray-100 transition-colors">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
              </Link>
            </div>
          )}
        </div>

        {/* Description */}
        {!compact && agent.description && (
          <p className="mt-4 text-sm text-gray-600 line-clamp-2">
            {agent.description}
          </p>
        )}

        {/* Capabilities */}
        {!compact && agent.capabilities && agent.capabilities.length > 0 && (
          <div className="mt-4">
            <div className="flex flex-wrap gap-2">
              {agent.capabilities.slice(0, 3).map((capability, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                >
                  {capability}
                </span>
              ))}
              {agent.capabilities.length > 3 && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                  +{agent.capabilities.length - 3} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Performance Metrics */}
        {!compact && agent.performance && (
          <div className="mt-4 grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-lg font-semibold text-gray-900">
                {agent.performance.successRate}%
              </div>
              <div className="text-xs text-gray-500">Success Rate</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-gray-900">
                {agent.performance.averageResponseTime}ms
              </div>
              <div className="text-xs text-gray-500">Avg Response</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-gray-900">
                {agent.performance.tasksCompleted}
              </div>
              <div className="text-xs text-gray-500">Tasks Done</div>
            </div>
          </div>
        )}

        {/* Actions */}
        {showActions && (
          <div className="mt-6 flex space-x-3">
            {canStart && onStart && (
              <button
                onClick={() => handleAction('start', () => onStart(agent.id))}
                disabled={actionLoading === 'start'}
                className="flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading === 'start' ? (
                  <ButtonLoading />
                ) : (
                  <>
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h1m4 0h1" />
                    </svg>
                    Start
                  </>
                )}
              </button>
            )}

            {canStop && onStop && (
              <button
                onClick={() => handleAction('stop', () => onStop(agent.id))}
                disabled={actionLoading === 'stop'}
                className="flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading === 'stop' ? (
                  <LoadingSpinner size="small" color="gray" />
                ) : (
                  <>
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10h6v4H9V10z" />
                    </svg>
                    Stop
                  </>
                )}
              </button>
            )}

            <Link href={`/agents/${agent.id}`}>
              <button className="flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors">
                <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                View
              </button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentCard;