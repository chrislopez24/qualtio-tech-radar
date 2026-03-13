import { HomeClient } from '@/components/HomeClient';
import type { AIRadarData } from '@/lib/types';
import aiData from '@/data/data.ai.json';

export default function Home() {
  return <HomeClient initialData={aiData as AIRadarData} />;
}
