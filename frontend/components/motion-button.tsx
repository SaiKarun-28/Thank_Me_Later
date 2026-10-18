'use client';

import { motion, useReducedMotion } from 'framer-motion';
import type { ComponentPropsWithoutRef, ReactNode } from 'react';

type Props = Omit<ComponentPropsWithoutRef<typeof motion.button>, 'children'> & { children: ReactNode; variant?: 'primary' | 'secondary'; };
export function MotionButton({ children, className = '', variant = 'primary', ...props }: Props) {
  const reduced = useReducedMotion();
  return <motion.button {...props} whileTap={reduced ? undefined : { scale: 0.97 }} transition={{ type: 'spring', duration: 0.35, bounce: 0 }} className={`${variant === 'primary' ? 'button-primary' : 'button-secondary'} ${className}`}>{children}</motion.button>;
}
