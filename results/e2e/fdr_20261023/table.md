**ep12**

| variant | change | seed | n | registered AUC | sim_vs_ref | Δ AUC mean vs base |
|---|---|---|---|---|---|---|
| mc | base (published policy) | 42 | 6 | 0.725 ± 0.067 (0.581–0.777) | 0.729 ± 0.074 (0.568–0.789) |  |
| mck-s42 | contact retargeting | 42 | 6 | 0.790 ± 0.023 (0.744–0.817) | 0.791 ± 0.015 (0.759–0.807) | +0.066 |
| mckd-s42 | retargeting + FDR rewards (object points, fingertip bound) | 42 | 6 | 0.891 ± 0.015 (0.866–0.915) | 0.905 ± 0.009 (0.891–0.914) | +0.167 |
| mckd-s43 | retargeting + FDR rewards (object points, fingertip bound) | 43 | 6 | 0.762 ± 0.077 (0.638–0.839) | 0.774 ± 0.097 (0.625–0.861) | +0.037 |

**ep18**

| variant | change | seed | n | registered AUC | sim_vs_ref | Δ AUC mean vs base |
|---|---|---|---|---|---|---|
| mckfi-s42 | kri + flattened sweeper base (library_v3) | 42 | 6 | 0.715 ± 0.240 (0.179–0.842) | 0.733 ± 0.247 (0.182–0.860) |  |
| mckfid-s42 | kfi + FDR rewards (object points, fingertip bound) | 42 | 6 | 0.776 ± 0.229 (0.265–0.891) | 0.791 ± 0.246 (0.240–0.910) |  |
| mckfid-s43 | kfi + FDR rewards (object points, fingertip bound) | 43 | 6 | 0.889 ± 0.011 (0.868–0.902) | 0.922 ± 0.015 (0.891–0.935) |  |


