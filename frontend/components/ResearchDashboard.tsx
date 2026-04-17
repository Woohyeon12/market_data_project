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
  type ResearchReport,
} from "../lib/api";

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

function candleGeometry(chart: IndexChart) {
  const width = 280;
  const height = 96;
  const highs = chart.points.map((point) => point.high);
  const lows = chart.points.map((point) => point.low);
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const range = max - min || 1;
  const slot = chart.points.length ? width / chart.points.length : width;
  const bodyWidth = Math.max(4, Math.min(12, slot * 0.58));

  return chart.points.map((point, index) => {
    const centerX = slot * index + slot / 2;
    const y = (value: number) => height - ((value - min) / range) * height;
    const openY = y(point.open);
    const closeY = y(point.close);
    const highY = y(point.high);
    const lowY = y(point.low);
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
}

export function ResearchDashboard() {
  const [report, setReport] = useState<ResearchReport>(fallbackReport);
  const [markets, setMarkets] = useState<MarketsOverview>(fallbackMarkets);

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
            <div className="index-chart-grid" aria-label="Major index price plots">
              {markets.index_charts.map((chart) => {
                const changePct = chartChangePct(chart);
                const firstPoint = chart.points[0];
                const lastPoint = chart.points[chart.points.length - 1];

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
                      viewBox="0 0 280 96"
                      role="img"
                      aria-label={`${chart.name} one month candlestick plot`}
                    >
                      <line x1="0" y1="92" x2="280" y2="92" />
                      {candleGeometry(chart).map((candle) => (
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
            <ul className="news-list">
              {report.news.map((item) => (
                <li key={`${item.source}-${item.title}`}>
                  {item.title} <strong>({item.sentiment})</strong>
                  <span className="item-source">Source: {item.data_source}</span>
                </li>
              ))}
            </ul>
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
