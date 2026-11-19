## RoadSense evaluation (test)

| Metric | Value |
|---|---|
| map50 | 0.406 |
| map50_95 | 0.164 |
| precision | 0.499 |
| recall | 0.377 |

| Class | Precision | Recall | AP@50 | AP@50-95 |
|---|---|---|---|---|
| longitudinal_crack | 0.520 | 0.320 | 0.380 | 0.158 |
| transverse_crack | 0.164 | 0.143 | 0.096 | 0.042 |
| alligator_crack | 0.683 | 0.649 | 0.694 | 0.294 |
| pothole | 0.630 | 0.398 | 0.455 | 0.162 |

Error analysis at conf=0.25, IoU=0.5

| Slice | Recall | Instances |
|---|---|---|
| lighting: dark | 0.3799 | 179 |
| lighting: normal | 0.444 | 241 |
| lighting: bright | 0.4113 | 282 |
| size: small | 0.4286 | 35 |
| size: medium | 0.2867 | 286 |
| size: large | 0.5092 | 381 |
