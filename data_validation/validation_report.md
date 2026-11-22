# 2022 NextGen NHTS V2.1 local data validation

**Overall result: PASS**  
Generated (UTC): 2026-10-17T04:16:43.981531+00:00  
Validator version: 1.0.0

## Scope and evidence rule

The `Data` folder was checked for file readability, required files, table grain and keys, schema coverage, cross-table relationships, official control totals, codebook consistency, and citation content. The official FHWA/NHTS pages and the official User's Guide are the evidence basis.

`NHTS_2022_complete_data_dictionary.xlsx` was used only as an optional convenience cross-check. It did not supply any expected value and is excluded from the overall result.

## File inventory

| file | bytes | sha256 | read_status | rows_or_pages | columns_or_sheets |
| --- | --- | --- | --- | --- | --- |
| Citation.pdf | 49313 | a419325e1632fbf9d36ead1c6bf2b50841e00bbc43599012cea06dd364fdb956 | PASS | 1 | PDF pages |
| hhv2pub.csv | 1767471 | d459a63d9bf818f38ea4a222fc0ae038e78509011cba3233762abd39d785745b | PASS | 7893 | 43 |
| ldtv2pub.csv | 6418788 | 523da0b5778061e1c405d3c656c30184e1e366dc913fd369c135fa7ca29baad8 | PASS | 16997 | 74 |
| NHTS_2022_Codebook_V2.1.xlsx | 163714 | 7e10ff62be0a72b03528f2469e8da850b335b7d761cf6efdfe9eba9b8a513d96 | PASS | 2718 | Household \| Person \| Vehicle \| Trip \| Long Distance |
| NHTS_2022_Data_Dictionary_V2.1.xlsx | 29000 | 6bb6a6518224ef62d511494ea7882a5f533becc1301ac06483dd65dc042db073 | PASS | 275 | Dictionary |
| perv2pub.csv | 12473819 | fa4d816ccd4d1975ff8afd394ce50b1d2326fa2c0b07b8d7f36636ea670fd89c | PASS | 16997 | 153 |
| tripv2pub.csv | 17505566 | f821357ffbab035a4a6704f575cfd20cd7eb4d2f890bd69e1345776377a66c82 | PASS | 31074 | 102 |
| vehv2pub.csv | 4455967 | eb7bc61dde5f81d08b2437a053aff2eabe9575a6befbfed6bc9a36159c23b52a | PASS | 14684 | 55 |

## Official control totals

| metric | observed_cases | official_cases | observed_weighted_total | official_weighted_total | overall_status |
| --- | --- | --- | --- | --- | --- |
| Households | 7893 | 7893 | 127544707.0 | 127544707.0 | PASS |
| Persons | 16997 | 16997 | 305560925.0 | 305560925.0 | PASS |
| Personally Owned Vehicle | 14684 | 14684 | 232837104.147 | 232837104.0 | PASS |
| Trips (Annualized) | 31074 | 31074 | 253754536506.74 | 253754536507.0 | PASS |
| Workers | 7783 | 7783 | 158009510.325 | 158009510.0 | PASS |
| Drivers | 13434 | 13434 | 231803889.469 | 231803889.0 | PASS |
| Person Trips | 31074 | 31074 | 253754536506.74 | 253754536507.0 | PASS |
| Person Miles of Travel | 31060 | 31060 | 3184397491594.138 | 3184397491594.0 | PASS |
| Vehicle Trips | 20490 | 20490 | 160953195395.043 | 160953195395.0 | PASS |
| Vehicle Miles of Travel | 20487 | 20487 | 1848031458831.87 | 1848031458832.0 | PASS |

All weighted comparisons allow an absolute tolerance of 1 because the User's Guide publishes rounded whole-number totals.

## Cross-table relationships

| relationship | eligible_child_rows | orphan_rows | status | expected_link |
| --- | --- | --- | --- | --- |
| Person -> Household | 16997 | 0 | PASS | HOUSEID |
| Vehicle -> Household | 14684 | 0 | PASS | HOUSEID |
| Trip -> Household | 31074 | 0 | PASS | HOUSEID |
| Trip -> Person | 31074 | 0 | PASS | HOUSEID + PERSONID |
| Long Distance -> Person | 16997 | 0 | PASS | HOUSEID + PERSONID |
| Trip with positive VEHID -> Vehicle | 26307 | 0 | PASS | HOUSEID + VEHID |
| Person <-> Long Distance roster equality | 16997 | 0 | PASS | one Long Distance roster row for every person |

## Schema and codebook summary

- Schema failures: 0
- Table/key failures: 0
- Codebook variable-total failures: 0 across 427 documented variables
- Citation-content failures: 0
- Other combined failures: 0

## Government sources

- [FHWA NHTS overview](https://www.fhwa.dot.gov/policyinformation/nhts.cfm)
- [FHWA latest NextGen NHTS data](https://www.fhwa.dot.gov/policyinformation/nextgen-nhts-data.cfm)
- [NHTS 2022 downloads](https://nhts.ornl.gov/downloads)
- [NHTS 2022 documentation](https://nhts.ornl.gov/documentation)
- [NHTS 2022 FAQ](https://nhts.ornl.gov/faq)
- [NHTS 2022 User's Guide](https://nhts.ornl.gov/assets/2022/doc/2022%20NextGen%20NHTS%20User's%20Guide%20V201_PubUse.pdf)

The official User's Guide defines the core table grains and identifiers, explains the special negative codes, and publishes the control totals used above. The NHTS documentation page identifies the V2.1 codebook and data dictionary, while the downloads page identifies the V2.1 CSV release and recommended citation.

## Online reachability

| source | status | http_status | final_url | note |
| --- | --- | --- | --- | --- |
| FHWA NHTS overview | PASS | 200 | https://www.fhwa.dot.gov/policyinformation/nhts.cfm | Official source was reachable at validation time. |
| FHWA latest NextGen NHTS data | PASS | 200 | https://www.fhwa.dot.gov/policyinformation/nextgen-nhts-data.cfm | Official source was reachable at validation time. |
| NHTS 2022 downloads | PASS | 200 | https://nhts.ornl.gov/downloads | Official source was reachable at validation time. |
| NHTS 2022 documentation | PASS | 200 | https://nhts.ornl.gov/documentation | Official source was reachable at validation time. |
| NHTS 2022 FAQ | PASS | 200 | https://nhts.ornl.gov/faq | Official source was reachable at validation time. |
| NHTS 2022 User's Guide | PASS | 200 | https://nhts.ornl.gov/assets/2022/doc/2022%20NextGen%20NHTS%20User's%20Guide%20V201_PubUse.pdf | Official source was reachable at validation time. |

A reachability warning means the network check failed or was not run; it does not invalidate locally reproduced data checks.

## Reference-only comparison (not evidence)

| status | test | observed | expected | evidence_role |
| --- | --- | --- | --- | --- |
| PASS | reference field-occurrence row count | 427 | 427 | NONE — excluded from validation result |
| PASS | reference table-field pairs match local CSVs | 427 | 427 | NONE — excluded from validation result |

## Interpretation

The folder is internally consistent and reproduces the official published NHTS control totals. It is suitable as the source data for the proposal-stage exploratory analysis. This audit establishes file integrity and release consistency; it does not by itself establish that any later analytical sample, recoding, model, or causal interpretation is valid.
