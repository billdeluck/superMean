import React, { useState, useEffect } from 'react';
import LoadingSpinner, { InlineLoading } from './LoadingSpinner';
import { useErrorHandler } from '../hooks/useErrorHandler';

export interface MemoryItem {
  id: string;
  type: 'agent' | 'global' | 'vector' | 'conversation' | 'task';
  key: string;
  value: any;
  metadata?: {
    createdAt: string;
    updatedAt?: string;
    accessCount?: number;
    ttl?: number; // time to live in seconds
    tags?: string[];
    source?: string;
    importance?: 'low' | 'medium' | 'high' | 'critical';
  };
  size?: number; // in bytes
}

interface MemoryViewerProps {
  memories?: MemoryItem[];
  onRefresh?: () => Promise<void>;
  onDelete?: (memoryId: string) => Promise<void>;
  onExport?: () => Promise<void>;
  onClear?: (type?: MemoryItem['type']) => Promise<void>;
  isLoading?: boolean;
  className?: string;
  showActions?: boolean;
  filterType?: MemoryItem['type'] | 'all';
}

/**
 * Memory Viewer Component
 * Displays and manages application memory with filtering and actions
 */
const MemoryViewer: React.FC<MemoryViewerProps> = ({
  memories = [],
  onRefresh,
  onDelete,
  onExport,
  onClear,
  isLoading = false,
  className = '',
  showActions = true,
  filterType = 'all'
}) => {
  const [selectedType, setSelectedType] = useState<MemoryItem['type'] | 'all'>(filterType);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const { handleAsyncError, withErrorHandling } = useErrorHandler();

  const memoryTypes: Array<{ type: MemoryItem['type'] | 'all'; label: string; icon: React.ReactNode }> = [
    {
      type: 'all',
      label: 'All Memory',
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14-7H5a2 2 0 00-2 2v14c0 1.1.9 2 2 2h14a2 2 0 002-2V6a2 2 0 00-2-2z" />
        </svg>
      )
    },
    {
      type: 'agent',
      label: 'Agent Memory',
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      )
    },
    {
      type: 'global',
      label: 'Global Memory',
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9v-9m0-9v9" />
        </svg>
      )
    },
    {
      type: 'vector',
      label: 'Vector Memory',
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
        </svg>
      )
    },
    {
      type: 'conversation',
      label: 'Conversation',
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      )
    },
    {
      type: 'task',
      label: 'Task Memory',
      icon: (
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
      )
    }
  ];

  const getTypeColor = (type: MemoryItem['type']) => {
    switch (type) {
      case 'agent':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'global':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'vector':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'conversation':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'task':
        return 'bg-indigo-100 text-indigo-800 border-indigo-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getImportanceColor = (importance?: MemoryItem['metadata']['importance']) => {
    switch (importance) {
      case 'critical':
        return 'text-red-600';
      case 'high':
        return 'text-orange-600';
      case 'medium':
        return 'text-yellow-600';
      case 'low':
        return 'text-gray-600';
      default:
        return 'text-gray-500';
    }
  };

  const filteredMemories = memories.filter(memory => {
    const typeMatch = selectedType === 'all' || memory.type === selectedType;
    const searchMatch = searchTerm === '' || 
      memory.key.toLowerCase().includes(searchTerm.toLowerCase()) ||
      JSON.stringify(memory.value).toLowerCase().includes(searchTerm.toLowerCase());
    return typeMatch && searchMatch;
  });

  const getMemoryStats = () => {
    const stats = {
      total: memories.length,
      byType: {} as Record<MemoryItem['type'], number>,
      totalSize: memories.reduce((sum, mem) => sum + (mem.size || 0), 0)
    };

    memoryTypes.slice(1).forEach(type => {
      stats.byType[type.type as MemoryItem['type']] = memories.filter(m => m.type === type.type).length;
    });

    return stats;
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatValue = (value: any) => {
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  const toggleExpanded = (memoryId: string) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(memoryId)) {
      newExpanded.delete(memoryId);
    } else {
      newExpanded.add(memoryId);
    }
    setExpandedItems(newExpanded);
  };

  const handleAction = async (action: string, callback: () => Promise<void>) => {
    setActionLoading(action);
    try {
      await withErrorHandling(callback, {
        operation: action,
        component: 'MemoryViewer'
      })();
    } finally {
      setActionLoading(null);
    }
  };

  const stats = getMemoryStats();

  if (isLoading) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
        <div className="p-6">
          <div className="flex items-center justify-center h-64">
            <InlineLoading text="Loading memory data..." />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Memory Visualization</h2>
          {showActions && (
            <div className="flex space-x-3">
              {onRefresh && (
                <button
                  onClick={() => handleAction('refresh', onRefresh)}
                  disabled={actionLoading === 'refresh'}
                  className="flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
                >
                  {actionLoading === 'refresh' ? (
                    <LoadingSpinner size="small" color="gray" />
                  ) : (
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  )}
                  Refresh
                </button>
              )}
              {onExport && (
                <button
                  onClick={() => handleAction('export', onExport)}
                  disabled={actionLoading === 'export'}
                  className="flex items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
                >
                  {actionLoading === 'export' ? (
                    <LoadingSpinner size="small" color="gray" />
                  ) : (
                    <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  )}
                  Export
                </button>
              )}
            </div>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-2xl font-semibold text-gray-900">{stats.total}</div>
            <div className="text-sm text-gray-600">Total Items</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-2xl font-semibold text-gray-900">{stats.byType.agent || 0}</div>
            <div className="text-sm text-gray-600">Agent Memory</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-2xl font-semibold text-gray-900">{stats.byType.vector || 0}</div>
            <div className="text-sm text-gray-600">Vector Memory</div>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-2xl font-semibold text-gray-900">{formatBytes(stats.totalSize)}</div>
            <div className="text-sm text-gray-600">Total Size</div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
          {/* Type Filter */}
          <div className="flex-1">
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as MemoryItem['type'] | 'all')}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              {memoryTypes.map((type) => (
                <option key={type.type} value={type.type}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                placeholder="Search memory..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
          </div>

          {/* Clear Actions */}
          {onClear && showActions && (
            <div className="flex space-x-2">
              <button
                onClick={() => handleAction('clear', () => onClear())}
                disabled={actionLoading === 'clear'}
                className="flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 transition-colors"
              >
                {actionLoading === 'clear' ? (
                  <LoadingSpinner size="small" color="gray" />
                ) : (
                  <svg className="h-4 w-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                )}
                Clear All
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Memory Items */}
      <div className="p-6">
        {filteredMemories.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14-7H5a2 2 0 00-2 2v14c0 1.1.9 2 2 2h14a2 2 0 002-2V6a2 2 0 00-2-2z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No memory items</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm || selectedType !== 'all' 
                ? 'No items match your current filters.' 
                : 'No memory items have been stored yet.'
              }
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredMemories.map((memory) => (
              <div
                key={memory.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow"
              >
                {/* Memory Item Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      <h4 className="text-sm font-semibold text-gray-900 truncate">
                        {memory.key}
                      </h4>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getTypeColor(memory.type)}`}>
                        {memory.type}
                      </span>
                      {memory.metadata?.importance && (
                        <span className={`text-xs font-medium ${getImportanceColor(memory.metadata.importance)}`}>
                          {memory.metadata.importance}
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      {memory.metadata?.createdAt && (
                        <span>Created: {new Date(memory.metadata.createdAt).toLocaleDateString()}</span>
                      )}
                      {memory.metadata?.accessCount && (
                        <span>Accessed: {memory.metadata.accessCount} times</span>
                      )}
                      {memory.size && (
                        <span>Size: {formatBytes(memory.size)}</span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => toggleExpanded(memory.id)}
                      className="text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600 transition-colors"
                    >
                      <svg 
                        className={`h-4 w-4 transform transition-transform ${expandedItems.has(memory.id) ? 'rotate-180' : ''}`} 
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    
                    {onDelete && (
                      <button
                        onClick={() => handleAction(`delete-${memory.id}`, () => onDelete(memory.id))}
                        disabled={actionLoading === `delete-${memory.id}`}
                        className="text-gray-400 hover:text-red-500 focus:outline-none focus:text-red-500 transition-colors"
                      >
                        {actionLoading === `delete-${memory.id}` ? (
                          <LoadingSpinner size="small" color="gray" />
                        ) : (
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {/* Tags */}
                {memory.metadata?.tags && memory.metadata.tags.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-3">
                    {memory.metadata.tags.map((tag, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Expanded Content */}
                {expandedItems.has(memory.id) && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs font-medium text-gray-700 mb-2">Value:</div>
                    <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-x-auto">
                      {formatValue(memory.value)}
                    </pre>
                    
                    {memory.metadata?.source && (
                      <div className="mt-3 text-xs text-gray-500">
                        Source: {memory.metadata.source}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MemoryViewer;