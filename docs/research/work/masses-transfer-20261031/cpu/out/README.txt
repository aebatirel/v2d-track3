CPU outputs of the masses-transfer build (2026-10-31). Files named mock_* come from the CPU mock of the exact JOBS.txt
string (cpu/mock: stub trainer / evaluator / scorer with SYNTHETIC scores, +0.05 / +0.04 built in for the mass arm).
They test the plumbing (which files each arm trains and is evaluated on, the verification and the verdict code), NOT
the effect of masses. mock_check.json: 38 assertions (check.py); tests.json: negative and unit tests (tests.py);
equiv.txt: old vs new glock_public.sh / ckpt_curve.sh with the new hooks off (identical); eval_timeout_test.txt.
Paths: MR = the mock root (/content mapped to MR/content).
Review fixes (31 Oct ~06:30 UTC): mock_* and tests.json re-made after the fixes (tests.json: 17 tests, T8-T14 for the
fixes, each with "before_fix" = the same fixture on the 4e019af tools). timeout_mock_check.json / timeout_mock_*:
cpu/mock/run_timeout_mock.sh, the same job string with EVAL_TIMEOUT=4 and three injected evaluation stalls (one ignoring
SIGTERM): exit codes, timing, verify counts and the verdict line. equiv.txt re-made with the fixed scripts.
