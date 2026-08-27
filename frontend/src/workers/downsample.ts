export function downsample(values: unknown[], maxPoints = 800): unknown[] {
  if (!Array.isArray(values) || values.length <= maxPoints) return values;
  const step = Math.ceil(values.length / maxPoints);
  return values.filter((_, index) => index % step === 0);
}

self.onmessage = (event: MessageEvent<{ option: Record<string, any> }>) => {
  const option = event.data.option || {};
  const next = { ...option, series: (option.series || []).map((series: Record<string, any>) => ({
    ...series,
    data: downsample(series.data || []),
  })) };
  (self as unknown as Worker).postMessage(next);
};
