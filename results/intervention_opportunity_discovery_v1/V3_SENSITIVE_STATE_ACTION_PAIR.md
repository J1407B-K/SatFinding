# V3 sensitive-state action pair — exploratory only

State `T10_S3_B488045`. Same sealed canonical logical/heuristic state; two frozen actions. The sealed v3 conclusion B is unchanged.

HIGH action #5633: -21.810436% remaining ops. NON-HIGH action #2544: 0.000000%.

| Frozen relational field | HIGH | same-state NON-HIGH | Equal? |
|---|---|---|---|
| action_rank | 2 | 1 | False |
| action_id | 5633 | 2544 | False |
| clause_id | 5633 | 2544 | False |
| clause | [27, 432, 203, 495, 473, 431] | [430, 432, 431] | False |
| clause_length | 6 | 3 | False |
| source | "learned" | "original" | False |
| implied_literal | 27 | 430 | False |
| implied_var | 27 | 430 | False |
| antecedent_trail_positions | [80, 40, 41, 55, 13] | [80, 13] | False |
| antecedent_min_trail_pos | 13 | 13 | True |
| antecedent_max_trail_pos | 80 | 80 | True |
| antecedent_mean_trail_pos | 45.8 | 46.5 | False |
| newest_antecedent_age | 0 | 0 | True |
| pending_antecedent_count | 1 | 1 | True |
| pending_antecedent_fraction | 0.2 | 0.5 | False |
| newest_antecedent_relative_to_qhead | 0 | 0 | True |
| all_antecedents_processed | false | false | True |
| implied_var_activity_hex | "0x1.067b92700018ep+35" | "0x1.c1d86157911a2p+33" | False |
| implied_var_activity | 35229832064.00304 | 15094301359.13361 | False |
| implied_var_activity_rank | 5.0 | 96.0 | False |
| implied_var_heap_rank | 3 | 79 | False |
| implied_var_in_heap | true | true | True |
| same_implied_literal_multiplicity | 1 | 1 | True |
| distinct_implied_literal_count | 2 | 2 | True |
| has_competing_implied_literals | true | true | True |
| max_variable_overlap | 2 | 2 | True |
| mean_variable_overlap | 2 | 2 | True |
| max_jaccard | 0.2857142857142857 | 0.2857142857142857 | True |
| mean_jaccard | 0.2857142857142857 | 0.2857142857142857 | True |
| watched_literals | [27, 432] | [430, 432] | False |
| watched_literal_trail_positions | [null, 80] | [null, 80] | True |
| watched_false_pending_count | 1 | 1 | True |
| partial_historical_snapshot | false | false | True |

Both actions share exactly the same queue head and newest antecedent frontier. Their clauses differ in length/source, older antecedents and implied variable activity/heap position. These differences are observed contrasts, not identified causes. The natural pending/frontier booleans cannot distinguish this HIGH/NON-HIGH pair. No continuous-value cutoff or action-selection rule was fitted.
