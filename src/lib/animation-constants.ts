export const SPRING_SNAPPY = {
  type: "spring" as const,
  stiffness: 400,
  damping: 17,
} as const;

export const SPRING_SMOOTH = {
  type: "spring" as const,
  stiffness: 100,
  damping: 20,
} as const;

export const SPRING_BOUNCY = {
  type: "spring" as const,
  stiffness: 200,
  damping: 15,
} as const;
