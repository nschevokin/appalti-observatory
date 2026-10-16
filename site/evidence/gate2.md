# Gate 2: comparability (ticket C2)
Run `35266f3e-G20261016T143459217263Z`, on indicators run `35266f3e-20261016T143024732152Z`.

Thresholds were fixed in `gate.toml` before any indicator was computed (D007, D038):
minimum populatedness 50.0%, maximum populatedness spread 20 points, volume ratio between 0.5 and 2.0, maximum composition drift 0.15.

**112 decisions: 42 passed, 70 refused.**

## Refusals by indicator and clock

| Indicator | Clock | Decisions | Refused |
|---|---|---|---|
| Awarded value | award year | 15 | 7 |
| Awarded value | tender start year | 13 | 7 |
| Single-bidder share | award year | 15 | 15 |
| Single-bidder share | tender start year | 13 | 13 |
| Supplier concentration | award year | 15 | 7 |
| Supplier concentration | tender start year | 13 | 7 |
| Procedure mix | award year | 15 | 7 |
| Procedure mix | tender start year | 13 | 7 |

## Volume ratio between consecutive years

| Clock | Pair | Records | Ratio | Within band |
|---|---|---|---|---|
| award year | 2018 to 2019 | 58,519 to 48,353 | 0.83 | yes |
| award year | 2019 to 2020 | 48,353 to 55,614 | 1.15 | yes |
| award year | 2020 to 2021 | 55,614 to 51,322 | 0.92 | yes |
| award year | 2021 to 2022 | 51,322 to 85,330 | 1.66 | yes |
| award year | 2022 to 2023 | 85,330 to 22,426 | 0.26 | no |
| award year | 2023 to 2024 | 22,426 to 664 | 0.03 | no |
| award year | 2024 to 2025 | 664 to 45 | 0.07 | no |
| tender start year | 2018 to 2019 | 63,862 to 55,102 | 0.86 | yes |
| tender start year | 2019 to 2020 | 55,102 to 47,566 | 0.86 | yes |
| tender start year | 2020 to 2021 | 47,566 to 52,792 | 1.11 | yes |
| tender start year | 2021 to 2022 | 52,792 to 87,658 | 1.66 | yes |
| tender start year | 2022 to 2023 | 87,658 to 15,993 | 0.18 | no |
| tender start year | 2023 to 2024 | 15,993 to 3 | 0.00 | no |

## Composition drift between consecutive years (CPV division mix)

| Clock | Pair | Drift | Within limit |
|---|---|---|---|
| award year | 2018 to 2019 | 0.064 | yes |
| award year | 2019 to 2020 | 0.100 | yes |
| award year | 2020 to 2021 | 0.161 | no |
| award year | 2021 to 2022 | 0.114 | yes |
| award year | 2022 to 2023 | 0.084 | yes |
| award year | 2023 to 2024 | 0.247 | no |
| award year | 2024 to 2025 | 0.260 | no |
| tender start year | 2018 to 2019 | 0.089 | yes |
| tender start year | 2019 to 2020 | 0.153 | no |
| tender start year | 2020 to 2021 | 0.197 | no |
| tender start year | 2021 to 2022 | 0.128 | yes |
| tender start year | 2022 to 2023 | 0.173 | no |
| tender start year | 2023 to 2024 | 0.934 | no |

## Every refusal, with its reason

- Awarded value, 2023 (award year): not published. No neighbouring year is comparable with 2023: the comparison with 2022 and 2024 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Awarded value, 2024 (award year): not published. No neighbouring year is comparable with 2024: the comparison with 2023 and 2025 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Awarded value, 2025 (award year): not published. No neighbouring year is comparable with 2025: the comparison with 2024 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Awarded value, 2020 compared with 2021 (award year): not published. The sector mix (CPV division) shifted by 0.161, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Awarded value, 2022 compared with 2023 (award year): not published. The 2023 record count is 0.26 of the 2022 count, outside the accepted band of 0.5 to 2.0. The two years are not comparable on this measure.
- Awarded value, 2023 compared with 2024 (award year): not published. The 2024 record count is 0.03 of the 2023 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.247, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Awarded value, 2024 compared with 2025 (award year): not published. The 2025 record count is 0.07 of the 2024 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.260, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Awarded value, 2020 (tender start year): not published. No neighbouring year is comparable with 2020: the comparison with 2019 and 2021 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Awarded value, 2023 (tender start year): not published. No neighbouring year is comparable with 2023: the comparison with 2022 and 2024 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Awarded value, 2024 (tender start year): not published. No neighbouring year is comparable with 2024: the comparison with 2023 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Awarded value, 2019 compared with 2020 (tender start year): not published. The sector mix (CPV division) shifted by 0.153, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Awarded value, 2020 compared with 2021 (tender start year): not published. The sector mix (CPV division) shifted by 0.197, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Awarded value, 2022 compared with 2023 (tender start year): not published. The 2023 record count is 0.18 of the 2022 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.173, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Awarded value, 2023 compared with 2024 (tender start year): not published. The 2024 record count is 0.00 of the 2023 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.934, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Single-bidder share, 2018 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2018 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2019 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2019 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2020 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2020 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2021 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2021 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2022 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2022 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2023 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2023 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2024 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2024 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2025 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2025 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2018 compared with 2019 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2018 records and 0.0% of 2019 records, below the minimum of 50.0%. The two years are not comparable on this measure.
- Single-bidder share, 2019 compared with 2020 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2019 records and 0.0% of 2020 records, below the minimum of 50.0%. The two years are not comparable on this measure.
- Single-bidder share, 2020 compared with 2021 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2020 records and 0.0% of 2021 records, below the minimum of 50.0%. The sector mix (CPV division) shifted by 0.161, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Single-bidder share, 2021 compared with 2022 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2021 records and 0.0% of 2022 records, below the minimum of 50.0%. The two years are not comparable on this measure.
- Single-bidder share, 2022 compared with 2023 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2022 records and 0.0% of 2023 records, below the minimum of 50.0%. The 2023 record count is 0.26 of the 2022 count, outside the accepted band of 0.5 to 2.0. The two years are not comparable on this measure.
- Single-bidder share, 2023 compared with 2024 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2023 records and 0.0% of 2024 records, below the minimum of 50.0%. The 2024 record count is 0.03 of the 2023 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.247, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Single-bidder share, 2024 compared with 2025 (award year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2024 records and 0.0% of 2025 records, below the minimum of 50.0%. The 2025 record count is 0.07 of the 2024 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.260, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Single-bidder share, 2018 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2018 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2019 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2019 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2020 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2020 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2021 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2021 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2022 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2022 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2023 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2023 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2024 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2024 records, below the minimum of 50.0%. The figure cannot be computed honestly for this year.
- Single-bidder share, 2018 compared with 2019 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2018 records and 0.0% of 2019 records, below the minimum of 50.0%. The two years are not comparable on this measure.
- Single-bidder share, 2019 compared with 2020 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2019 records and 0.0% of 2020 records, below the minimum of 50.0%. The sector mix (CPV division) shifted by 0.153, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Single-bidder share, 2020 compared with 2021 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2020 records and 0.0% of 2021 records, below the minimum of 50.0%. The sector mix (CPV division) shifted by 0.197, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Single-bidder share, 2021 compared with 2022 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2021 records and 0.0% of 2022 records, below the minimum of 50.0%. The two years are not comparable on this measure.
- Single-bidder share, 2022 compared with 2023 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2022 records and 0.0% of 2023 records, below the minimum of 50.0%. The 2023 record count is 0.18 of the 2022 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.173, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Single-bidder share, 2023 compared with 2024 (tender start year): not published. The required field (tender.numberOfTenderers) is populated in 0.0% of 2023 records and 0.0% of 2024 records, below the minimum of 50.0%. The 2024 record count is 0.00 of the 2023 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.934, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Supplier concentration, 2023 (award year): not published. No neighbouring year is comparable with 2023: the comparison with 2022 and 2024 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Supplier concentration, 2024 (award year): not published. No neighbouring year is comparable with 2024: the comparison with 2023 and 2025 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Supplier concentration, 2025 (award year): not published. No neighbouring year is comparable with 2025: the comparison with 2024 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Supplier concentration, 2020 compared with 2021 (award year): not published. The sector mix (CPV division) shifted by 0.161, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Supplier concentration, 2022 compared with 2023 (award year): not published. The 2023 record count is 0.26 of the 2022 count, outside the accepted band of 0.5 to 2.0. The two years are not comparable on this measure.
- Supplier concentration, 2023 compared with 2024 (award year): not published. The 2024 record count is 0.03 of the 2023 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.247, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Supplier concentration, 2024 compared with 2025 (award year): not published. The 2025 record count is 0.07 of the 2024 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.260, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Supplier concentration, 2020 (tender start year): not published. No neighbouring year is comparable with 2020: the comparison with 2019 and 2021 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Supplier concentration, 2023 (tender start year): not published. No neighbouring year is comparable with 2023: the comparison with 2022 and 2024 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Supplier concentration, 2024 (tender start year): not published. No neighbouring year is comparable with 2024: the comparison with 2023 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Supplier concentration, 2019 compared with 2020 (tender start year): not published. The sector mix (CPV division) shifted by 0.153, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Supplier concentration, 2020 compared with 2021 (tender start year): not published. The sector mix (CPV division) shifted by 0.197, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Supplier concentration, 2022 compared with 2023 (tender start year): not published. The 2023 record count is 0.18 of the 2022 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.173, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Supplier concentration, 2023 compared with 2024 (tender start year): not published. The 2024 record count is 0.00 of the 2023 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.934, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Procedure mix, 2023 (award year): not published. No neighbouring year is comparable with 2023: the comparison with 2022 and 2024 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Procedure mix, 2024 (award year): not published. No neighbouring year is comparable with 2024: the comparison with 2023 and 2025 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Procedure mix, 2025 (award year): not published. No neighbouring year is comparable with 2025: the comparison with 2024 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Procedure mix, 2020 compared with 2021 (award year): not published. The sector mix (CPV division) shifted by 0.161, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Procedure mix, 2022 compared with 2023 (award year): not published. The 2023 record count is 0.26 of the 2022 count, outside the accepted band of 0.5 to 2.0. The two years are not comparable on this measure.
- Procedure mix, 2023 compared with 2024 (award year): not published. The 2024 record count is 0.03 of the 2023 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.247, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Procedure mix, 2024 compared with 2025 (award year): not published. The 2025 record count is 0.07 of the 2024 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.260, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Procedure mix, 2020 (tender start year): not published. No neighbouring year is comparable with 2020: the comparison with 2019 and 2021 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Procedure mix, 2023 (tender start year): not published. No neighbouring year is comparable with 2023: the comparison with 2022 and 2024 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Procedure mix, 2024 (tender start year): not published. No neighbouring year is comparable with 2024: the comparison with 2023 was refused, so a single-year figure would stand alone as a level without context. A year with no comparable neighbour is not published (D040).
- Procedure mix, 2019 compared with 2020 (tender start year): not published. The sector mix (CPV division) shifted by 0.153, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Procedure mix, 2020 compared with 2021 (tender start year): not published. The sector mix (CPV division) shifted by 0.197, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Procedure mix, 2022 compared with 2023 (tender start year): not published. The 2023 record count is 0.18 of the 2022 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.173, above the accepted maximum of 0.15. The two years are not comparable on this measure.
- Procedure mix, 2023 compared with 2024 (tender start year): not published. The 2024 record count is 0.00 of the 2023 count, outside the accepted band of 0.5 to 2.0. The sector mix (CPV division) shifted by 0.934, above the accepted maximum of 0.15. The two years are not comparable on this measure.

## Clocks side by side (awarded value, headline)

| Period | Award year | Tender start year | Relative gap | Note |
|---|---|---|---|---|
| 2018 | 49.53 bn | 59.22 bn | 0.16 |  |
| 2019 | 35.78 bn | 45.10 bn | 0.21 |  |
| 2020 | 41.50 bn | 35.65 bn | 0.14 |  |
| 2021 | 34.64 bn | 35.22 bn | 0.02 |  |
| 2022 | 76.17 bn | 83.53 bn | 0.09 |  |
| 2023 | 26.56 bn | 10.66 bn | 0.60 | clocks differ by more than the informational limit |
| 2024 | 4.85 bn | 0.00 bn | 1.00 | clocks differ by more than the informational limit |
