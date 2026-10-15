function mean(values: readonly number[]): number | undefined {
  if (values.length === 0) return undefined;
  let total = 0;
  for (const value of values) {
    if (!Number.isFinite(value)) throw new Error("需要有限数字");
    total += value;
  }
  return total / values.length;
}

function parseFiniteNumbers(value: unknown): readonly number[] {
  if (!Array.isArray(value)) throw new Error("需要数组");
  const items: readonly unknown[] = value;
  const numbers: number[] = [];
  for (const item of items) {
    if (typeof item !== "number" || !Number.isFinite(item)) {
      throw new Error("每项都需要有限数字");
    }
    numbers.push(item);
  }
  return numbers;
}

const jsonText = '[2, 4, 6, 8]';
try {
  const externalValue: unknown = JSON.parse(jsonText);
  const values = parseFiniteNumbers(externalValue);
  const result = mean(values);
  console.log(result === undefined ? "没有平均值" : `平均值 = ${result}`);
} catch (error: unknown) {
  console.log(error instanceof Error ? `输入被拒绝：${error.message}` : "输入被拒绝");
}
