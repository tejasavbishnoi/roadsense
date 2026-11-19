## RoadSense evaluation (test)

| Metric | Value |
|---|---|
| map50 | 0.423 |
| map50_95 | 0.188 |
| precision | 0.572 |
| recall | 0.377 |

| Class | Precision | Recall | AP@50 | AP@50-95 |
|---|---|---|---|---|
| longitudinal_crack | 0.536 | 0.320 | 0.349 | 0.168 |
| transverse_crack | 0.411 | 0.143 | 0.156 | 0.062 |
| alligator_crack | 0.722 | 0.646 | 0.720 | 0.343 |
| pothole | 0.617 | 0.397 | 0.468 | 0.177 |

Error analysis at conf=0.25, IoU=0.5

| Slice | Recall | Instances |
|---|---|---|
| lighting: dark | 0.3799 | 179 |
| lighting: normal | 0.5394 | 241 |
| lighting: bright | 0.461 | 282 |
| size: small | 0.4286 | 35 |
| size: medium | 0.3566 | 286 |
| size: large | 0.5538 | 381 |
