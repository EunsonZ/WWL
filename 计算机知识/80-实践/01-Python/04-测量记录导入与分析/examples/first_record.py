"""Finite synthetic input only; arbitrary external CSV uses core.read_records."""
from fractions import Fraction

records = [("a", 0, 2), ("b", 1000, 4), ("c", 2000, 6), ("d", 3000, 8)]
codes = [record[2] for record in records]
count = len(codes)
total = sum(codes)
mean = Fraction(total, count)
centered = sum((Fraction(code) - mean) ** 2 for code in codes)
print("n =", count)
print("sum_mV =", total)
print("mean_mV =", mean)
print("pvariance_mV2 =", centered / count)
print("variance_mV2 =", centered / (count - 1))
print("rms2_mV2 =", Fraction(sum(code * code for code in codes), count))
