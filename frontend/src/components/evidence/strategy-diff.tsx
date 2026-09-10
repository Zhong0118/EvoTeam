import type { Strategy } from "../../data/schema";
import { Badge } from "./common";
export function configFields(strategy: Strategy): Record<string, string> {
  const fields: Record<string, string> = {};
  for (const a of strategy.definition.agents) {
    for (const [key, value] of Object.entries(a)) {
      if (key !== "node_id")
        fields[`${a.node_id}.${key}`] = JSON.stringify(value);
    }
  }
  fields["topology.edges"] = JSON.stringify(strategy.definition.edges);
  if (strategy.definition.orchestration)
    fields["orchestration"] = JSON.stringify(strategy.definition.orchestration);
  return fields;
}
export function StrategyDiff({
  left,
  right,
}: {
  left: Strategy;
  right: Strategy;
}) {
  const a = configFields(left),
    b = configFields(right);
  const fields = [...new Set([...Object.keys(a), ...Object.keys(b)])];
  return (
    <div className="table-scroll">
      <table className="diff-table">
        <thead>
          <tr>
            <th>字段 / 变化</th>
            <th>v{left.metadata.ref.version}</th>
            <th>v{right.metadata.ref.version}</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((key) => (
            <tr key={key}>
              <td>
                <code>{key}</code>
                <div>
                  <Badge value={a[key] === b[key] ? "neutral" : "candidate"}>
                    {a[key] === b[key]
                      ? "相同"
                      : !(key in a)
                        ? "新增"
                        : !(key in b)
                          ? "删除"
                          : "修改"}
                  </Badge>
                </div>
              </td>
              <td>{a[key] ?? "未包含"}</td>
              <td>{b[key] ?? "未包含"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
