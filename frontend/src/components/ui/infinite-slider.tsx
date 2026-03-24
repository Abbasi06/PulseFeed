import { useMotionValue, animate, motion } from 'framer-motion';
import { useEffect } from 'react';
import useMeasure from 'react-use-measure';

interface InfiniteSliderProps {
  children: React.ReactNode;
  gap?: number;
  duration?: number;
  direction?: 'left' | 'right';
}

export function InfiniteSlider({
  children,
  gap = 24,
  duration = 20,
  direction = 'left',
}: InfiniteSliderProps) {
  const [ref, { width }] = useMeasure();
  const x = useMotionValue(0);

  useEffect(() => {
    let controls: any;
    if (width > 0) {
      const distance = width + gap;
      // Start moving based on direction
      controls = animate(x, direction === 'left' ? [0, -distance] : [-distance, 0], {
        duration,
        ease: 'linear',
        repeat: Infinity,
      });
    }
    return () => {
      if (controls && controls.stop) controls.stop();
    };
  }, [width, gap, duration, direction, x]);

  return (
    <div 
      className="flex overflow-hidden w-full relative" 
      style={{ WebkitMaskImage: 'linear-gradient(to right, transparent, black 10%, black 90%, transparent)' }}
    >
      <motion.div 
         style={{ x, gap: `${gap}px` }} 
         className="flex w-max items-center"
      >
        <div ref={ref} className="flex items-center" style={{ gap: `${gap}px` }}>
          {children}
        </div>
        <div className="flex items-center" style={{ gap: `${gap}px` }}>
          {children}
        </div>
        <div className="flex items-center" style={{ gap: `${gap}px` }}>
          {children}
        </div>
      </motion.div>
    </div>
  );
}
