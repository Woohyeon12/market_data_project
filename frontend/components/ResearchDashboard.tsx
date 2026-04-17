"use client";

import { Fragment, useEffect, useState } from "react";
import {
  fallbackMarkets,
  fallbackModelBacktests,
  fallbackReport,
  fetchBtcResearch,
  fetchMarketsOverview,
  fetchModelBacktests,
  type IndexChart,
  type MarketInstrument,
  type MarketsOverview,
  type ModelBacktestOverview,
  type ModelEquityPoint,
  type NewsItem,
  type ResearchReport,
  type CorrelationCell,
} from "../lib/api";

const RANGE_OPTIONS = [
  { label: "6M", value: "6m", days: 183 },
  { label: "1Y", value: "1y", days: 365 },
  { label: "3Y", value: "3y", days: 365 * 3 },
  { label: "5Y", value: "5y", days: 365 * 5 },
  { label: "10Y", value: "10y", days: 365 * 10 },
  { label: "All", value: "all", days: null },
];

const CHART_SIZES = {
  compact: { label: "Compact", height: 96, maxPoints: 90 },
  medium: { label: "Medium", height: 128, maxPoints: 140 },
  large: { label: "Large", height: 176, maxPoints: 220 },
};

type ChartSize = keyof typeof CHART_SIZES;

function formatUsd(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatCompactUsd(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatMarketPrice(item: MarketInstrument) {
  if (item.category === "Government Bonds" || item.currency === "Yield") {
    return `${item.price.toFixed(2)}%`;
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: item.currency,
    maximumFractionDigits: item.currency === "JPY" || item.currency === "KRW" ? 0 : 2,
  }).format(item.price);
}

function formatAxisValue(value: number, currency: string) {
  if (currency === "Yield") {
    return `${value.toFixed(2)}%`;
  }

  if (value >= 1000) {
    return new Intl.NumberFormat("en-US", {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  }

  return value.toFixed(value >= 100 ? 0 : 2);
}

function formatShortDate(value?: string) {
  if (!value) {
    return "";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, "0")}`;
}

function groupInstruments(instruments: MarketInstrument[]) {
  return instruments.reduce<Record<string, MarketInstrument[]>>((groups, item) => {
    groups[item.category] = [...(groups[item.category] ?? []), item];
    return groups;
  }, {});
}

function averageChange(items: MarketInstrument[]) {
  if (items.length === 0) {
    return 0;
  }

  return items.reduce((total, item) => total + item.change_pct, 0) / items.length;
}

function barWidth(changePct: number, maxAbsChange: number) {
  if (maxAbsChange === 0) {
    return "0%";
  }

  return `${Math.min(Math.abs(changePct) / maxAbsChange, 1) * 100}%`;
}

function chartChangePct(chart: IndexChart) {
  const first = chart.points[0]?.close ?? 0;
  const last = chart.points[chart.points.length - 1]?.close ?? first;

  return first ? ((last - first) / first) * 100 : 0;
}

function visibleChartPoints(chart: IndexChart, rangeValue: string) {
  const selected = RANGE_OPTIONS.find((option) => option.value === rangeValue);

  if (!selected?.days) {
    return chart.points;
  }

  return chart.points.slice(-selected.days);
}

function sampledChartPoints(points: IndexChart["points"], maxPoints: number) {
  if (points.length <= maxPoints) {
    return points;
  }

  const step = Math.ceil(points.length / maxPoints);
  return points.filter((_, index) => index % step === 0);
}

function calculateSma(values: number[], period: number) {
  return values.map((_, index) => {
    if (index < period - 1) {
      return null;
    }

    const slice = values.slice(index - period + 1, index + 1);
    return slice.reduce((total, value) => total + value, 0) / period;
  });
}

function calculateBollinger(values: number[], period = 20, deviation = 2) {
  const sma = calculateSma(values, period);

  return values.map((_, index) => {
    const middle = sma[index];

    if (middle === null || index < period - 1) {
      return { upper: null, middle: null, lower: null };
    }

    const slice = values.slice(index - period + 1, index + 1);
    const variance = slice.reduce((total, value) => total + (value - middle) ** 2, 0) / period;
    const band = Math.sqrt(variance) * deviation;

    return {
      upper: middle + band,
      middle,
      lower: middle - band,
    };
  });
}

function calculateRsi(values: number[], period = 14) {
  return values.map((_, index) => {
    if (index < period) {
      return null;
    }

    const slice = values.slice(index - period + 1, index + 1);
    let gains = 0;
    let losses = 0;

    slice.forEach((value, sliceIndex) => {
      if (sliceIndex === 0) {
        return;
      }

      const change = value - slice[sliceIndex - 1];
      if (change >= 0) {
        gains += change;
      } else {
        losses += Math.abs(change);
      }
    });

    const averageGain = gains / period;
    const averageLoss = losses / period;

    if (averageLoss === 0) {
      return 100;
    }

    const relativeStrength = averageGain / averageLoss;
    return 100 - 100 / (1 + relativeStrength);
  });
}

function scaledPath(
  values: Array<number | null>,
  yForValue: (value: number) => number,
  slot: number,
  xOffset = 0,
) {
  return values
    .map((value, index) => {
      if (value === null) {
        return "";
      }

      const command = values.slice(0, index).some((previous) => previous !== null) ? "L" : "M";
      return `${command} ${xOffset + slot * index + slot / 2} ${yForValue(value)}`;
    })
    .filter(Boolean)
    .join(" ");
}

function chartGeometry(points: IndexChart["points"], size: ChartSize, currency: string) {
  const width = 328;
  const leftAxis = 42;
  const rightPad = 8;
  const bottomAxis = 22;
  const plotWidth = width - leftAxis - rightPad;
  const height = CHART_SIZES[size].height;
  const plotHeight = height - bottomAxis;
  const sampledPoints = sampledChartPoints(points, CHART_SIZES[size].maxPoints);
  const closes = sampledPoints.map((point) => point.close);
  const bollinger = calculateBollinger(closes);
  const sma20 = calculateSma(closes, 20);
  const rsi14 = calculateRsi(closes);
  const highs = points.map((point) => point.high);
  const lows = points.map((point) => point.low);
  const bandValues = bollinger
    .flatMap((band) => [band.upper, band.lower])
    .filter((value): value is number => value !== null);
  const min = Math.min(...lows, ...bandValues);
  const max = Math.max(...highs, ...bandValues);
  const range = max - min || 1;
  const slot = sampledPoints.length ? plotWidth / sampledPoints.length : plotWidth;
  const bodyWidth = Math.max(1.5, Math.min(8, slot * 0.58));
  const priceHeight = Math.round(plotHeight * 0.72);
  const rsiTop = priceHeight + 12;
  const rsiHeight = Math.max(32, plotHeight - rsiTop);
  const priceY = (value: number) => priceHeight - ((value - min) / range) * priceHeight;
  const rsiY = (value: number) => rsiTop + rsiHeight - (value / 100) * rsiHeight;

  const candles = sampledPoints.map((point, index) => {
    const centerX = leftAxis + slot * index + slot / 2;
    const openY = priceY(point.open);
    const closeY = priceY(point.close);
    const highY = priceY(point.high);
    const lowY = priceY(point.low);
    const bodyTop = Math.min(openY, closeY);
    const bodyHeight = Math.max(2, Math.abs(closeY - openY));

    return {
      key: `${point.date}-${index}`,
      rising: point.close >= point.open,
      centerX,
      highY,
      lowY,
      bodyX: centerX - bodyWidth / 2,
      bodyTop,
      bodyWidth,
      bodyHeight,
    };
  });

  return {
    candles,
    upperPath: scaledPath(bollinger.map((band) => band.upper), priceY, slot, leftAxis),
    middlePath: scaledPath(sma20, priceY, slot, leftAxis),
    lowerPath: scaledPath(bollinger.map((band) => band.lower), priceY, slot, leftAxis),
    rsiPath: scaledPath(rsi14, rsiY, slot, leftAxis),
    leftAxis,
    plotWidth,
    width,
    height,
    priceBaseline: priceHeight,
    rsiTop,
    rsiHeight,
    rsi30: rsiY(30),
    rsi70: rsiY(70),
    sampledCount: sampledPoints.length,
    yTicks: [
      { label: formatAxisValue(max, currency), y: priceY(max) },
      { label: formatAxisValue((max + min) / 2, currency), y: priceY((max + min) / 2) },
      { label: formatAxisValue(min, currency), y: priceY(min) },
    ],
    xTicks: [
      { label: formatShortDate(sampledPoints[0]?.date), x: leftAxis },
      {
        label: formatShortDate(sampledPoints[Math.floor(sampledPoints.length / 2)]?.date),
        x: leftAxis + plotWidth / 2,
      },
      {
        label: formatShortDate(sampledPoints[sampledPoints.length - 1]?.date),
        x: leftAxis + plotWidth,
      },
    ],
  };
}

function newsKey(item: NewsItem) {
  return `${item.source}-${item.title}`;
}

function formatNewsTime(value?: string | null) {
  if (!value) {
    return "Recently collected";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function correlationColor(value: number) {
  const opacity = Math.min(Math.abs(value), 1);

  if (value > 0) {
    return `rgba(14, 138, 115, ${0.12 + opacity * 0.78})`;
  }

  if (value < 0) {
    return `rgba(178, 58, 72, ${0.12 + opacity * 0.78})`;
  }

  return "rgba(104, 113, 123, 0.16)";
}

function correlationTextColor(value: number) {
  return Math.abs(value) > 0.55 ? "#ffffff" : "var(--foreground)";
}

function correlationTone(value: number) {
  if (Math.abs(value) < 0.15) {
    return "Low signal";
  }

  if (Math.abs(value) < 0.35) {
    return "Watch";
  }

  if (Math.abs(value) < 0.55) {
    return "Meaningful";
  }

  return "High priority";
}

function correlationAction(cell: CorrelationCell) {
  if (Math.abs(cell.value) < 0.15) {
    return "Keep as context until the signal strengthens.";
  }

  if (cell.value > 0) {
    return "Track as a same-direction macro or risk appetite input.";
  }

  return "Track as a possible hedge, stress, or regime-warning input.";
}

function formatPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function modelCurveGeometry(points: ModelEquityPoint[]) {
  const width = 260;
  const height = 72;
  const pad = 6;

  if (points.length === 0) {
    return { width, height, path: "", baseline: height - pad };
  }

  const values = points.map((point) => point.equity);
  const min = Math.min(...values, 1);
  const max = Math.max(...values, 1);
  const range = max - min || 1;
  const slot = points.length > 1 ? (width - pad * 2) / (points.length - 1) : 0;
  const yForValue = (value: number) => height - pad - ((value - min) / range) * (height - pad * 2);
  const path = points
    .map((point, index) => {
      const command = index === 0 ? "M" : "L";
      return `${command} ${pad + slot * index} ${yForValue(point.equity)}`;
    })
    .join(" ");

  return {
    width,
    height,
    path,
    baseline: yForValue(1),
  };
}

export function ResearchDashboard() {
  const [report, setReport] = useState<ResearchReport>(fallbackReport);
  const [markets, setMarkets] = useState<MarketsOverview>(fallbackMarkets);
  const [modelBacktests, setModelBacktests] = useState<ModelBacktestOverview>(fallbackModelBacktests);
  const [newsFilter, setNewsFilter] = useState("all");
  const [selectedNewsKey, setSelectedNewsKey] = useState<string | null>(null);
  const [chartRange, setChartRange] = useState("10y");
  const [chartSize, setChartSize] = useState<ChartSize>("medium");
  const [showBollinger, setShowBollinger] = useState(true);
  const [showRsi, setShowRsi] = useState(true);
  const [selectedFeature, setSelectedFeature] = useState("BTC return");

  useEffect(() => {
    let active = true;

    fetchBtcResearch().then((nextReport) => {
      if (active) {
        setReport(nextReport);
      }
    });
    fetchMarketsOverview().then((nextMarkets) => {
      if (active) {
        setMarkets(nextMarkets);
      }
    });
    fetchModelBacktests().then((nextModelBacktests) => {
      if (active) {
        setModelBacktests(nextModelBacktests);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  const groupedMarkets = groupInstruments(markets.instruments);
  const marketCategories = Object.entries(groupedMarkets);
  const maxMarketChange = Math.max(
    1,
    ...markets.instruments.map((item) => Math.abs(item.change_pct)),
  );
  const maxCategoryChange = Math.max(
    1,
    ...marketCategories.map(([, items]) => Math.abs(averageChange(items))),
  );
  const filteredNews = report.news.filter((item) => {
    return newsFilter === "all" || item.sentiment === newsFilter;
  });
  const chartSet = [...markets.index_charts, ...markets.bond_charts];
  const activeFeature = markets.correlations.assets.includes(selectedFeature)
    ? selectedFeature
    : markets.correlations.assets[0] ?? "BTC return";
  const focusedRelationships = markets.correlations.matrix
    .filter((cell) => cell.y === activeFeature && cell.x !== activeFeature)
    .sort((first, second) => Math.abs(second.value) - Math.abs(first.value));
  const topPositiveRelationships = focusedRelationships
    .filter((cell) => cell.value > 0)
    .sort((first, second) => second.value - first.value)
    .slice(0, 3);
  const topNegativeRelationships = focusedRelationships
    .filter((cell) => cell.value < 0)
    .sort((first, second) => first.value - second.value)
    .slice(0, 3);

  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">BTC Research AI</p>
            <h1>Bitcoin market research</h1>
            <p className="lede">
              Scenario-based research for market context, news signals, and risk notes.
            </p>
          </div>
          <p className="timestamp">
            Updated {new Date(report.generated_at).toLocaleString()}
          </p>
        </header>

        <section className="grid" aria-label="Bitcoin research dashboard">
          <div className="panel">
            <h2>Market Snapshot</h2>
            <p className="source-label">Source: {report.market.data_source}</p>
            <div className="metric-row">
              <div className="metric">
                <div className="metric-label">Price</div>
                <p className="metric-value">{formatUsd(report.market.price_usd)}</p>
              </div>
              <div className="metric">
                <div className="metric-label">24h Change</div>
                <p className="metric-value">{report.market.change_24h_pct}%</p>
              </div>
              <div className="metric">
                <div className="metric-label">24h Volume</div>
                <p className="metric-value">
                  {formatCompactUsd(report.market.volume_24h_usd)}
                </p>
              </div>
            </div>
          </div>

          <div className="panel">
            <h2>Research Summary</h2>
            <ul className="summary-list">
              {report.summary.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="panel">
            <h2>Scenarios</h2>
            <div className="scenario-grid">
              {report.scenarios.map((scenario) => (
                <article className="scenario" key={scenario.label}>
                  <h3>{scenario.label}</h3>
                  <p className="probability">{scenario.probability_pct}%</p>
                  <div className="probability-bar" aria-label={`${scenario.label} probability`}>
                    <div
                      className="probability-fill"
                      style={{ width: `${scenario.probability_pct}%` }}
                    />
                  </div>
                  <p>{scenario.rationale}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="panel">
            <h2>Global Market Watch</h2>
            <p className="source-label">
              Updated {new Date(markets.generated_at).toLocaleString()}
            </p>
            <div className="chart-controls" aria-label="Chart controls">
              <div>
                <span>Range</span>
                <div className="segmented-control">
                  {RANGE_OPTIONS.map((option) => (
                    <button
                      className={chartRange === option.value ? "control-active" : ""}
                      key={option.value}
                      onClick={() => setChartRange(option.value)}
                      type="button"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <span>Size</span>
                <div className="segmented-control">
                  {Object.entries(CHART_SIZES).map(([value, option]) => (
                    <button
                      className={chartSize === value ? "control-active" : ""}
                      key={value}
                      onClick={() => setChartSize(value as ChartSize)}
                      type="button"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
              <label>
                <input
                  checked={showBollinger}
                  onChange={(event) => setShowBollinger(event.target.checked)}
                  type="checkbox"
                />
                Bollinger
              </label>
              <label>
                <input
                  checked={showRsi}
                  onChange={(event) => setShowRsi(event.target.checked)}
                  type="checkbox"
                />
                RSI
              </label>
            </div>
            <div className="index-chart-grid" aria-label="Major market and bond plots">
              {chartSet.map((chart) => {
                const visiblePoints = visibleChartPoints(chart, chartRange);
                const visibleChart = { ...chart, points: visiblePoints };
                const geometry = chartGeometry(visiblePoints, chartSize, chart.currency);
                const changePct = chartChangePct(visibleChart);
                const firstPoint = visiblePoints[0];
                const lastPoint = visiblePoints[visiblePoints.length - 1];

                return (
                  <article className="index-chart" key={chart.symbol}>
                    <div className="index-chart-header">
                      <div>
                        <h3>{chart.name}</h3>
                        <span>{chart.symbol} - {chart.data_source}</span>
                      </div>
                      <strong className={changePct >= 0 ? "change-positive" : "change-negative"}>
                        {changePct.toFixed(2)}%
                      </strong>
                    </div>
                    <svg
                      className="candle-plot"
                      style={{ height: `${geometry.height + 14}px` }}
                      viewBox={`0 0 ${geometry.width} ${geometry.height}`}
                      role="img"
                      aria-label={`${chart.name} candlestick plot with technical indicators`}
                    >
                      {geometry.yTicks.map((tick) => (
                        <g className="axis-tick" key={`${chart.symbol}-${tick.label}`}>
                          <line x1={geometry.leftAxis} y1={tick.y} x2={geometry.width} y2={tick.y} />
                          <text x={0} y={tick.y + 3}>{tick.label}</text>
                        </g>
                      ))}
                      <line x1={geometry.leftAxis} y1={geometry.priceBaseline} x2={geometry.width} y2={geometry.priceBaseline} />
                      {showRsi ? (
                        <>
                          <line className="rsi-guide" x1={geometry.leftAxis} y1={geometry.rsi70} x2={geometry.width} y2={geometry.rsi70} />
                          <line className="rsi-guide" x1={geometry.leftAxis} y1={geometry.rsi30} x2={geometry.width} y2={geometry.rsi30} />
                          <path className="rsi-line" d={geometry.rsiPath} />
                        </>
                      ) : null}
                      {showBollinger ? (
                        <>
                          <path className="bollinger-line" d={geometry.upperPath} />
                          <path className="moving-average-line" d={geometry.middlePath} />
                          <path className="bollinger-line" d={geometry.lowerPath} />
                        </>
                      ) : null}
                      {geometry.candles.map((candle) => (
                        <g
                          className={candle.rising ? "candle-positive" : "candle-negative"}
                          key={candle.key}
                        >
                          <line
                            x1={candle.centerX}
                            y1={candle.highY}
                            x2={candle.centerX}
                            y2={candle.lowY}
                          />
                          <rect
                            x={candle.bodyX}
                            y={candle.bodyTop}
                            width={candle.bodyWidth}
                            height={candle.bodyHeight}
                          />
                        </g>
                      ))}
                      <line className="date-axis" x1={geometry.leftAxis} y1={geometry.height - 16} x2={geometry.width} y2={geometry.height - 16} />
                      {geometry.xTicks.map((tick) => (
                        <text className="date-tick" key={`${chart.symbol}-${tick.label}-${tick.x}`} x={tick.x} y={geometry.height - 3}>
                          {tick.label}
                        </text>
                      ))}
                    </svg>
                    <div className="chart-range">
                      <span>{firstPoint?.date ?? "Start"}</span>
                      <span>
                        {visiblePoints.length.toLocaleString()} visible / {chart.points.length.toLocaleString()} DB rows
                      </span>
                      <span>{lastPoint?.date ?? "Latest"}</span>
                    </div>
                  </article>
                );
              })}
            </div>
            <div className="market-summary-bars" aria-label="Average market moves by category">
              {marketCategories.map(([category, items]) => {
                const changePct = averageChange(items);

                return (
                  <div className="summary-bar-row" key={category}>
                    <span>{category}</span>
                    <div className="summary-bar-track">
                      <div
                        className={changePct >= 0 ? "summary-bar-positive" : "summary-bar-negative"}
                        style={{ width: barWidth(changePct, maxCategoryChange) }}
                      />
                    </div>
                    <strong className={changePct >= 0 ? "change-positive" : "change-negative"}>
                      {changePct.toFixed(2)}%
                    </strong>
                  </div>
                );
              })}
            </div>
            <div className="market-watch">
              {marketCategories.map(([category, items]) => (
                <section className="market-group" key={category}>
                  <h3>{category}</h3>
                  <div className="market-table">
                    {items.map((item) => (
                      <div className="market-row" key={item.symbol}>
                        <div>
                          <strong>{item.name}</strong>
                          <span>{item.symbol} - {item.market}</span>
                          <div className="move-bar" aria-label={`${item.name} daily move`}>
                            <div
                              className={item.change_pct >= 0 ? "move-fill-positive" : "move-fill-negative"}
                              style={{ width: barWidth(item.change_pct, maxMarketChange) }}
                            />
                          </div>
                        </div>
                        <div className="market-values">
                          <strong>{formatMarketPrice(item)}</strong>
                          <span className={item.change_pct >= 0 ? "change-positive" : "change-negative"}>
                            {item.change_pct.toFixed(2)}%
                          </span>
                          <span>{item.data_source}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
            <p className="disclaimer">{markets.disclaimer}</p>
          </div>

          <div className="panel">
            <h2>Feature Correlation Heatmap</h2>
            <p className="source-label">
              {markets.correlations.lookback_days} trading days - {markets.correlations.data_source}
            </p>
            <div className="feature-workbench" aria-label="Feature relationship workbench">
              <div className="feature-picker">
                <span>Focus variable</span>
                <div>
                  {markets.correlations.assets.map((asset) => (
                    <button
                      className={asset === activeFeature ? "feature-active" : ""}
                      key={asset}
                      onClick={() => setSelectedFeature(asset)}
                      type="button"
                    >
                      {asset}
                    </button>
                  ))}
                </div>
              </div>
              <div className="relationship-grid">
                <section>
                  <h3>Positive drivers</h3>
                  {(topPositiveRelationships.length ? topPositiveRelationships : focusedRelationships.slice(0, 3)).map((cell) => (
                    <article className="relationship-card" key={`positive-${cell.x}-${cell.y}`}>
                      <div>
                        <strong>{cell.x}</strong>
                        <span>{correlationTone(cell.value)}</span>
                      </div>
                      <b style={{ background: correlationColor(cell.value), color: correlationTextColor(cell.value) }}>
                        {cell.value.toFixed(2)}
                      </b>
                      <p>{correlationAction(cell)}</p>
                    </article>
                  ))}
                </section>
                <section>
                  <h3>Negative drivers</h3>
                  {(topNegativeRelationships.length ? topNegativeRelationships : focusedRelationships.slice(-3)).map((cell) => (
                    <article className="relationship-card" key={`negative-${cell.x}-${cell.y}`}>
                      <div>
                        <strong>{cell.x}</strong>
                        <span>{correlationTone(cell.value)}</span>
                      </div>
                      <b style={{ background: correlationColor(cell.value), color: correlationTextColor(cell.value) }}>
                        {cell.value.toFixed(2)}
                      </b>
                      <p>{correlationAction(cell)}</p>
                    </article>
                  ))}
                </section>
              </div>
            </div>
            <div className="correlation-scroll">
              <div
                className="correlation-grid"
                aria-label="Feature correlation heatmap"
                style={{
                  gridTemplateColumns: `minmax(96px, 1.2fr) repeat(${markets.correlations.assets.length}, minmax(58px, 1fr))`,
                }}
              >
                <div className="correlation-corner">Feature</div>
                {markets.correlations.assets.map((asset) => (
                  <div className="correlation-axis correlation-axis-top" key={`x-${asset}`}>
                    {asset}
                  </div>
                ))}
                {markets.correlations.assets.map((yAsset) => (
                  <Fragment key={`row-${yAsset}`}>
                    <div className="correlation-axis" key={`y-${yAsset}`}>{yAsset}</div>
                    {markets.correlations.assets.map((xAsset) => {
                      const value = markets.correlations.matrix.find((cell) => {
                        return cell.x === xAsset && cell.y === yAsset;
                      })?.value ?? 0;

                      return (
                        <div
                          className={`correlation-cell ${
                            xAsset === activeFeature || yAsset === activeFeature
                              ? "correlation-cell-focused"
                              : ""
                          }`}
                          key={`${xAsset}-${yAsset}`}
                          style={{
                            background: correlationColor(value),
                            color: correlationTextColor(value),
                          }}
                          title={`${xAsset} x ${yAsset}: ${value.toFixed(2)}`}
                        >
                          {value.toFixed(2)}
                        </div>
                      );
                    })}
                  </Fragment>
                ))}
              </div>
            </div>
            <div className="correlation-legend" aria-label="Correlation color legend">
              <span>Negative</span>
              <div />
              <span>Positive</span>
            </div>
            <div className="correlation-commentary" aria-label="AI research commentary">
              {markets.correlations.commentary.map((comment) => (
                <p key={comment}>{comment}</p>
              ))}
            </div>
            <div className="lag-correlation-table" aria-label="Lead lag correlation table">
              <div className="lag-correlation-header">
                <span>Leading feature</span>
                <span>Lag</span>
                <span>Corr.</span>
              </div>
              {markets.correlations.lag_correlations.slice(0, 12).map((item) => (
                <div className="lag-correlation-row" key={`${item.feature}-${item.lag_days}`}>
                  <span>{item.feature}</span>
                  <span>{item.lag_days}D</span>
                  <strong
                    style={{
                      background: correlationColor(item.value),
                      color: correlationTextColor(item.value),
                    }}
                  >
                    {item.value.toFixed(2)}
                  </strong>
                </div>
              ))}
            </div>
            <ul className="correlation-insights">
              {markets.correlations.insights.map((insight) => (
                <li key={insight}>{insight}</li>
              ))}
            </ul>
          </div>

          <div className="panel">
            <h2>Model Backtest Lab</h2>
            <p className="source-label">
              Folder: {modelBacktests.model_folder} - {modelBacktests.evaluation_window}
            </p>
            {modelBacktests.results.length === 0 ? (
              <div className="empty-state">
                <strong>No enabled model files yet.</strong>
                <p>
                  Put weighted boosting, bagging, or ensemble JSON files in the model registry to backtest them against recent BTC returns.
                </p>
              </div>
            ) : (
              <div className="model-grid" aria-label="Model backtest results">
                {modelBacktests.results.map((model) => {
                  const curve = modelCurveGeometry(model.equity_curve);
                  const healthy = model.status === "ok";

                  return (
                    <article className="model-card" key={`${model.file_name}-${model.name}`}>
                      <div className="model-card-header">
                        <div>
                          <h3>{model.name}</h3>
                          <span>{model.model_type} - {model.file_name}</span>
                        </div>
                        <strong className={healthy ? "status-ok" : "status-muted"}>
                          {model.status}
                        </strong>
                      </div>
                      <div className="model-metrics">
                        <div>
                          <span>Sharpe</span>
                          <strong>{model.sharpe_ratio.toFixed(2)}</strong>
                        </div>
                        <div>
                          <span>Win rate</span>
                          <strong>{model.win_rate_pct.toFixed(1)}%</strong>
                        </div>
                        <div>
                          <span>Total</span>
                          <strong className={model.total_return_pct >= 0 ? "change-positive" : "change-negative"}>
                            {formatPercent(model.total_return_pct)}
                          </strong>
                        </div>
                        <div>
                          <span>MDD</span>
                          <strong className="change-negative">{model.max_drawdown_pct.toFixed(2)}%</strong>
                        </div>
                      </div>
                      {model.equity_curve.length ? (
                        <svg
                          className="model-equity-curve"
                          viewBox={`0 0 ${curve.width} ${curve.height}`}
                          role="img"
                          aria-label={`${model.name} equity curve`}
                        >
                          <line x1="0" y1={curve.baseline} x2={curve.width} y2={curve.baseline} />
                          <path d={curve.path} />
                        </svg>
                      ) : null}
                      <div className="model-meta">
                        <span>{model.observations.toLocaleString()} observations</span>
                        <span>{model.exposure_pct.toFixed(1)}% exposure</span>
                        <span>{model.trades.toLocaleString()} position changes</span>
                        {model.backtest_start && model.backtest_end ? (
                          <span>{model.backtest_start} to {model.backtest_end}</span>
                        ) : null}
                      </div>
                      <p>{model.message}</p>
                      <div className="feature-pills">
                        {model.features.slice(0, 8).map((feature) => (
                          <span key={`${model.file_name}-${feature}`}>{feature}</span>
                        ))}
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
            <div className="model-instructions">
              {modelBacktests.instructions.map((instruction) => (
                <span key={instruction}>{instruction}</span>
              ))}
            </div>
            <p className="disclaimer">{modelBacktests.disclaimer}</p>
          </div>

          <div className="panel">
            <h2>News Signals</h2>
            <div className="news-toolbar" aria-label="News sentiment filter">
              {["all", "positive", "neutral", "negative"].map((filter) => (
                <button
                  className={newsFilter === filter ? "filter-active" : ""}
                  key={filter}
                  onClick={() => setNewsFilter(filter)}
                  type="button"
                >
                  {filter}
                </button>
              ))}
            </div>
            <div className="news-card-list">
              {filteredNews.map((item) => {
                const key = newsKey(item);
                const selected = selectedNewsKey === key;

                return (
                  <article className="news-card" key={key}>
                    <button
                      aria-expanded={selected}
                      className="news-toggle"
                      onClick={() => setSelectedNewsKey(selected ? null : key)}
                      type="button"
                    >
                      <span>
                        {item.title}
                        <small>{formatNewsTime(item.published_at)}</small>
                      </span>
                      <strong className={`sentiment-${item.sentiment}`}>
                        {item.sentiment}
                      </strong>
                    </button>
                    {item.summary ? (
                      <p className="news-summary">{item.summary}</p>
                    ) : null}
                    {selected ? (
                      <div className="news-detail">
                        <span>Source: {item.source}</span>
                        <span>Data: {item.data_source}</span>
                        {item.url ? (
                          <a href={item.url} rel="noreferrer" target="_blank">
                            Open original
                          </a>
                        ) : null}
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          </div>

          <div className="panel">
            <h2>Risk Notes</h2>
            <ul className="risk-list">
              {report.risks.map((risk) => (
                <li key={risk}>{risk}</li>
              ))}
            </ul>
            <p className="disclaimer">{report.disclaimer}</p>
          </div>
        </section>
      </div>
    </main>
  );
}
