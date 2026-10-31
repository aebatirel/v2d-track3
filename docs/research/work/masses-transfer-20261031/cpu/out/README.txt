CPU outputs of the masses-transfer build (2026-10-31). Files named mock_* come from the CPU mock of the exact JOBS.txt
string (cpu/mock: stub trainer / evaluator / scorer with SYNTHETIC scores, +0.05 / +0.04 built in for the mass arm).
They test the plumbing (which files each arm trains and is evaluated on, the verification and the verdict code), NOT
the effect of masses. mock_check.json: 38 assertions (check.py); tests.json: negative and unit tests (tests.py);
equiv.txt: old vs new glock_public.sh / ckpt_curve.sh with the new hooks off (identical); eval_timeout_test.txt.
Paths: MR = the mock root (/content mapped to MR/content).
