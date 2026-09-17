import type { EvidenceSection } from "../evidence";
import { evidenceTitle } from "../evidence";
import { colorForBrand } from "../brandColors";

interface Props {
  sections: EvidenceSection[];
  activeToolName: string | null;
  onAsk: (question: string) => void;
}

export default function EvidencePane({ sections, activeToolName, onAsk }: Props) {
  const hasStatus = sections.some((s) => s.kind === "status");
  const hasData = sections.some((s) => s.kind !== "status");
  const overallOk = hasData || !hasStatus;

  return (
    <aside className="evidence-pane">
      <header className="evidence-header">
        <div>
          <div className="evidence-eyebrow mono">Evidence{activeToolName ? ` · ${activeToolName}` : ""}</div>
          <div className="evidence-title">{evidenceTitle(sections)}</div>
        </div>
        {sections.length > 0 && (
          <span
            className="status-badge mono"
            style={{
              color: overallOk ? "var(--status-ok-color)" : "var(--status-warn-color)",
              borderColor: overallOk ? "var(--status-ok-border)" : "var(--status-warn-border)",
            }}
          >
            {overallOk ? "ok" : "attention"}
          </span>
        )}
      </header>

      <div className="evidence-scroll">
        {sections.length === 0 && (
          <p className="evidence-empty">
            Ask a question in the chat — brand stats, complaints or praises on a topic, a
            rating trend, or a review search — and whatever the assistant's tool calls return
            will be drawn here.
          </p>
        )}

        {sections.map((section, i) => (
          <EvidenceSectionView key={i} section={section} onAsk={onAsk} />
        ))}
      </div>
    </aside>
  );
}

function EvidenceSectionView({ section, onAsk }: { section: EvidenceSection; onAsk: (q: string) => void }) {
  switch (section.kind) {
    case "stats-single": {
      const { brand_name, stats } = section.entry;
      const tiles = [
        { label: "avg_rating", value: stats.avg_rating.toFixed(2), sub: "of 5.00", accent: true },
        { label: "median_rating", value: stats.median_rating.toFixed(1), sub: "of 5.0" },
        {
          label: "rating_std",
          value: `±${stats.rating_std.toFixed(2)}`,
          sub: stats.rating_std < 0.85 ? "tight spread" : "wide spread",
        },
        { label: "review_count", value: stats.review_count.toLocaleString(), sub: "reviews in corpus" },
        { label: "avg_car_year", value: stats.avg_car_year.toFixed(1), sub: "model year mean" },
        { label: "brand", value: brand_name, sub: "" },
      ];
      return (
        <div className="tile-grid">
          {tiles.map((t) => (
            <div className="tile" key={t.label}>
              <span className="tile-label mono">{t.label}</span>
              <span className="tile-value mono" style={t.accent ? { color: "var(--cyan)" } : undefined}>
                {t.value}
              </span>
              <span className="tile-sub mono">{t.sub}</span>
            </div>
          ))}
        </div>
      );
    }

    case "stats-multi": {
      const maxN = Math.max(...section.entries.map((e) => e.stats.review_count));
      const totalN = section.entries.reduce((a, e) => a + e.stats.review_count, 0);
      const avgYear =
        section.entries.reduce((a, e) => a + e.stats.avg_car_year, 0) / section.entries.length;
      return (
        <div className="card">
          <div className="card-head">
            <span className="card-head-title">Average rating by brand</span>
            <span className="card-head-meta mono">0 – 5 · bar opacity = sample size</span>
          </div>
          {section.entries.map((e) => (
            <div className="bar-row" key={e.brand_name}>
              <span className="bar-name">{e.brand_name}</span>
              <span className="bar-track">
                <span
                  className="bar-fill"
                  style={{
                    width: `${(e.stats.avg_rating / 5) * 100}%`,
                    background: colorForBrand(e.brand_name),
                    opacity: 0.45 + 0.55 * (e.stats.review_count / maxN),
                  }}
                />
              </span>
              <span className="bar-value">
                <span className="bar-value-main mono">{e.stats.avg_rating.toFixed(2)}</span>
                <span className="bar-value-sub mono">{e.stats.review_count.toLocaleString()} rev</span>
              </span>
            </div>
          ))}
          <span className="trend-footnote mono">
            n = {totalN.toLocaleString()} reviews · avg model year {avgYear.toFixed(1)}
          </span>
        </div>
      );
    }

    case "topics": {
      return (
        <>
          {section.groups.map((g, gi) => {
            const color = g.sentiment === "negative" ? "var(--neg)" : "var(--pos)";
            const border = g.sentiment === "negative" ? "var(--neg-border)" : "var(--pos-border)";
            const max = Math.max(...g.items.map((x) => x.count));
            return (
              <div className="card" key={`${g.brand_name}-${g.sentiment}-${gi}`} style={{ borderColor: border }}>
                <div className="card-head">
                  <span className="card-head-title">
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 2,
                        background: color,
                        display: "inline-block",
                      }}
                    />
                    {g.brand_name} · {g.sentiment === "negative" ? "complaints" : "praises"}
                  </span>
                  <span className="card-head-meta mono">
                    {g.topic_filter ? "topic_filter set" : `${g.items.length} topics`}
                  </span>
                </div>
                {g.items.map((item) => (
                  <div className="topic-row" key={item.topic_label} title={`${item.topic_label} — ${item.top_keywords}`}>
                    <div className="topic-row-head">
                      <span className="topic-label">{item.topic_label}</span>
                      <span className="topic-count mono">{item.count.toLocaleString()}</span>
                    </div>
                    <span className="topic-track">
                      <span
                        className="topic-fill"
                        style={{ width: `${(item.count / max) * 100}%`, background: color }}
                      />
                    </span>
                    <span className="topic-kw mono">{item.top_keywords}</span>
                  </div>
                ))}
              </div>
            );
          })}
        </>
      );
    }

    case "trend": {
      const { brands, points } = section;
      const years = points.map((p) => p.car_year);
      const ratings = points.map((p) => p.avg_rating);
      const yMin = Math.min(...years);
      const yMax = Math.max(...years);
      const rMin = Math.max(0, Math.floor(Math.min(...ratings) * 5 - 1) / 5);
      const rMax = Math.min(5, Math.ceil(Math.max(...ratings) * 5 + 1) / 5);
      const x0 = 30,
        x1 = 432,
        yTop = 14,
        yBot = 158;
      const px = (year: number) => (yMax === yMin ? (x0 + x1) / 2 : x0 + ((year - yMin) / (yMax - yMin)) * (x1 - x0));
      const py = (v: number) => (rMax === rMin ? (yTop + yBot) / 2 : yBot - ((v - rMin) / (rMax - rMin)) * (yBot - yTop));

      const gridStep = (rMax - rMin) / 4 || 0.5;
      const gridVals = Array.from({ length: 5 }, (_, i) => rMin + gridStep * i);
      const tickYears = Array.from(new Set([yMin, Math.round((yMin + yMax) / 2), yMax]));

      const byBrand = new Map<string, typeof points>();
      for (const p of points) {
        if (!byBrand.has(p.brand_name)) byBrand.set(p.brand_name, []);
        byBrand.get(p.brand_name)!.push(p);
      }

      const totalN = points.reduce((a, p) => a + p.review_count, 0);

      return (
        <div className="card">
          <div className="card-head">
            <span className="card-head-title">Avg rating by model year</span>
            <div className="trend-legend">
              {brands.map((b) => (
                <span className="trend-legend-item" key={b}>
                  <span className="trend-legend-swatch" style={{ background: colorForBrand(b) }} />
                  {b}
                </span>
              ))}
            </div>
          </div>
          <svg viewBox="0 0 440 190" style={{ width: "100%", height: "auto", display: "block", overflow: "visible" }}>
            {gridVals.map((v, i) => (
              <g key={i}>
                <line x1={30} y1={py(v)} x2={436} y2={py(v)} stroke="oklch(0.27 0.008 265)" strokeWidth={1} />
                <text x={24} y={py(v) + 3} textAnchor="end" fill="oklch(0.55 0.01 265)" fontFamily="JetBrains Mono, monospace" fontSize={9}>
                  {v.toFixed(1)}
                </text>
              </g>
            ))}
            {tickYears.map((y) => (
              <text key={y} x={px(y)} y={182} textAnchor="middle" fill="oklch(0.55 0.01 265)" fontFamily="JetBrains Mono, monospace" fontSize={9}>
                {y}
              </text>
            ))}
            {[...byBrand.entries()].map(([brand, pts]) => {
              const sorted = [...pts].sort((a, b) => a.car_year - b.car_year);
              const linePoints = sorted.map((p) => `${px(p.car_year).toFixed(1)},${py(p.avg_rating).toFixed(1)}`).join(" ");
              return (
                <polyline
                  key={brand}
                  points={linePoints}
                  fill="none"
                  stroke={colorForBrand(brand)}
                  strokeWidth={1.8}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              );
            })}
          </svg>
          <span className="trend-footnote mono">
            {yMax - yMin + 1} model years · {totalN.toLocaleString()} reviews
          </span>
        </div>
      );
    }

    case "reviews": {
      return (
        <div className="review-list">
          <span className="review-meta mono">
            {section.matches.length} matches · query "{section.query}"
          </span>
          {section.matches.map((m) => (
            <article className="review-card" key={m.review_id}>
              <div className="review-card-head">
                <span className="review-badge-row">
                  <span className="review-badge mono">
                    {m.brand_name} {m.car_year}
                  </span>
                  <span
                    className="review-stars"
                    style={{ color: m.rating >= 4 ? "var(--pos)" : m.rating <= 2 ? "var(--neg)" : "oklch(0.78 0.11 85)" }}
                  >
                    {"★★★★★".slice(0, Math.round(m.rating))}
                    {"☆☆☆☆☆".slice(0, 5 - Math.round(m.rating))}
                  </span>
                </span>
                <span className="review-date mono">{m.date}</span>
              </div>
              <p className="review-text">{m.review_text}</p>
              <span className="review-footer-meta mono">
                #{m.review_id} · {m.word_count} words
              </span>
            </article>
          ))}
        </div>
      );
    }

    case "status": {
      return (
        <>
          {section.items.map((item, i) => {
            const isOk = item.status === "ok";
            const color = isOk ? "var(--status-ok-color)" : "var(--status-warn-color)";
            const border = isOk ? "var(--status-ok-border)" : "var(--status-warn-border)";
            return (
              <div className="status-card" key={i} style={{ borderColor: border }}>
                <span className="status-tag mono" style={{ color }}>
                  {item.status}
                </span>
                <span className="status-title">{item.title}</span>
                <span className="status-body">{item.body}</span>
                {item.options.length > 0 && (
                  <div>
                    <span className="status-options-label mono">available options</span>
                    <div className="status-options-row">
                      {item.options.map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          className="status-option-btn"
                          onClick={() => onAsk(item.onOptionClick ? item.onOptionClick(opt) : opt)}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </>
      );
    }

    default:
      return null;
  }
}
