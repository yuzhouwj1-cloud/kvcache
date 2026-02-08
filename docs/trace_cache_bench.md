# Trace Cache Hit-Rate Matrix

## FAST25-release/arxiv-trace/mooncake_trace.jsonl

Unique blocks (deduplicated): **183,166**
Timestamp throughput (tokens/s): **56,339.61**

Policies: **lru, hierarchical_lru**
| Policy | Cache fraction | Cache time (s) | Cache blocks | Cache capacity (GB) | Hit rate | Prefix block hit rate | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| lru | 25% | 416.14 | 45,791 | 1542.76 | 0.0108 | 0.5510 |  |
| lru | 50% | 832.28 | 91,583 | 3085.56 | 0.0108 | 0.5522 |  |
| lru | 75% | 1248.42 | 137,374 | 4628.32 | 0.0109 | 0.5525 |  |
| lru | 100% | 1664.57 | 183,166 | 6171.12 | 0.0109 | 0.5526 |  |
| hierarchical_lru | 25% | 416.14 | 45,791 | 1542.76 | 0.0107 | 0.5509 | L1 11,447 / L2 34,344 blocks |
| hierarchical_lru | 50% | 832.28 | 91,583 | 3085.56 | 0.0108 | 0.5520 | L1 22,895 / L2 68,688 blocks |
| hierarchical_lru | 75% | 1248.42 | 137,374 | 4628.32 | 0.0109 | 0.5524 | L1 34,343 / L2 103,031 blocks |
| hierarchical_lru | 100% | 1664.57 | 183,166 | 6171.12 | 0.0109 | 0.5526 | L1 45,791 / L2 137,375 blocks |

## FAST25-release/traces/conversation_trace.jsonl

Unique blocks (deduplicated): **182,790**
Timestamp throughput (tokens/s): **40,939.64**

Policies: **lru, hierarchical_lru**
| Policy | Cache fraction | Cache time (s) | Cache blocks | Cache capacity (GB) | Hit rate | Prefix block hit rate | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| lru | 25% | 571.50 | 45,697 | 1539.60 | 0.0097 | 0.3536 |  |
| lru | 50% | 1143.01 | 91,395 | 3079.23 | 0.0098 | 0.3634 |  |
| lru | 75% | 1714.50 | 137,092 | 4618.82 | 0.0098 | 0.3660 |  |
| lru | 100% | 2286.01 | 182,790 | 6158.45 | 0.0098 | 0.3664 |  |
| hierarchical_lru | 25% | 571.50 | 45,697 | 1539.60 | 0.0096 | 0.3490 | L1 11,424 / L2 34,273 blocks |
| hierarchical_lru | 50% | 1143.01 | 91,395 | 3079.23 | 0.0098 | 0.3610 | L1 22,848 / L2 68,547 blocks |
| hierarchical_lru | 75% | 1714.50 | 137,092 | 4618.82 | 0.0098 | 0.3644 | L1 34,273 / L2 102,819 blocks |
| hierarchical_lru | 100% | 2286.01 | 182,790 | 6158.45 | 0.0098 | 0.3662 | L1 45,697 / L2 137,093 blocks |

## FAST25-release/traces/toolagent_trace.jsonl

Unique blocks (deduplicated): **183,300**
Timestamp throughput (tokens/s): **57,385.11**

Policies: **lru, hierarchical_lru**
| Policy | Cache fraction | Cache time (s) | Cache blocks | Cache capacity (GB) | Hit rate | Prefix block hit rate | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| lru | 25% | 408.86 | 45,825 | 1543.91 | 0.0108 | 0.5510 |  |
| lru | 50% | 817.72 | 91,650 | 3087.82 | 0.0108 | 0.5522 |  |
| lru | 75% | 1226.58 | 137,475 | 4631.73 | 0.0109 | 0.5524 |  |
| lru | 100% | 1635.43 | 183,300 | 6175.63 | 0.0109 | 0.5525 |  |
| hierarchical_lru | 25% | 408.86 | 45,825 | 1543.91 | 0.0107 | 0.5508 | L1 11,456 / L2 34,369 blocks |
| hierarchical_lru | 50% | 817.72 | 91,650 | 3087.82 | 0.0108 | 0.5519 | L1 22,912 / L2 68,738 blocks |
| hierarchical_lru | 75% | 1226.58 | 137,475 | 4631.73 | 0.0109 | 0.5523 | L1 34,368 / L2 103,107 blocks |
| hierarchical_lru | 100% | 1635.43 | 183,300 | 6175.63 | 0.0109 | 0.5525 | L1 45,825 / L2 137,475 blocks |

## FAST25-release/traces/synthetic_trace.jsonl

Unique blocks (deduplicated): **43,924**
Timestamp throughput (tokens/s): **59,803.06**

Policies: **lru, hierarchical_lru**
| Policy | Cache fraction | Cache time (s) | Cache blocks | Cache capacity (GB) | Hit rate | Prefix block hit rate | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| lru | 25% | 94.01 | 10,981 | 369.97 | 0.0331 | 0.4487 |  |
| lru | 50% | 188.03 | 21,962 | 739.93 | 0.0468 | 0.5920 |  |
| lru | 75% | 282.04 | 32,943 | 1109.90 | 0.0521 | 0.6339 |  |
| lru | 100% | 376.05 | 43,924 | 1479.86 | 0.0533 | 0.6396 |  |
| hierarchical_lru | 25% | 94.01 | 10,981 | 369.97 | 0.0265 | 0.3968 | L1 2,745 / L2 8,236 blocks |
| hierarchical_lru | 50% | 188.03 | 21,962 | 739.93 | 0.0423 | 0.5403 | L1 5,490 / L2 16,472 blocks |
| hierarchical_lru | 75% | 282.04 | 32,943 | 1109.90 | 0.0496 | 0.6060 | L1 8,235 / L2 24,708 blocks |
| hierarchical_lru | 100% | 376.05 | 43,924 | 1479.86 | 0.0518 | 0.6292 | L1 10,981 / L2 32,943 blocks |

