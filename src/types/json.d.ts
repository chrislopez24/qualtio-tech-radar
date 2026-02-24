declare module '*.json' {
  const value: import('@/lib/types').RadarData | import('@/lib/types').AIRadarData;
  export default value;
}