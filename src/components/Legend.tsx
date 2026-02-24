'use client';

import { QUADRANTS, RINGS } from '@/lib/radar-config';

export function Legend() {
  return (
    <div className="flex flex-col gap-6 p-4 glassmorphism rounded-lg">
      <div>
        <h3 className="text-sm font-semibold mb-3">Rings</h3>
        <div className="space-y-2">
          {RINGS.map((ring) => (
            <div key={ring.id} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: ring.color }}
              />
              <span className="text-sm">{ring.name}</span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold mb-3">Quadrants</h3>
        <div className="space-y-2">
          {QUADRANTS.map((quadrant) => (
            <div key={quadrant.id} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: quadrant.color }}
              />
              <span className="text-sm">{quadrant.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}