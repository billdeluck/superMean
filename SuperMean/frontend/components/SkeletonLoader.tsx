import React from 'react';

interface SkeletonProps {
  className?: string;
  animate?: boolean;
}

/**
 * Basic Skeleton Component
 * Creates a skeleton loading placeholder with optional animation
 */
const Skeleton: React.FC<SkeletonProps> = ({ 
  className = '', 
  animate = true 
}) => {
  return (
    <div
      className={`bg-gray-200 rounded ${animate ? 'animate-pulse' : ''} ${className}`}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};

/**
 * Text Skeleton
 * Creates skeleton placeholders for text content
 */
interface TextSkeletonProps {
  lines?: number;
  className?: string;
  animate?: boolean;
}

export const TextSkeleton: React.FC<TextSkeletonProps> = ({ 
  lines = 1, 
  className = '',
  animate = true 
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton
          key={index}
          className={`h-4 ${
            index === lines - 1 && lines > 1 
              ? 'w-3/4' // Last line is shorter
              : 'w-full'
          }`}
          animate={animate}
        />
      ))}
    </div>
  );
};

/**
 * Card Skeleton
 * Creates skeleton placeholder for card components
 */
interface CardSkeletonProps {
  showAvatar?: boolean;
  showImage?: boolean;
  textLines?: number;
  className?: string;
  animate?: boolean;
}

export const CardSkeleton: React.FC<CardSkeletonProps> = ({
  showAvatar = false,
  showImage = false,
  textLines = 3,
  className = '',
  animate = true
}) => {
  return (
    <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
      {/* Header with avatar */}
      {showAvatar && (
        <div className="flex items-center space-x-3 mb-4">
          <Skeleton className="h-10 w-10 rounded-full" animate={animate} />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/4" animate={animate} />
            <Skeleton className="h-3 w-1/6" animate={animate} />
          </div>
        </div>
      )}

      {/* Image placeholder */}
      {showImage && (
        <Skeleton className="h-48 w-full mb-4" animate={animate} />
      )}

      {/* Text content */}
      <div className="space-y-3">
        <Skeleton className="h-6 w-3/4" animate={animate} />
        <TextSkeleton lines={textLines} animate={animate} />
      </div>

      {/* Footer actions */}
      <div className="flex space-x-3 mt-6">
        <Skeleton className="h-8 w-20" animate={animate} />
        <Skeleton className="h-8 w-20" animate={animate} />
      </div>
    </div>
  );
};

/**
 * Table Skeleton
 * Creates skeleton placeholder for table components
 */
interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  showHeader?: boolean;
  className?: string;
  animate?: boolean;
}

export const TableSkeleton: React.FC<TableSkeletonProps> = ({
  rows = 5,
  columns = 4,
  showHeader = true,
  className = '',
  animate = true
}) => {
  return (
    <div className={`bg-white shadow rounded-lg overflow-hidden ${className}`}>
      {/* Table header */}
      {showHeader && (
        <div className="px-6 py-3 bg-gray-50 border-b">
          <div className="flex space-x-4">
            {Array.from({ length: columns }, (_, index) => (
              <Skeleton 
                key={index}
                className="h-4 flex-1" 
                animate={animate}
              />
            ))}
          </div>
        </div>
      )}

      {/* Table rows */}
      <div className="divide-y divide-gray-200">
        {Array.from({ length: rows }, (_, rowIndex) => (
          <div key={rowIndex} className="px-6 py-4">
            <div className="flex space-x-4">
              {Array.from({ length: columns }, (_, colIndex) => (
                <Skeleton 
                  key={colIndex}
                  className={`h-4 ${
                    colIndex === 0 ? 'w-1/4' : // First column wider
                    colIndex === columns - 1 ? 'w-1/6' : // Last column narrower
                    'flex-1'
                  }`}
                  animate={animate}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * List Skeleton
 * Creates skeleton placeholder for list components
 */
interface ListSkeletonProps {
  items?: number;
  showAvatar?: boolean;
  className?: string;
  animate?: boolean;
}

export const ListSkeleton: React.FC<ListSkeletonProps> = ({
  items = 5,
  showAvatar = true,
  className = '',
  animate = true
}) => {
  return (
    <div className={`space-y-4 ${className}`}>
      {Array.from({ length: items }, (_, index) => (
        <div key={index} className="flex items-center space-x-3 p-4 bg-white rounded-lg shadow">
          {showAvatar && (
            <Skeleton className="h-10 w-10 rounded-full" animate={animate} />
          )}
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" animate={animate} />
            <Skeleton className="h-3 w-1/2" animate={animate} />
          </div>
          <Skeleton className="h-8 w-20" animate={animate} />
        </div>
      ))}
    </div>
  );
};

/**
 * Dashboard Skeleton
 * Creates skeleton placeholder for dashboard layouts
 */
interface DashboardSkeletonProps {
  className?: string;
  animate?: boolean;
}

export const DashboardSkeleton: React.FC<DashboardSkeletonProps> = ({
  className = '',
  animate = true
}) => {
  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <Skeleton className="h-8 w-1/3" animate={animate} />
        <Skeleton className="h-10 w-32" animate={animate} />
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <Skeleton className="h-4 w-20" animate={animate} />
                <Skeleton className="h-8 w-16" animate={animate} />
              </div>
              <Skeleton className="h-12 w-12 rounded" animate={animate} />
            </div>
          </div>
        ))}
      </div>

      {/* Main content area */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CardSkeleton showImage textLines={4} animate={animate} />
        <CardSkeleton showAvatar textLines={6} animate={animate} />
      </div>

      {/* Table */}
      <TableSkeleton rows={8} columns={5} animate={animate} />
    </div>
  );
};

export default Skeleton;