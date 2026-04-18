"use client";

import { Fragment, useEffect, useState } from "react";
import {
  fallbackMarkets,
  fallbackModelBacktests,
  fallbackReport,
  fetchBtcResearch,
  fetchMarketsOverview,
  fetchModelBacktests,
  type EquityFundamental,
  type FinancialStatementPeriod,
  type IndexChart,
  type MarketInstrument,
  type MarketsOverview,
  type ModelBacktestOverview,
  type ModelBacktestResult,
  type ModelEquityPoint,
  type KaggleModelResult,
  type KaggleModelRun,
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

const DASHBOARD_PAGES = [
  {
    value: "overview",
    label: "Overview",
    description: "BTC snapshot, research summary, and scenarios",
  },
  {
    value: "markets",
    label: "Markets",
    description: "Global charts, bonds, stocks, indices, and gold",
  },
  {
    value: "fundamentals",
    label: "Fundamentals",
    description: "Stock statements, ratios, and financial model scores",
  },
  {
    value: "signals",
    label: "Signals",
    description: "Feature heatmap, drivers, and lead-lag signals",
  },
  {
    value: "models",
    label: "Models",
    description: "Two-year model backtests and equity curves",
  },
  {
    value: "news",
    label: "News & Risk",
    description: "News summaries, source links, and risk notes",
  },
] as const;

const FUNDAMENTAL_SORT_OPTIONS = [
  { label: "ROE", value: "fundamental_roe", direction: "desc" },
  { label: "Revenue growth", value: "fundamental_revenue_growth_yoy", direction: "desc" },
  { label: "FCF margin", value: "fundamental_fcf_margin", direction: "desc" },
  { label: "Market cap", value: "fundamental_market_cap_b", direction: "desc" },
  { label: "Low PER", value: "fundamental_trailing_pe", direction: "asc" },
  { label: "Low P/B", value: "fundamental_price_to_book", direction: "asc" },
  { label: "Low leverage", value: "fundamental_debt_to_equity", direction: "asc" },
] as const;

type ChartSize = keyof typeof CHART_SIZES;
type DashboardPage = (typeof DASHBOARD_PAGES)[number]["value"];
type FundamentalSort = (typeof FUNDAMENTAL_SORT_OPTIONS)[number]["value"];

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

function formatFinancialValue(value?: number | null, currency = "USD") {
  if (value === null || value === undefined) {
    return "n/a";
  }

  const absValue = Math.abs(value);
  const suffixes = [
    { threshold: 1_000_000_000_000, suffix: "T" },
    { threshold: 1_000_000_000, suffix: "B" },
    { threshold: 1_000_000, suffix: "M" },
  ];
  const selected = suffixes.find((item) => absValue >= item.threshold);

  if (!selected) {
    return new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 0,
    }).format(value);
  }

  const formatted = (value / selected.threshold).toFixed(1);
  return `${currency} ${formatted}${selected.suffix}`;
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

function formatShortDateTime(value?: string | null) {
  if (!value) {
    return "n/a";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, "0")}-${String(parsed.getDate()).padStart(2, "0")}`;
}

function normalizedPercentWidth(value: number, maxAbsValue: number) {
  const denominator = Math.max(Math.abs(maxAbsValue), 0.0001);
  return `${Math.min(Math.abs(value) / denominator, 1) * 100}%`;
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function average(values: number[]) {
  if (!values.length) {
    return 0;
  }

  return values.reduce((total, value) => total + value, 0) / values.length;
}

function standardDeviation(values: number[]) {
  if (values.length < 2) {
    return 0;
  }

  const mean = average(values);
  const variance = average(values.map((value) => (value - mean) ** 2));
  return Math.sqrt(variance);
}

function sampledEquityReturn(points: ModelEquityPoint[], fallbackReturn: number) {
  if (points.length < 2) {
    return fallbackReturn;
  }

  const first = points[0].equity || 1;
  const last = points[points.length - 1].equity || first;
  return ((last / first) - 1) * 100;
}

function equitySplitReturns(points: ModelEquityPoint[], fallbackReturn: number) {
  if (points.length < 8) {
    return [fallbackReturn];
  }

  const splitSize = Math.ceil(points.length / 4);
  return [0, 1, 2, 3]
    .map((split) => points.slice(split * splitSize, (split + 1) * splitSize))
    .filter((chunk) => chunk.length >= 2)
    .map((chunk) => {
      const first = chunk[0].equity || 1;
      const last = chunk[chunk.length - 1].equity || first;
      return ((last / first) - 1) * 100;
    });
}

type ShowcaseModel = {
  id: string;
  name: string;
  source: string;
  modelType: string;
  status: string;
  message: string;
  createdAt?: string | null;
  backtestStart?: string | null;
  backtestEnd?: string | null;
  sharpeRatio: number;
  grossSharpeRatio?: number | null;
  winRatePct: number;
  totalReturnPct: number;
  grossTotalReturnPct?: number | null;
  maxDrawdownPct: number;
  exposurePct: number;
  trades: number;
  totalTransactionCostPct?: number | null;
  observations: number;
  activeObservations: number;
  returnSinceStartPct: number;
  stabilityScore: number;
  stabilityLabel: string;
  positiveSplitCount: number;
  splitCount: number;
  splitReturnStd: number;
  splitReturns: number[];
  features: string[];
  featureCount?: number | null;
  featureCandidateCount?: number | null;
  selectedFeatureCount?: number | null;
  selectedBaseFeatureCount?: number | null;
  selectedInteractionFeatureCount?: number | null;
  selectedBaseFloorMet?: boolean | null;
  selectedThreshold?: number | null;
  selectedShortThreshold?: number | null;
  selectedScoreMargin?: number | null;
  strategySide?: string | null;
  validationSharpeRatio?: number | null;
  sharpeTarget?: number | null;
  targetMet?: boolean | null;
  packageCandidate?: boolean | null;
  worstSplitSharpe?: number | null;
  validationTestSharpeGap?: number | null;
  transactionCostBps?: number | null;
  slippageBps?: number | null;
  readinessLabel: string;
  readinessTone: "ready" | "watch" | "hold";
  readinessReasons: string[];
  equityCurve: ModelEquityPoint[];
};

function stabilityLabel(score: number) {
  if (score >= 78) {
    return "Stable candidate";
  }

  if (score >= 62) {
    return "Promising";
  }

  if (score >= 45) {
    return "Needs monitoring";
  }

  return "Fragile";
}

function featureSelectionNumber(selection: KaggleModelResult["feature_selection"], key: string) {
  const value = selection?.[key];
  if (typeof value === "number") {
    return value;
  }

  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isNaN(parsed) ? null : parsed;
  }

  return null;
}

function featureSelectionBoolean(selection: KaggleModelResult["feature_selection"], key: string) {
  const value = selection?.[key];
  return typeof value === "boolean" ? value : null;
}

function buildStabilityScore(model: {
  sharpeRatio: number;
  winRatePct: number;
  maxDrawdownPct: number;
  splitReturns: number[];
}) {
  const splitReturns = model.splitReturns.length ? model.splitReturns : [0];
  const positiveRatio = splitReturns.filter((value) => value > 0).length / splitReturns.length;
  const consistency = 1 - clamp(standardDeviation(splitReturns) / 18, 0, 1);
  const drawdownControl = 1 - clamp(Math.abs(model.maxDrawdownPct) / 35, 0, 1);
  const sharpeQuality = clamp((model.sharpeRatio + 0.5) / 2.2, 0, 1);
  const winQuality = clamp((model.winRatePct - 42) / 18, 0, 1);

  return Math.round(
    positiveRatio * 28 +
    consistency * 24 +
    drawdownControl * 20 +
    sharpeQuality * 18 +
    winQuality * 10,
  );
}

function buildModelReadiness(model: {
  sharpeRatio: number;
  sharpeTarget?: number | null;
  targetMet?: boolean | null;
  packageCandidate?: boolean | null;
  rejectionReasons?: string[];
  validationSharpeRatio?: number | null;
  maxDrawdownPct: number;
  splitReturns: number[];
}) {
  const target = model.sharpeTarget ?? 2;
  const positiveSplitCount = model.splitReturns.filter((value) => value > 0).length;
  const splitCount = Math.max(1, model.splitReturns.length);
  const positiveSplitRatio = positiveSplitCount / splitCount;
  const splitVolatility = standardDeviation(model.splitReturns);
  const reasons = [...(model.rejectionReasons ?? [])];

  if ((model.targetMet === false || model.sharpeRatio < target) && reasons.length === 0) {
    reasons.push(`Latest 2Y Sharpe ${model.sharpeRatio.toFixed(2)} is below ${target.toFixed(1)} target`);
  }

  if (
    model.validationSharpeRatio !== null &&
    model.validationSharpeRatio !== undefined &&
    model.validationSharpeRatio >= target &&
    model.sharpeRatio < target
  ) {
    reasons.push("Validation looked stronger than the recent backtest, so regime decay is likely");
  }

  if (positiveSplitRatio < 0.75) {
    reasons.push(`Only ${positiveSplitCount}/${splitCount} splits are positive`);
  }

  if (splitVolatility > 18) {
    reasons.push(`Split return dispersion is high at ${splitVolatility.toFixed(1)}%`);
  }

  if (model.maxDrawdownPct <= -20) {
    reasons.push(`Drawdown reached ${model.maxDrawdownPct.toFixed(1)}%`);
  }

  if (reasons.length === 0 && model.packageCandidate !== false) {
    return {
      label: "Package candidate",
      tone: "ready" as const,
      reasons: ["Meets the current Sharpe target and split stability gates"],
    };
  }

  if (model.sharpeRatio >= 1 && positiveSplitRatio >= 0.5) {
    return {
      label: "Watchlist only",
      tone: "watch" as const,
      reasons,
    };
  }

  return {
    label: "Research hold",
    tone: "hold" as const,
    reasons,
  };
}

function fromLocalModel(model: ModelBacktestResult): ShowcaseModel {
  const splitReturns = equitySplitReturns(model.equity_curve, model.total_return_pct);
  const returnSinceStartPct = sampledEquityReturn(model.equity_curve, model.total_return_pct);
  const stabilityScore = buildStabilityScore({
    sharpeRatio: model.sharpe_ratio,
    winRatePct: model.win_rate_pct,
    maxDrawdownPct: model.max_drawdown_pct,
    splitReturns,
  });
  const readiness = buildModelReadiness({
    sharpeRatio: model.sharpe_ratio,
    maxDrawdownPct: model.max_drawdown_pct,
    splitReturns,
  });

  return {
    id: `local-${model.file_name}-${model.name}`,
    name: model.name,
    source: "Local registry",
    modelType: model.model_type,
    status: model.status,
    message: model.message,
    backtestStart: model.backtest_start,
    backtestEnd: model.backtest_end,
    sharpeRatio: model.sharpe_ratio,
    grossSharpeRatio: model.sharpe_ratio,
    winRatePct: model.win_rate_pct,
    totalReturnPct: model.total_return_pct,
    grossTotalReturnPct: model.total_return_pct,
    maxDrawdownPct: model.max_drawdown_pct,
    exposurePct: model.exposure_pct,
    trades: model.trades,
    totalTransactionCostPct: 0,
    observations: model.observations,
    activeObservations: model.observations,
    returnSinceStartPct,
    stabilityScore,
    stabilityLabel: stabilityLabel(stabilityScore),
    positiveSplitCount: splitReturns.filter((value) => value > 0).length,
    splitCount: splitReturns.length,
    splitReturnStd: standardDeviation(splitReturns),
    splitReturns,
    features: model.features,
    featureCount: model.features.length,
    featureCandidateCount: model.features.length,
    selectedFeatureCount: model.features.length,
    readinessLabel: readiness.label,
    readinessTone: readiness.tone,
    readinessReasons: readiness.reasons,
    equityCurve: model.equity_curve,
  };
}

function fromKaggleModel(run: KaggleModelRun, model: KaggleModelResult): ShowcaseModel {
  const splitReturns = model.split_metrics.length
    ? model.split_metrics.map((split) => split.total_return_pct)
    : equitySplitReturns(model.equity_curve, model.total_return_pct);
  const returnSinceStartPct = sampledEquityReturn(model.equity_curve, model.total_return_pct);
  const stabilityScore = buildStabilityScore({
    sharpeRatio: model.sharpe_ratio,
    winRatePct: model.win_rate_pct,
    maxDrawdownPct: model.max_drawdown_pct,
    splitReturns,
  });
  const readiness = buildModelReadiness({
    sharpeRatio: model.sharpe_ratio,
    sharpeTarget: model.sharpe_target,
    targetMet: model.target_met,
    packageCandidate: model.package_candidate,
    rejectionReasons: model.rejection_reasons,
    validationSharpeRatio: model.validation_sharpe_ratio,
    maxDrawdownPct: model.max_drawdown_pct,
    splitReturns,
  });

  return {
    id: `kaggle-${run.run_id}-${model.name}`,
    name: model.name,
    source: "Kaggle GPU",
    modelType: model.model_type,
    status: model.status,
    message: model.message,
    createdAt: run.generated_at,
    backtestStart: model.backtest_start,
    backtestEnd: model.backtest_end,
    sharpeRatio: model.sharpe_ratio,
    grossSharpeRatio: model.gross_sharpe_ratio,
    winRatePct: model.win_rate_pct,
    totalReturnPct: model.total_return_pct,
    grossTotalReturnPct: model.gross_total_return_pct,
    maxDrawdownPct: model.max_drawdown_pct,
    exposurePct: model.exposure_pct,
    trades: model.trades,
    totalTransactionCostPct: model.total_transaction_cost_pct,
    observations: model.observations,
    activeObservations: model.active_observations,
    returnSinceStartPct,
    stabilityScore,
    stabilityLabel: stabilityLabel(stabilityScore),
    positiveSplitCount: splitReturns.filter((value) => value > 0).length,
    splitCount: splitReturns.length,
    splitReturnStd: standardDeviation(splitReturns),
    splitReturns,
    features: model.features,
    featureCount: model.feature_count,
    featureCandidateCount: model.feature_candidate_count,
    selectedFeatureCount: model.selected_feature_count,
    selectedBaseFeatureCount: featureSelectionNumber(model.feature_selection, "selected_base_feature_count"),
    selectedInteractionFeatureCount: featureSelectionNumber(model.feature_selection, "selected_interaction_feature_count"),
    selectedBaseFloorMet: featureSelectionBoolean(model.feature_selection, "selected_base_floor_met"),
    selectedThreshold: model.selected_threshold,
    selectedShortThreshold: model.selected_short_threshold,
    selectedScoreMargin: model.selected_score_margin,
    strategySide: model.strategy_side,
    validationSharpeRatio: model.validation_sharpe_ratio,
    sharpeTarget: model.sharpe_target,
    targetMet: model.target_met,
    packageCandidate: model.package_candidate,
    worstSplitSharpe: model.worst_split_sharpe,
    validationTestSharpeGap: model.validation_test_sharpe_gap,
    transactionCostBps: model.transaction_cost_bps,
    slippageBps: model.slippage_bps,
    readinessLabel: readiness.label,
    readinessTone: readiness.tone,
    readinessReasons: readiness.reasons,
    equityCurve: model.equity_curve,
  };
}

function metricDisplayValue(value: number, unit: string) {
  if (unit === "%") {
    return `${value.toFixed(1)}%`;
  }

  if (unit === "x") {
    return `${value.toFixed(2)}x`;
  }

  if (unit === "B") {
    return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}B`;
  }

  return value.toFixed(2);
}

function fundamentalSortUnit(sort: FundamentalSort) {
  if (sort === "fundamental_market_cap_b") {
    return "B";
  }

  if (
    sort === "fundamental_debt_to_equity" ||
    sort === "fundamental_trailing_pe" ||
    sort === "fundamental_price_to_book"
  ) {
    return "x";
  }

  return "%";
}

function topStatementPeriods(item: EquityFundamental) {
  return item.periods.slice(0, 3);
}

function statementKey(symbol: string, period: FinancialStatementPeriod) {
  return `${symbol}-${period.fiscal_date}`;
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
  const [activePage, setActivePage] = useState<DashboardPage>("overview");
  const [fundamentalSort, setFundamentalSort] = useState<FundamentalSort>("fundamental_roe");
  const [selectedModelIndex, setSelectedModelIndex] = useState(0);

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

  useEffect(() => {
    setSelectedModelIndex(0);
  }, [modelBacktests.generated_at]);

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
  const equityFundamentals = markets.equity_fundamentals ?? [];
  const fundamentalModelScores = markets.fundamental_model_scores ?? [];
  const selectedFundamentalSort = FUNDAMENTAL_SORT_OPTIONS.find((option) => {
    return option.value === fundamentalSort;
  }) ?? FUNDAMENTAL_SORT_OPTIONS[0];
  const sortedEquityFundamentals = [...equityFundamentals].sort((first, second) => {
    const missingValue = selectedFundamentalSort.direction === "asc"
      ? Number.POSITIVE_INFINITY
      : Number.NEGATIVE_INFINITY;
    const firstValue = first.model_features[fundamentalSort] ?? missingValue;
    const secondValue = second.model_features[fundamentalSort] ?? missingValue;

    if (selectedFundamentalSort.direction === "asc") {
      return firstValue - secondValue;
    }

    return secondValue - firstValue;
  });
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
  const latestKaggleRun = modelBacktests.kaggle_runs[0];
  const kaggleModelCount = modelBacktests.kaggle_runs.reduce((total, run) => {
    return total + run.models.length;
  }, 0);
  const topKaggleModel = latestKaggleRun?.models[0];
  const topKaggleImportance = topKaggleModel?.feature_importance.slice(0, 8) ?? [];
  const topKaggleSplitCorrelations = topKaggleModel?.split_correlations.slice(0, 20) ?? [];
  const maxKaggleImportance = Math.max(
    0.01,
    ...topKaggleImportance.map((item) => item.importance),
  );
  const maxKaggleCorrelation = Math.max(
    0.01,
    ...topKaggleSplitCorrelations.map((item) => Math.abs(item.correlation)),
  );
  const showcaseModels = [
    ...modelBacktests.results.map(fromLocalModel),
    ...modelBacktests.kaggle_runs.flatMap((run) => {
      return run.models.map((model) => fromKaggleModel(run, model));
    }),
  ].sort((first, second) => {
    return second.stabilityScore - first.stabilityScore || second.sharpeRatio - first.sharpeRatio;
  });
  const selectedModel = showcaseModels.length
    ? showcaseModels[selectedModelIndex % showcaseModels.length]
    : null;
  const comparisonModels = showcaseModels.length
    ? [0, 1, 2, 3].map((offset) => showcaseModels[(selectedModelIndex + offset) % showcaseModels.length])
    : [];
  const averageStability = Math.round(average(showcaseModels.map((model) => model.stabilityScore)));
  const modelCarouselPosition = showcaseModels.length ? selectedModelIndex + 1 : 0;
  const goToModelOffset = (offset: number) => {
    if (!showcaseModels.length) {
      return;
    }

    setSelectedModelIndex((current) => {
      return (current + offset + showcaseModels.length) % showcaseModels.length;
    });
  };
  const pageStats: Record<DashboardPage, string> = {
    overview: `${report.scenarios.length} scenarios`,
    markets: `${chartSet.length} charts`,
    fundamentals: `${equityFundamentals.length} stocks`,
    signals: `${markets.correlations.assets.length} features`,
    models: `${modelBacktests.results.length + kaggleModelCount} models`,
    news: `${filteredNews.length} news`,
  };
  const activePageIndex = DASHBOARD_PAGES.findIndex((page) => page.value === activePage);
  const activePageInfo = DASHBOARD_PAGES[activePageIndex] ?? DASHBOARD_PAGES[0];
  const goToPageOffset = (offset: number) => {
    const nextIndex = (activePageIndex + offset + DASHBOARD_PAGES.length) % DASHBOARD_PAGES.length;
    setActivePage(DASHBOARD_PAGES[nextIndex].value);
  };

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

        <nav className="page-switcher" aria-label="Dashboard page list">
          {DASHBOARD_PAGES.map((dashboardPage) => (
            <button
              aria-current={activePage === dashboardPage.value ? "page" : undefined}
              className={activePage === dashboardPage.value ? "page-tab-active" : ""}
              key={dashboardPage.value}
              onClick={() => setActivePage(dashboardPage.value)}
              type="button"
            >
              <strong>{dashboardPage.label}</strong>
              <span>{dashboardPage.description}</span>
              <em>{pageStats[dashboardPage.value]}</em>
            </button>
          ))}
        </nav>

        <div className="page-turner" aria-label="Dashboard page controls">
          <button onClick={() => goToPageOffset(-1)} type="button">
            Previous
          </button>
          <span>
            {activePageIndex + 1} / {DASHBOARD_PAGES.length} - {activePageInfo.label}
          </span>
          <button onClick={() => goToPageOffset(1)} type="button">
            Next
          </button>
        </div>

        <section className="grid" aria-label="Bitcoin research dashboard">
          <div className="panel snapshot-panel" hidden={activePage !== "overview"}>
            <h2>Market Snapshot</h2>
            <p className="source-label">Source: {report.market.data_source}</p>
            <div className="metric-row">
              <div className="metric">
                <div className="metric-label">BTC Price</div>
                <p className="metric-value">{formatUsd(report.market.price_usd)}</p>
              </div>
              <div className="metric">
                <div className="metric-label">24h</div>
                <p className="metric-value">{report.market.change_24h_pct}%</p>
              </div>
              <div className="metric">
                <div className="metric-label">Volume</div>
                <p className="metric-value">
                  {formatCompactUsd(report.market.volume_24h_usd)}
                </p>
              </div>
            </div>
          </div>

          <div className="panel" hidden={activePage !== "overview"}>
            <h2>Research Summary</h2>
            <ul className="summary-list">
              {report.summary.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="panel" hidden={activePage !== "overview"}>
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

          <div className="panel" hidden={activePage !== "markets"}>
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

          <div className="panel" hidden={activePage !== "fundamentals"}>
            <h2>Equity Fundamentals</h2>
            <p className="source-label">
              Annual statements, derived ratios, and model-ready financial features for tracked stocks.
            </p>
            <div className="fundamental-toolbar" aria-label="Fundamental sorting controls">
              <span>Sort stocks by</span>
              <div className="segmented-control">
                {FUNDAMENTAL_SORT_OPTIONS.map((option) => (
                  <button
                    className={fundamentalSort === option.value ? "control-active" : ""}
                    key={option.value}
                    onClick={() => setFundamentalSort(option.value)}
                    type="button"
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="fundamental-grid" aria-label="Equity financial statement summaries">
              {sortedEquityFundamentals.map((item) => {
                const sortValue = item.model_features[fundamentalSort];

                return (
                  <article className="fundamental-card" key={item.symbol}>
                    <div className="fundamental-header">
                      <div>
                        <h3>{item.name}</h3>
                        <span>{item.symbol} - {item.market} - {item.data_source}</span>
                      </div>
                      <div className="fundamental-badges">
                        <strong>{item.currency}</strong>
                        <span title={`Current sort: ${selectedFundamentalSort.label}`}>
                          {selectedFundamentalSort.label}:{" "}
                          {sortValue === undefined
                            ? "n/a"
                            : metricDisplayValue(sortValue, fundamentalSortUnit(fundamentalSort))}
                        </span>
                      </div>
                    </div>
                    <div className="fundamental-metrics">
                      {item.metrics.slice(0, 8).map((metric) => (
                        <div key={`${item.symbol}-${metric.key}`} title={metric.interpretation}>
                          <span>{metric.label}</span>
                          <strong>{metricDisplayValue(metric.value, metric.unit)}</strong>
                        </div>
                      ))}
                    </div>
                    <div className="financial-table">
                      <div className="financial-row financial-row-head">
                        <span>Fiscal</span>
                        <span>Revenue</span>
                        <span>Net income</span>
                        <span>FCF</span>
                      </div>
                      {topStatementPeriods(item).map((period) => (
                        <div className="financial-row" key={statementKey(item.symbol, period)}>
                          <span>{period.fiscal_date}</span>
                          <span>{formatFinancialValue(period.revenue, item.currency)}</span>
                          <span>{formatFinancialValue(period.net_income, item.currency)}</span>
                          <span>{formatFinancialValue(period.free_cash_flow, item.currency)}</span>
                        </div>
                      ))}
                    </div>
                    <div className="feature-pills">
                      {Object.keys(item.model_features).slice(0, 8).map((feature) => (
                        <span key={`${item.symbol}-${feature}`}>{feature}</span>
                      ))}
                    </div>
                  </article>
                );
              })}
            </div>
            {fundamentalModelScores.length ? (
              <div className="fundamental-scoreboard" aria-label="Fundamental model scores">
                <h3>Fundamental model scores</h3>
                {fundamentalModelScores.slice(0, 12).map((score) => (
                  <div className="fundamental-score-row" key={`${score.file_name}-${score.symbol}`}>
                    <span>{score.company}</span>
                    <span>{score.model_name}</span>
                    <strong>{score.score.toFixed(3)}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <strong>No enabled fundamental model yet.</strong>
                <p>
                  Add a JSON model with target equity_fundamental_score to score stocks from financial statement metrics.
                </p>
              </div>
            )}
            <p className="disclaimer">{markets.disclaimer}</p>
          </div>

          <div className="panel" hidden={activePage !== "signals"}>
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

          <div className="panel" hidden={activePage !== "models"}>
            <h2>Model Backtest Lab</h2>
            <p className="source-label">
              Folder: {modelBacktests.model_folder} - {modelBacktests.evaluation_window}
            </p>
            {selectedModel ? (
              <div className="model-showcase" aria-label="Trading model performance showcase">
                <div className="showcase-header">
                  <div>
                    <p className="eyebrow">Model Marketplace View</p>
                    <h3>{selectedModel.name}</h3>
                    <p>
                      {selectedModel.source} - {selectedModel.modelType} - {selectedModel.stabilityLabel}
                    </p>
                  </div>
                  <div className="model-carousel-controls">
                    <button onClick={() => goToModelOffset(-1)} type="button">
                      Previous model
                    </button>
                    <span>
                      {modelCarouselPosition} / {showcaseModels.length}
                    </span>
                    <button onClick={() => goToModelOffset(1)} type="button">
                      Next model
                    </button>
                  </div>
                </div>
                <div className="showcase-hero">
                  <div className="showcase-score">
                    <span>Stability score</span>
                    <strong>{selectedModel.stabilityScore}</strong>
                    <em>Average {averageStability || 0}</em>
                  </div>
                  <div className="showcase-metrics">
                    <div>
                      <span>Sharpe</span>
                      <strong>{selectedModel.sharpeRatio.toFixed(2)}</strong>
                    </div>
                    <div>
                      <span>Win rate</span>
                      <strong>{selectedModel.winRatePct.toFixed(1)}%</strong>
                    </div>
                    <div>
                      <span>Backtest total</span>
                      <strong className={selectedModel.totalReturnPct >= 0 ? "change-positive" : "change-negative"}>
                        {formatPercent(selectedModel.totalReturnPct)}
                      </strong>
                    </div>
                    <div>
                      <span>Since model start</span>
                      <strong className={selectedModel.returnSinceStartPct >= 0 ? "change-positive" : "change-negative"}>
                        {formatPercent(selectedModel.returnSinceStartPct)}
                      </strong>
                    </div>
                    <div>
                      <span>Max drawdown</span>
                      <strong className="change-negative">{selectedModel.maxDrawdownPct.toFixed(2)}%</strong>
                    </div>
                    <div>
                      <span>Positive splits</span>
                      <strong>{selectedModel.positiveSplitCount}/{selectedModel.splitCount}</strong>
                    </div>
                  </div>
                </div>
                <div className={`model-readiness model-readiness-${selectedModel.readinessTone}`}>
                  <div>
                    <span>Model readiness</span>
                    <strong>{selectedModel.readinessLabel}</strong>
                  </div>
                  <ul>
                    {selectedModel.readinessReasons.slice(0, 3).map((reason) => (
                      <li key={`${selectedModel.id}-${reason}`}>{reason}</li>
                    ))}
                  </ul>
                </div>
                <div className="showcase-detail-grid">
                  <div>
                    <span>Created</span>
                    <strong>{formatShortDateTime(selectedModel.createdAt)}</strong>
                  </div>
                  <div>
                    <span>Backtest window</span>
                    <strong>{selectedModel.backtestStart ?? "n/a"} to {selectedModel.backtestEnd ?? "n/a"}</strong>
                  </div>
                  <div>
                    <span>Exposure</span>
                    <strong>{selectedModel.exposurePct.toFixed(1)}%</strong>
                  </div>
                  <div>
                    <span>Active observations</span>
                    <strong>{selectedModel.activeObservations.toLocaleString()} / {selectedModel.observations.toLocaleString()}</strong>
                  </div>
                  <div>
                    <span>Split return volatility</span>
                    <strong>{selectedModel.splitReturnStd.toFixed(2)}%</strong>
                  </div>
                  <div>
                    <span>Position changes</span>
                    <strong>{selectedModel.trades.toLocaleString()}</strong>
                  </div>
                  <div>
                    <span>Sharpe target</span>
                    <strong className={selectedModel.targetMet ? "change-positive" : "change-negative"}>
                      {selectedModel.sharpeTarget ? selectedModel.sharpeTarget.toFixed(1) : "n/a"}
                    </strong>
                  </div>
                  <div>
                    <span>Validation Sharpe</span>
                    <strong>{selectedModel.validationSharpeRatio !== null && selectedModel.validationSharpeRatio !== undefined ? selectedModel.validationSharpeRatio.toFixed(2) : "n/a"}</strong>
                  </div>
                  <div>
                    <span>Gross Sharpe</span>
                    <strong>{selectedModel.grossSharpeRatio !== null && selectedModel.grossSharpeRatio !== undefined ? selectedModel.grossSharpeRatio.toFixed(2) : "n/a"}</strong>
                  </div>
                  <div>
                    <span>Cost drag</span>
                    <strong>{selectedModel.totalTransactionCostPct !== null && selectedModel.totalTransactionCostPct !== undefined ? `${selectedModel.totalTransactionCostPct.toFixed(2)}%` : "n/a"}</strong>
                  </div>
                  <div>
                    <span>Worst split Sharpe</span>
                    <strong>{selectedModel.worstSplitSharpe !== null && selectedModel.worstSplitSharpe !== undefined ? selectedModel.worstSplitSharpe.toFixed(2) : "n/a"}</strong>
                  </div>
                  <div>
                    <span>Feature count</span>
                    <strong>{selectedModel.selectedFeatureCount?.toLocaleString() ?? selectedModel.featureCount?.toLocaleString() ?? selectedModel.features.length.toLocaleString()}</strong>
                  </div>
                  <div>
                    <span>Candidate pool</span>
                    <strong>{selectedModel.featureCandidateCount?.toLocaleString() ?? "n/a"}</strong>
                  </div>
                  <div>
                    <span>Base / interaction</span>
                    <strong>
                      {selectedModel.selectedBaseFeatureCount !== null && selectedModel.selectedBaseFeatureCount !== undefined
                        ? selectedModel.selectedBaseFeatureCount.toLocaleString()
                        : "n/a"}
                      {" / "}
                      {selectedModel.selectedInteractionFeatureCount !== null && selectedModel.selectedInteractionFeatureCount !== undefined
                        ? selectedModel.selectedInteractionFeatureCount.toLocaleString()
                        : "n/a"}
                    </strong>
                  </div>
                  <div>
                    <span>Base floor</span>
                    <strong
                      className={
                        selectedModel.selectedBaseFloorMet === null || selectedModel.selectedBaseFloorMet === undefined
                          ? ""
                          : selectedModel.selectedBaseFloorMet
                            ? "change-positive"
                            : "change-negative"
                      }
                    >
                      {selectedModel.selectedBaseFloorMet === null || selectedModel.selectedBaseFloorMet === undefined
                        ? "not recorded"
                        : selectedModel.selectedBaseFloorMet
                          ? "met"
                          : "missed"}
                    </strong>
                  </div>
                  <div>
                    <span>Signal threshold</span>
                    <strong>
                      {selectedModel.selectedThreshold !== null && selectedModel.selectedThreshold !== undefined ? selectedModel.selectedThreshold.toFixed(4) : "n/a"}
                      {selectedModel.selectedShortThreshold !== null && selectedModel.selectedShortThreshold !== undefined ? ` / ${selectedModel.selectedShortThreshold.toFixed(4)}` : ""}
                    </strong>
                  </div>
                  <div>
                    <span>Score margin</span>
                    <strong>
                      {selectedModel.selectedScoreMargin !== null && selectedModel.selectedScoreMargin !== undefined
                        ? selectedModel.selectedScoreMargin.toFixed(3)
                        : "n/a"}
                    </strong>
                  </div>
                  <div>
                    <span>Strategy side</span>
                    <strong>{selectedModel.strategySide ?? "long_only"}</strong>
                  </div>
                </div>
                {selectedModel.equityCurve.length ? (
                  <svg
                    className="showcase-equity-curve"
                    viewBox={`0 0 ${modelCurveGeometry(selectedModel.equityCurve).width} ${modelCurveGeometry(selectedModel.equityCurve).height}`}
                    role="img"
                    aria-label={`${selectedModel.name} showcase equity curve`}
                  >
                    <line
                      x1="0"
                      y1={modelCurveGeometry(selectedModel.equityCurve).baseline}
                      x2={modelCurveGeometry(selectedModel.equityCurve).width}
                      y2={modelCurveGeometry(selectedModel.equityCurve).baseline}
                    />
                    <path d={modelCurveGeometry(selectedModel.equityCurve).path} />
                  </svg>
                ) : null}
                <div className="split-return-strip" aria-label="Split return stability">
                  {selectedModel.splitReturns.map((value, index) => (
                    <div key={`${selectedModel.id}-split-return-${index}`}>
                      <span>Split {index + 1}</span>
                      <strong className={value >= 0 ? "change-positive" : "change-negative"}>
                        {formatPercent(value)}
                      </strong>
                    </div>
                  ))}
                </div>
                <div className="model-carousel-track" aria-label="Model carousel">
                  {showcaseModels.map((model, index) => (
                    <button
                      className={index === selectedModelIndex ? "model-slide-active" : ""}
                      key={model.id}
                      onClick={() => setSelectedModelIndex(index)}
                      type="button"
                    >
                      <span>{model.source}</span>
                      <strong>{model.name}</strong>
                      <em>{model.stabilityScore} stability</em>
                      <b className={model.totalReturnPct >= 0 ? "change-positive" : "change-negative"}>
                        {formatPercent(model.totalReturnPct)}
                      </b>
                    </button>
                  ))}
                </div>
                <div className="comparison-table" aria-label="Model comparison table">
                  <div className="comparison-row comparison-head">
                    <span>Model</span>
                    <span>Readiness</span>
                    <span>Stability</span>
                    <span>Sharpe</span>
                    <span>Win</span>
                    <span>Total</span>
                    <span>MDD</span>
                  </div>
                  {comparisonModels.map((model) => (
                    <div className="comparison-row" key={`compare-${model.id}`}>
                      <span>{model.name}</span>
                      <strong className={`readiness-pill readiness-pill-${model.readinessTone}`}>
                        {model.readinessLabel}
                      </strong>
                      <strong>{model.stabilityScore}</strong>
                      <strong>{model.sharpeRatio.toFixed(2)}</strong>
                      <strong>{model.winRatePct.toFixed(1)}%</strong>
                      <strong className={model.totalReturnPct >= 0 ? "change-positive" : "change-negative"}>
                        {formatPercent(model.totalReturnPct)}
                      </strong>
                      <strong className="change-negative">{model.maxDrawdownPct.toFixed(2)}%</strong>
                    </div>
                  ))}
                </div>
                <p className="model-seller-note">
                  Track record view only. Keep sales copy clear that model performance can decay and does not guarantee future returns.
                </p>
              </div>
            ) : null}
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
            <div className="kaggle-run-panel">
              <div className="kaggle-run-header">
                <div>
                  <h3>Kaggle GPU Volume Models</h3>
                  <p>
                    High-volume BTC candle regime models trained before the latest two-year backtest window.
                  </p>
                </div>
                {latestKaggleRun ? (
                  <strong className="status-ok">{latestKaggleRun.accelerator}</strong>
                ) : (
                  <strong className="status-muted">waiting</strong>
                )}
              </div>
              {latestKaggleRun ? (
                <>
                  <div className="kaggle-run-meta">
                    <span>Run {latestKaggleRun.run_id}</span>
                    <span>{latestKaggleRun.high_volume_rule}</span>
                    <span>Train {latestKaggleRun.training_window}</span>
                    <span>Backtest {latestKaggleRun.backtest_window}</span>
                    <span>Batch size {latestKaggleRun.batch_size}</span>
                  </div>
                  <div className="model-grid kaggle-model-grid" aria-label="Kaggle GPU model comparison">
                    {latestKaggleRun.models.slice(0, 10).map((model) => {
                      const curve = modelCurveGeometry(model.equity_curve);
                      const healthy = model.status === "ok";

                      return (
                        <article className="model-card" key={`${latestKaggleRun.run_id}-${model.name}`}>
                          <div className="model-card-header">
                            <div>
                              <h3>{model.name}</h3>
                              <span>{model.model_type}</span>
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
                              <span>Exposure</span>
                              <strong>{model.exposure_pct.toFixed(1)}%</strong>
                            </div>
                          </div>
                          {model.equity_curve.length ? (
                            <svg
                              className="model-equity-curve"
                              viewBox={`0 0 ${curve.width} ${curve.height}`}
                              role="img"
                              aria-label={`${model.name} Kaggle equity curve`}
                            >
                              <line x1="0" y1={curve.baseline} x2={curve.width} y2={curve.baseline} />
                              <path d={curve.path} />
                            </svg>
                          ) : null}
                          <div className="model-meta">
                            <span>{model.active_observations.toLocaleString()} active candles</span>
                            <span>{model.observations.toLocaleString()} observations</span>
                            <span>{model.trades.toLocaleString()} position changes</span>
                            <span className="change-negative">MDD {model.max_drawdown_pct.toFixed(2)}%</span>
                          </div>
                          <p>{model.message}</p>
                        </article>
                      );
                    })}
                  </div>
                  {topKaggleModel ? (
                    <div className="kaggle-analysis-grid" aria-label="Top Kaggle model diagnostics">
                      <div className="kaggle-analysis-block">
                        <h3>Top Model Drivers</h3>
                        <p>{topKaggleModel.name} feature importance</p>
                        <div className="importance-bars">
                          {topKaggleImportance.map((item) => (
                            <div className="importance-row" key={`${topKaggleModel.name}-${item.feature}`}>
                              <span>{item.feature}</span>
                              <div>
                                <i style={{ width: normalizedPercentWidth(item.importance, maxKaggleImportance) }} />
                              </div>
                              <strong>{(item.importance * 100).toFixed(1)}%</strong>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="kaggle-analysis-block">
                        <h3>Recent 2Y Four Splits</h3>
                        <div className="split-grid">
                          {topKaggleModel.split_metrics.map((split) => (
                            <article key={`${topKaggleModel.name}-split-${split.split}`}>
                              <span>Split {split.split}</span>
                              <strong>{split.sharpe_ratio.toFixed(2)} Sharpe</strong>
                              <em>{split.start} to {split.end}</em>
                              <div>
                                <span>{split.win_rate_pct.toFixed(1)}% win</span>
                                <span>{formatPercent(split.total_return_pct)}</span>
                                <span>{split.active_observations} active</span>
                              </div>
                            </article>
                          ))}
                        </div>
                      </div>
                      <div className="kaggle-analysis-block kaggle-correlation-block">
                        <h3>Split Feature Correlations</h3>
                        <p>Top drivers versus next-day BTC return inside each recent split.</p>
                        <div className="correlation-bars">
                          {topKaggleSplitCorrelations.map((item) => (
                            <div className="correlation-bar-row" key={`${item.model_name}-${item.split}-${item.feature}`}>
                              <span>S{item.split} {item.feature}</span>
                              <div>
                                <i
                                  className={item.correlation >= 0 ? "bar-positive" : "bar-negative"}
                                  style={{ width: normalizedPercentWidth(item.correlation, maxKaggleCorrelation) }}
                                />
                              </div>
                              <strong className={item.correlation >= 0 ? "change-positive" : "change-negative"}>
                                {item.correlation.toFixed(2)}
                              </strong>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="empty-state">
                  <strong>Kaggle run output has not been imported yet.</strong>
                  <p>
                    Push the GPU kernel, download its output folder, and place run_summary.json under backend/model_registry/kaggle_runs.
                  </p>
                </div>
              )}
            </div>
            <div className="model-instructions">
              {modelBacktests.instructions.map((instruction) => (
                <span key={instruction}>{instruction}</span>
              ))}
            </div>
            <p className="disclaimer">{modelBacktests.disclaimer}</p>
          </div>

          <div className="panel" hidden={activePage !== "news"}>
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

          <div className="panel" hidden={activePage !== "news"}>
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
