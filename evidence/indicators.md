# Indicators (ticket C1)
Run `35266f3e-20261016T143024732152Z`, input `full.jsonl.gz`, sha256 `35266f3e1a5bfe5680207dd85ad18ad55858c9a2e8b7dc66447c94d5313ab720`.

Every row carries its **n** (awards behind the figure) and, where a field can be absent,
its populatedness. These are measurements: whether two years may be compared is decided
by Gate 2 (`evidence/gate2.md`). Figures are awarded (not spent) euro; threshold 40,000
euro, so below-threshold contracts are absent. No entity is named anywhere.

Window 2018 to 2025. Awards outside it, or without a year, are not in any figure: 703 of 322,976 on the award-year clock, 0 on the tender-start-year clock.

## Awarded value, award year clock (billion EUR)

| Period | Awards | Populated | Headline | All awards | Flagged (D025) | Flagged awards |
|---|---|---|---|---|---|---|
| 2018 | 58,519 | 100.0% | 49.53 | 51.47 | 1.94 | 23 |
| 2019 | 48,353 | 100.0% | 35.78 | 35.88 | 0.10 | 6 |
| 2020 | 55,614 | 100.0% | 41.50 | 50.06 | 8.55 | 72 |
| 2021 | 51,322 | 100.0% | 34.64 | 38.42 | 3.78 | 51 |
| 2022 | 85,330 | 100.0% | 76.17 | 121.61 | 45.44 | 20 |
| 2023 | 22,426 | 100.0% | 26.56 | 54.56 | 28.00 | 48 |
| 2024 | 664 | 100.0% | 4.85 | 4.85 | n/a | 0 |
| 2025 | 45 | 100.0% | 0.04 | 0.04 | n/a | 0 |

## Awarded value, tender year clock (billion EUR)

| Period | Awards | Populated | Headline | All awards | Flagged (D025) | Flagged awards |
|---|---|---|---|---|---|---|
| 2018 | 63,862 | 100.0% | 59.22 | 63.43 | 4.21 | 29 |
| 2019 | 55,102 | 99.9% | 45.10 | 50.33 | 5.23 | 80 |
| 2020 | 47,566 | 99.9% | 35.65 | 39.21 | 3.56 | 29 |
| 2021 | 52,792 | 99.9% | 35.22 | 62.47 | 27.25 | 17 |
| 2022 | 87,658 | 100.0% | 83.53 | 129.99 | 46.46 | 59 |
| 2023 | 15,993 | 99.9% | 10.66 | 11.77 | 1.10 | 7 |
| 2024 | 3 | 100.0% | 0.00 | 0.00 | n/a | 0 |

## Supplier concentration (top five), award year clock

Share of the year's headline awarded value that went to the five largest suppliers.
`Point` treats every identifier as one entity; `upper` also merges ids that share a
legal-form name, so the truth lies between them (D036: split rate about 7%, wide interval).

| Period | Awards used | Populated | Point | Upper |
|---|---|---|---|---|
| 2018 | 58,373 | 99.9% | 12.8% | 12.8% |
| 2019 | 48,156 | 99.7% | 10.0% | 10.0% |
| 2020 | 55,354 | 99.7% | 7.8% | 8.2% |
| 2021 | 51,117 | 99.8% | 10.1% | 10.2% |
| 2022 | 84,763 | 99.4% | 13.7% | 13.7% |
| 2023 | 22,327 | 99.9% | 12.3% | 12.3% |
| 2024 | 658 | 99.2% | 51.0% | 51.0% |
| 2025 | 43 | 95.6% | 56.5% | 56.5% |

## Supplier concentration (top five), tender year clock

Share of the year's headline awarded value that went to the five largest suppliers.
`Point` treats every identifier as one entity; `upper` also merges ids that share a
legal-form name, so the truth lies between them (D036: split rate about 7%, wide interval).

| Period | Awards used | Populated | Point | Upper |
|---|---|---|---|---|
| 2018 | 63,685 | 99.9% | 11.0% | 11.0% |
| 2019 | 54,776 | 99.6% | 8.9% | 8.9% |
| 2020 | 47,376 | 99.8% | 11.0% | 11.4% |
| 2021 | 52,605 | 99.8% | 7.7% | 7.8% |
| 2022 | 87,030 | 99.4% | 13.1% | 13.1% |
| 2023 | 15,946 | 99.8% | 22.1% | 22.1% |
| 2024 | 3 | 100.0% | 87.1% | 87.1% |

## Procedure mix, share of awarded value, award year clock

| Period | Populated | below_threshold | direct_award | framework_call_off | negotiated_with_notice | negotiated_without_notice | open_or_restricted | other |
|---|---|---|---|---|---|---|---|---|
| 2018 | 100.0% | 0.9% | 2.2% | 46.3% | 7.4% | 15.7% | 25.9% | 1.6% |
| 2019 | 100.0% | 3.5% | 2.7% | 27.7% | 7.2% | 13.6% | 44.3% | 1.1% |
| 2020 | 100.0% | 5.3% | 2.7% | 19.8% | 6.4% | 15.4% | 50.4% | 0.1% |
| 2021 | 100.0% | 5.3% | 5.5% | 24.8% | 2.9% | 8.9% | 52.6% | 0.0% |
| 2022 | 100.0% | 4.4% | 4.1% | 29.9% | 4.4% | 12.8% | 44.3% | 0.1% |
| 2023 | 100.0% | 4.4% | 8.5% | 10.3% | 13.9% | 7.8% | 55.1% | 0.0% |
| 2024 | 100.0% | 0.9% | 1.1% | 0.3% | 11.5% | 13.1% | 73.0% | 0.0% |
| 2025 | 100.0% | 13.4% | 0.7% | 1.6% | n/a | 1.0% | 83.3% | n/a |

## Procedure mix, share of awarded value, tender year clock

| Period | Populated | below_threshold | direct_award | framework_call_off | negotiated_with_notice | negotiated_without_notice | open_or_restricted | other |
|---|---|---|---|---|---|---|---|---|
| 2018 | 100.0% | 0.8% | 1.9% | 38.8% | 9.0% | 14.1% | 33.9% | 1.5% |
| 2019 | 100.0% | 4.0% | 2.4% | 22.0% | 4.9% | 12.9% | 53.1% | 0.7% |
| 2020 | 100.0% | 4.5% | 2.8% | 22.9% | 5.7% | 14.3% | 49.7% | 0.0% |
| 2021 | 100.0% | 6.0% | 5.5% | 24.6% | 2.6% | 9.0% | 52.3% | 0.0% |
| 2022 | 100.0% | 4.1% | 4.0% | 27.3% | 7.7% | 13.1% | 43.8% | 0.0% |
| 2023 | 100.0% | 8.0% | 20.1% | 25.1% | 5.3% | 11.7% | 29.8% | 0.1% |
| 2024 | 100.0% | n/a | 100.0% | n/a | n/a | n/a | n/a | n/a |

## Single-bidder share

| Clock | Period | Awards with a tenderer count | Of all awards | Value |
|---|---|---|---|---|
| award_year | 2018 | 0 | 0.0% | n/a |
| award_year | 2019 | 0 | 0.0% | n/a |
| award_year | 2020 | 0 | 0.0% | n/a |
| award_year | 2021 | 0 | 0.0% | n/a |
| award_year | 2022 | 0 | 0.0% | n/a |
| award_year | 2023 | 0 | 0.0% | n/a |
| award_year | 2024 | 0 | 0.0% | n/a |
| award_year | 2025 | 0 | 0.0% | n/a |
| tender_year | 2018 | 0 | 0.0% | n/a |
| tender_year | 2019 | 0 | 0.0% | n/a |
| tender_year | 2020 | 0 | 0.0% | n/a |
| tender_year | 2021 | 0 | 0.0% | n/a |
| tender_year | 2022 | 0 | 0.0% | n/a |
| tender_year | 2023 | 0 | 0.0% | n/a |
| tender_year | 2024 | 0 | 0.0% | n/a |

A value of n/a means the field is empty and the share cannot be computed (D016).
