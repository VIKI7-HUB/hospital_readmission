/**
 * Motion System Configuration
 * ClinicalAI Readmission Insights Design System
 * 
 * Reusable motion tokens, spring physics, animation variants,
 * and prefers-reduced-motion accessibility fallbacks.
 */

export const motionTokens = {
  durations: {
    fast: 0.15,
    base: 0.25,
    slow: 0.4,
  },
  easings: {
    entrance: [0.22, 1, 0.36, 1],
    easeInOut: [0.4, 0, 0.2, 1],
    easeOut: [0, 0, 0.2, 1],
  },
  springs: {
    snappy: { type: "spring", stiffness: 380, damping: 30 },
    gentle: { type: "spring", stiffness: 200, damping: 25 },
    drawer: { type: "spring", stiffness: 380, damping: 32 },
  },
};

/**
 * Returns variants configured for full motion or reduced motion.
 */
export function createVariants(reduced = false) {
  if (reduced) {
    return {
      page: {
        initial: { opacity: 0 },
        animate: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.1 } },
      },
      stagger: {
        animate: { transition: { staggerChildren: 0 } },
      },
      fadeInUp: {
        initial: { opacity: 0 },
        animate: { opacity: 1, transition: { duration: 0.15 } },
      },
      drawer: {
        initial: { opacity: 0 },
        animate: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.1 } },
      },
      overlay: {
        initial: { opacity: 0 },
        animate: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.1 } },
      },
      palette: {
        initial: { opacity: 0 },
        animate: { opacity: 1, transition: { duration: 0.15 } },
        exit: { opacity: 0, transition: { duration: 0.1 } },
      },
      cardHover: {},
    };
  }

  return {
    page: {
      initial: { opacity: 0, y: 8 },
      animate: {
        opacity: 1,
        y: 0,
        transition: {
          duration: motionTokens.durations.base,
          ease: motionTokens.easings.entrance,
        },
      },
      exit: {
        opacity: 0,
        y: -6,
        transition: {
          duration: motionTokens.durations.fast,
          ease: motionTokens.easings.easeInOut,
        },
      },
    },
    stagger: (staggerDelay = 0.05) => ({
      animate: {
        transition: {
          staggerChildren: staggerDelay,
        },
      },
    }),
    fadeInUp: {
      initial: { opacity: 0, y: 12 },
      animate: {
        opacity: 1,
        y: 0,
        transition: {
          duration: motionTokens.durations.base,
          ease: motionTokens.easings.entrance,
        },
      },
    },
    drawer: {
      initial: { x: "100%", opacity: 0.6 },
      animate: {
        x: 0,
        opacity: 1,
        transition: motionTokens.springs.drawer,
      },
      exit: {
        x: "100%",
        opacity: 0,
        transition: {
          duration: motionTokens.durations.fast,
          ease: motionTokens.easings.easeInOut,
        },
      },
    },
    overlay: {
      initial: { opacity: 0 },
      animate: { opacity: 1, transition: { duration: 0.2 } },
      exit: { opacity: 0, transition: { duration: 0.15 } },
    },
    palette: {
      initial: { opacity: 0, scale: 0.96, y: -12 },
      animate: {
        opacity: 1,
        scale: 1,
        y: 0,
        transition: motionTokens.springs.snappy,
      },
      exit: {
        opacity: 0,
        scale: 0.96,
        y: -8,
        transition: { duration: 0.12 },
      },
    },
    cardHover: {
      whileHover: { y: -4, transition: { duration: 0.18, ease: "easeOut" } },
      whileTap: { scale: 0.98 },
    },
  };
}
