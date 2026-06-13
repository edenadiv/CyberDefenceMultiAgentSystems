/* Live packet sprites streaming the network links, drawn inside the MessageFlow SVG.
   Positions come from the precomputed sprites + the clock `t` — pure, scrub-safe. */
import { useMemo } from "react";

import { activeSprites, buildSprites } from "../lib/packets";
import { useReplay } from "../lib/replayContext";

const TRAIL = 15; // px trail length behind each dot

export function PacketLayer() {
  const { data, t } = useReplay();
  const sprites = useMemo(() => buildSprites(data.replay.packets ?? []), [data.replay.packets]);
  const active = activeSprites(sprites, t);
  if (active.length === 0) return null;

  return (
    <g className="packet-layer">
      {active.map(({ s, pos }) => {
        const dx = s.x2 - s.x1;
        const dy = s.y2 - s.y1;
        const len = Math.hypot(dx, dy) || 1;
        const tx = pos.x - (dx / len) * TRAIL;
        const ty = pos.y - (dy / len) * TRAIL;
        return (
          <g key={s.id} opacity={pos.opacity}>
            <line
              x1={tx}
              y1={ty}
              x2={pos.x}
              y2={pos.y}
              stroke={s.color}
              strokeWidth={2}
              strokeLinecap="round"
              opacity={0.45}
            />
            <circle
              cx={pos.x}
              cy={pos.y}
              r={3}
              fill={s.color}
              style={{ filter: `drop-shadow(0 0 4px ${s.color})` }}
            />
          </g>
        );
      })}
    </g>
  );
}
