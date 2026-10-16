# Meter day charges

Three modules. `report` calls `tariffs`, which calls `units`. Fix the program so this contract holds. Do not special-case the numbers in the visible test.

- `units.c_to_f(celsius)` returns Fahrenheit: `celsius * 9/5 + 32`.
- `tariffs.degree_day_charge(celsius, rate)` converts with `c_to_f`. The charge is `rate` dollars for each degree Fahrenheit above 60. At or below 60F the charge is 0.
- `report.day_line(celsius, rate)` returns `{"temp_f": <fahrenheit>, "charge": <dollars>}`.
- `report.month_total(days)` takes a list of `(celsius, rate)` pairs and returns the sum of the degree-day charges.

Examples that the visible test does not cover: `c_to_f(-40) == -40`, `c_to_f(0) == 32`, `c_to_f(100) == 212`, `degree_day_charge(10, 2) == 0` (50F), `degree_day_charge(25, 1) == 17`.
