import React, { useState, useRef, useEffect } from 'react';
import { DragEvent } from 'react';
import LoadingSpinner, { ButtonLoading } from './LoadingSpinner';
import { useErrorHandler } from '../hooks/useErrorHandler';

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: 'todo' | 'in-progress' | 'review' | 'done';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assignedTo?: string;
  createdAt: string;
  dueDate?: string;
  tags?: string[];
  estimatedTime?: number; // in minutes
  actualTime?: number; // in minutes
  dependencies?: string[]; // task IDs
  attachments?: number;
  comments?: number;
}

interface TaskBoardProps {
  tasks: Task[];
  onTaskMove?: (taskId: string, newStatus: Task['status']) => Promise<void>;
  onTaskCreate?: (status: Task['status']) => Promise<void>;
  onTaskEdit?: (taskId: string) => void;
  onTaskDelete?: (taskId: string) => Promise<void>;
  isLoading?: boolean;
  className?: string;
  allowDragDrop?: boolean;
}

/**
 * Task Board Component
 * Kanban-style board for task management with drag & drop functionality
 */
const TaskBoard: React.FC<TaskBoardProps> = ({
  tasks,
  onTaskMove,
  onTaskCreate,
  onTaskEdit,
  onTaskDelete,
  isLoading = false,
  className = '',
  allowDragDrop = true
}) => {
  const [draggedTask, setDraggedTask] = useState<Task | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<Task['status'] | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const { handleAsyncError, withErrorHandling } = useErrorHandler();

  const columns: Array<{ status: Task['status']; title: string; color: string }> = [
    { status: 'todo', title: 'To Do', color: 'bg-gray-50 border-gray-200' },
    { status: 'in-progress', title: 'In Progress', color: 'bg-blue-50 border-blue-200' },
    { status: 'review', title: 'Review', color: 'bg-yellow-50 border-yellow-200' },
    { status: 'done', title: 'Done', color: 'bg-green-50 border-green-200' }
  ];

  const getTasksByStatus = (status: Task['status']) => {
    return tasks.filter(task => task.status === status);
  };

  const getPriorityColor = (priority: Task['priority']) => {
    switch (priority) {
      case 'critical':
        return 'border-l-red-500 bg-red-50';
      case 'high':
        return 'border-l-orange-500 bg-orange-50';
      case 'medium':
        return 'border-l-blue-500 bg-blue-50';
      case 'low':
        return 'border-l-gray-500 bg-gray-50';
      default:
        return 'border-l-gray-500 bg-gray-50';
    }
  };

  const getPriorityDot = (priority: Task['priority']) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-blue-500';
      case 'low':
        return 'bg-gray-500';
      default:
        return 'bg-gray-500';
    }
  };

  const handleDragStart = (e: DragEvent<HTMLDivElement>, task: Task) => {
    if (!allowDragDrop) return;
    setDraggedTask(task);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    if (!allowDragDrop || !draggedTask) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDragEnter = (status: Task['status']) => {
    if (!allowDragDrop || !draggedTask) return;
    setDragOverColumn(status);
  };

  const handleDragLeave = () => {
    if (!allowDragDrop) return;
    setDragOverColumn(null);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>, newStatus: Task['status']) => {
    if (!allowDragDrop || !draggedTask || !onTaskMove) return;
    
    e.preventDefault();
    setDragOverColumn(null);
    
    if (draggedTask.status !== newStatus) {
      setActionLoading(`move-${draggedTask.id}`);
      try {
        await withErrorHandling(
          () => onTaskMove(draggedTask.id, newStatus),
          {
            operation: 'move_task',
            component: 'TaskBoard'
          }
        )();
      } finally {
        setActionLoading(null);
      }
    }
    
    setDraggedTask(null);
  };

  const handleAction = async (action: string, taskId: string, callback: () => Promise<void>) => {
    setActionLoading(`${action}-${taskId}`);
    try {
      await withErrorHandling(callback, {
        operation: action,
        component: 'TaskBoard'
      })();
    } finally {
      setActionLoading(null);
    }
  };

  const isOverdue = (dueDate?: string) => {
    if (!dueDate) return false;
    return new Date(dueDate) < new Date();
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  if (isLoading) {
    return (
      <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 ${className}`}>
        {columns.map((column, index) => (
          <div key={index} className={`rounded-lg border-2 border-dashed ${column.color} p-4 min-h-96`}>
            <div className="mb-4">
              <div className="h-6 bg-gray-200 rounded w-24 animate-pulse"></div>
            </div>
            <div className="space-y-3">
              {Array.from({ length: 3 }, (_, i) => (
                <div key={i} className="bg-white rounded-lg shadow-sm border p-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-full mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 ${className}`}>
      {columns.map((column) => (
        <div
          key={column.status}
          className={`rounded-lg border-2 border-dashed ${column.color} ${
            dragOverColumn === column.status ? 'border-indigo-400 bg-indigo-50' : ''
          } p-4 min-h-96 transition-colors duration-200`}
          onDragOver={handleDragOver}
          onDragEnter={() => handleDragEnter(column.status)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, column.status)}
        >
          {/* Column Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <h3 className="text-lg font-semibold text-gray-900">{column.title}</h3>
              <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-gray-600 bg-gray-200 rounded-full">
                {getTasksByStatus(column.status).length}
              </span>
            </div>
            
            {onTaskCreate && (
              <button
                onClick={() => onTaskCreate(column.status)}
                className="text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600 transition-colors"
                title={`Add task to ${column.title}`}
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </button>
            )}
          </div>

          {/* Tasks */}
          <div className="space-y-3">
            {getTasksByStatus(column.status).map((task) => (
              <div
                key={task.id}
                draggable={allowDragDrop}
                onDragStart={(e) => handleDragStart(e, task)}
                className={`bg-white rounded-lg shadow-sm border-l-4 p-4 cursor-pointer hover:shadow-md transition-shadow duration-200 ${
                  getPriorityColor(task.priority)
                } ${draggedTask?.id === task.id ? 'opacity-50' : ''} ${
                  allowDragDrop ? 'cursor-move' : 'cursor-pointer'
                }`}
                onClick={() => onTaskEdit?.(task.id)}
              >
                {actionLoading === `move-${task.id}` && (
                  <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-lg">
                    <LoadingSpinner size="small" />
                  </div>
                )}

                {/* Task Header */}
                <div className="flex items-start justify-between mb-2">
                  <h4 className="text-sm font-semibold text-gray-900 line-clamp-2 flex-1">
                    {task.title}
                  </h4>
                  <div className="flex items-center space-x-1 ml-2">
                    <div className={`h-2 w-2 rounded-full ${getPriorityDot(task.priority)}`} />
                    {task.priority === 'critical' && (
                      <svg className="h-3 w-3 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>
                </div>

                {/* Description */}
                {task.description && (
                  <p className="text-xs text-gray-600 line-clamp-2 mb-3">
                    {task.description}
                  </p>
                )}

                {/* Tags */}
                {task.tags && task.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {task.tags.slice(0, 2).map((tag, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700"
                      >
                        {tag}
                      </span>
                    ))}
                    {task.tags.length > 2 && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                        +{task.tags.length - 2}
                      </span>
                    )}
                  </div>
                )}

                {/* Task Meta */}
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <div className="flex items-center space-x-2">
                    {task.assignedTo && (
                      <div className="flex items-center space-x-1">
                        <div className="h-4 w-4 rounded-full bg-indigo-100 flex items-center justify-center">
                          <span className="text-xs font-medium text-indigo-600">
                            {task.assignedTo.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <span>{task.assignedTo}</span>
                      </div>
                    )}
                    
                    {task.estimatedTime && (
                      <div className="flex items-center space-x-1">
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>{task.estimatedTime}m</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {task.attachments && task.attachments > 0 && (
                      <div className="flex items-center space-x-1">
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                        </svg>
                        <span>{task.attachments}</span>
                      </div>
                    )}
                    
                    {task.comments && task.comments > 0 && (
                      <div className="flex items-center space-x-1">
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <span>{task.comments}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Due Date */}
                {task.dueDate && (
                  <div className={`mt-2 text-xs ${
                    isOverdue(task.dueDate) ? 'text-red-600' : 'text-gray-500'
                  }`}>
                    Due: {formatDate(task.dueDate)}
                    {isOverdue(task.dueDate) && (
                      <span className="ml-1 font-medium">(Overdue)</span>
                    )}
                  </div>
                )}

                {/* Task Actions */}
                <div className="mt-3 flex justify-end space-x-2">
                  {onTaskDelete && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAction('delete', task.id, () => onTaskDelete(task.id));
                      }}
                      disabled={actionLoading === `delete-${task.id}`}
                      className="text-gray-400 hover:text-red-500 focus:outline-none focus:text-red-500 transition-colors"
                      title="Delete task"
                    >
                      {actionLoading === `delete-${task.id}` ? (
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
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default TaskBoard;