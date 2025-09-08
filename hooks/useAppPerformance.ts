import React from 'react';

// Optional: Performance monitoring hook
export const useAppPerformance = () => {
  React.useEffect(() => {
    const startTime = Date.now();
    
    return () => {
      const loadTime = Date.now() - startTime;
      // Log a warning if the app takes more than 3 seconds to load.
      if (loadTime > 3000) {
        console.warn(`App took ${loadTime}ms to load`);
      }
    };
  }, []);
};
