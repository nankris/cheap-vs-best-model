# Per-line tax

Amounts and the rate are decimal strings. Use `decimal.Decimal`. Do not use binary floats.

- `tax.line_tax(amount, rate)` returns the tax as a two-place string. Multiply, then quantize to cents with `ROUND_HALF_EVEN`.
- `invoice.total_tax(amounts, rate)` sums the already-rounded line taxes and returns that sum as a two-place string. Rounding each line and rounding the sum are different. The contract is per line, then sum.
- An empty list totals `"0.00"`. A non-decimal string raises `ValueError`.

`total_tax(["1.005", "1.005"], "1")` is `"2.00"` because each line is `1.00`. It is not `"2.01"`.
`line_tax("1.225", "1")` is `"1.22"`. `line_tax("1.275", "1")` is `"1.28"`. `line_tax("0.005", "1")` is `"0.00"`.
`total_tax(["10.00"], "0.1225")` is `"1.22"`.

The visible test only checks the two `1.005` lines.
