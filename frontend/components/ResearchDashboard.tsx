"use client";

import { useEffect, useState } from "react";
import {
  fallbackMarkets,
  fallbackReport,
  fetchBtcResearch,
  fetchMarketsOverview,
  type IndexChart,
  type MarketInstrument,
  type MarketsOverview,
  type NewsItem,
  type ResearchReport,
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
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: item.currency,
    maximumFractionDigits: item.currency === "JPY" || item.currency === "KRW" ? 0 : 2,
  }).format(item.price);
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
) {
  return values
    .map((value, index) => {
      if (value === null) {
        return "";
      }

      const command = values.slice(0, index).some((previous) => previous !== null) ? "L" : "M";
      return `${command} ${slot * index + slot / 2} ${yForValue(value)}`;
    })
    .filter(Boolean)
    .join(" ");
}

function chartGeometry(points: IndexChart["points"], size: ChartSize) {
  const width = 280;
  const height = CHART_SIZES[size].height;
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
  const slot = sampledPoints.length ? width / sampledPoints.length : width;
  const bodyWidth = Math.max(1.5, Math.min(8, slot * 0.58));
  const priceHeight = Math.round(height * 0.72);
  const rsiTop = priceHeight + 12;
  const rsiHeight = Math.max(36, height - rsiTop);
  const priceY = (value: number) => priceHeight - ((value - min) / range) * priceHeight;
  const rsiY = (value: number) => rsiTop + rsiHeight - (value / 100) * rsiHeight;

  const candles = sampledPoints.map((point, index) => {
    const centerX = slot * index + slot / 2;
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
    upperPath: scaledPath(bollinger.map((band) => band.upper), priceY, slot),
    middlePath: scaledPath(sma20, priceY, slot),
    lowerPath: scaledPath(bollinger.map((band) => band.lower), priceY, slot),
    rsiPath: scaledPath(rsi14, rsiY, slot),
    height,
    priceBaseline: priceHeight,
    rsiTop,
    rsiHeight,
    rsi30: rsiY(30),
    rsi70: rsiY(70),
    sampledCount: sampledPoints.length,
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

export function ResearchDashboard() {
  const [report, setReport] = useState<ResearchReport>(fallbackReport);
  const [markets, setMarkets] = useState<MarketsOverview>(fallbackMarkets);
  const [newsFilter, setNewsFilter] = useState("all");
  const [selectedNewsKey, setSelectedNewsKey] = useState<string | null>(null);
  const [chartRange, setChartRange] = useState("10y");
  const [chartSize, setChartSize] = useState<ChartSize>("medium");
  const [showBollinger, setShowBollinger] = useState(true);
  const [showRsi, setShowRsi] = useState(true);

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
            <div className="index-chart-grid" aria-label="Major index price plots">
              {markets.index_charts.map((chart) => {
                const visiblePoints = visibleChartPoints(chart, chartRange);
                const visibleChart = { ...chart, points: visiblePoints };
                const geometry = chartGeometry(visiblePoints, chartSize);
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
                      viewBox={`0 0 280 ${geometry.height}`}
                      role="img"
                      aria-label={`${chart.name} candlestick plot with technical indicators`}
                    >
                      <line x1="0" y1={geometry.priceBaseline} x2="280" y2={geometry.priceBaseline} />
                      {showRsi ? (
                        <>
                          <line className="rsi-guide" x1="0" y1={geometry.rsi70} x2="280" y2={geometry.rsi70} />
                          <line className="rsi-guide" x1="0" y1={geometry.rsi30} x2="280" y2={geometry.rsi30} />
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
