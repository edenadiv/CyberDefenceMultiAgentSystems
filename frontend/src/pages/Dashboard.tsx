import { AlertFeed } from "../components/AlertFeed";
import { MessageFlow } from "../components/MessageFlow";
import { MetricsPanel } from "../components/MetricsPanel";
import { ResourcePanel } from "../components/ResourcePanel";
import { TopologyMap } from "../components/TopologyMap";

export function Dashboard() {
  return (
    <div className="grid-dash">
      <TopologyMap />
      <div className="center">
        <MessageFlow />
        <MetricsPanel />
      </div>
      <div className="right">
        <AlertFeed />
        <ResourcePanel />
      </div>
    </div>
  );
}
