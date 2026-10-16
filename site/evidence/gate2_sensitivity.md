# Gate 2: threshold sensitivity

The thresholds in `gate.toml` were fixed before any indicator was computed and were not
changed after seeing the results. This page re-judges the same measurements under other
limits, in memory, to show how much the published result depends on them. It is a
disclosure, not a tuning step: nothing here is written to `gate_decision` and no limit
was moved because of it.

Baseline: minimum populatedness 0.5, maximum populatedness spread 0.2, volume ratio band 0.5 to 2.0, maximum composition drift 0.15. 112 judgements in the window 2018 to 2025.

## One limit at a time, then all together

The last two columns follow awarded value on the award year clock, the headline indicator.

| Scenario | Refused | Judgements that flip | Years shown | Years joined into a line |
|---|---|---|---|---|
| baseline (gate.toml) | 70 of 112 | 0 | 2018 to 2022 | 2018 to 2020, 2021 to 2022 |
| min populatedness 0.40 | 70 of 112 | 0 | 2018 to 2022 | 2018 to 2020, 2021 to 2022 |
| min populatedness 0.60 | 70 of 112 | 0 | 2018 to 2022 | 2018 to 2020, 2021 to 2022 |
| max populatedness spread 0.30 | 70 of 112 | 0 | 2018 to 2022 | 2018 to 2020, 2021 to 2022 |
| max populatedness spread 0.10 | 70 of 112 | 0 | 2018 to 2022 | 2018 to 2020, 2021 to 2022 |
| volume ratio band 0.33 to 3.0 | 70 of 112 | 0 | 2018 to 2022 | 2018 to 2020, 2021 to 2022 |
| volume ratio band 0.67 to 1.5 | 88 of 112 | 18 | 2018 to 2020 | 2018 to 2020 |
| max composition drift 0.10 | 88 of 112 | 18 | 2018 to 2020 | 2018 to 2020 |
| max composition drift 0.20 | 58 of 112 | 12 | 2018 to 2022 | 2018 to 2022 |
| max composition drift 0.25 | 58 of 112 | 12 | 2018 to 2022 | 2018 to 2022 |
| all lenient together | 58 of 112 | 12 | 2018 to 2022 | 2018 to 2022 |
| all strict together | 88 of 112 | 18 | 2018 to 2020 | 2018 to 2020 |

## What flips, for the headline indicator

- volume ratio band 0.67 to 1.5: 2021 compared with 2022 passed, now refused.
- max composition drift 0.10: 2021 compared with 2022 passed, now refused.
- max composition drift 0.20: 2020 compared with 2021 was refused, now passes.
- max composition drift 0.25: 2020 compared with 2021 was refused, now passes.
- all lenient together: 2020 compared with 2021 was refused, now passes.
- all strict together: 2021 compared with 2022 passed, now refused.

## Closest calls: pairs refused for exactly one measure

How far past its limit each single-cause refusal is, and what the limit would have to
be for the pair to pass. A small margin means the refusal depends on the exact limit.

| Indicator | Clock | Pair | Measure | Value | Limit | Past the limit by | Would need |
|---|---|---|---|---|---|---|---|
| Awarded value | tender start year | 2019 to 2020 | composition drift | 0.153 | 0.150 | 2% | drift limit of at least 0.153 |
| Supplier concentration | tender start year | 2019 to 2020 | composition drift | 0.153 | 0.150 | 2% | drift limit of at least 0.153 |
| Procedure mix | tender start year | 2019 to 2020 | composition drift | 0.153 | 0.150 | 2% | drift limit of at least 0.153 |
| Awarded value | award year | 2020 to 2021 | composition drift | 0.161 | 0.150 | 7% | drift limit of at least 0.161 |
| Supplier concentration | award year | 2020 to 2021 | composition drift | 0.161 | 0.150 | 7% | drift limit of at least 0.161 |
| Procedure mix | award year | 2020 to 2021 | composition drift | 0.161 | 0.150 | 7% | drift limit of at least 0.161 |
| Awarded value | tender start year | 2020 to 2021 | composition drift | 0.197 | 0.150 | 31% | drift limit of at least 0.197 |
| Supplier concentration | tender start year | 2020 to 2021 | composition drift | 0.197 | 0.150 | 31% | drift limit of at least 0.197 |
| Procedure mix | tender start year | 2020 to 2021 | composition drift | 0.197 | 0.150 | 31% | drift limit of at least 0.197 |
| Awarded value | award year | 2022 to 2023 | volume ratio | 0.263 | 0.500 | 90% | lower ratio bound of at most 0.26 |
| Supplier concentration | award year | 2022 to 2023 | volume ratio | 0.263 | 0.500 | 90% | lower ratio bound of at most 0.26 |
| Procedure mix | award year | 2022 to 2023 | volume ratio | 0.263 | 0.500 | 90% | lower ratio bound of at most 0.26 |

## Closest calls: pairs that passed

Drift and volume ratio of the passed pairs of the headline indicator, nearest to a limit.

| Clock | Pair | Drift | Drift limit | Volume ratio | Band |
|---|---|---|---|---|---|
| award year | 2021 to 2022 | 0.114 | 0.15 | 1.66 | 0.5 to 2.0 |
| award year | 2019 to 2020 | 0.100 | 0.15 | 1.15 | 0.5 to 2.0 |
| award year | 2018 to 2019 | 0.064 | 0.15 | 0.83 | 0.5 to 2.0 |
