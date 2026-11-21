#!/usr/bin/env bash
set -eu
# From repository root, with fresh output filenames (existing files are protected).
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261115 --output results/ilp-baseline-20261115/agreement-20261115.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261116 --output results/ilp-baseline-20261115/agreement-20261116.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261117 --output results/ilp-baseline-20261115/agreement-20261117.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261118 --output results/ilp-baseline-20261115/agreement-20261118.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261119 --output results/ilp-baseline-20261115/agreement-20261119.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261120 --output results/ilp-baseline-20261115/agreement-20261120.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261115 --output results/ilp-baseline-20261115/agreement-current-20261115.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261116 --output results/ilp-baseline-20261115/agreement-current-20261116.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261117 --output results/ilp-baseline-20261115/agreement-current-20261117.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261118 --output results/ilp-baseline-20261115/agreement-current-20261118.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261119 --output results/ilp-baseline-20261115/agreement-current-20261119.jsonl
bash results/ilp-baseline-20261115/run.sh agreement --count 500 --seed 20261120 --output results/ilp-baseline-20261115/agreement-current-20261120.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 0 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i0-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 0 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i0-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 0 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i0-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 0 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i0-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 1 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i1-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 1 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i1-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 1 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i1-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 1 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i1-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 2 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i2-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 2 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i2-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 2 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i2-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 1000 --index 2 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m1000-i2-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 0 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i0-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 0 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i0-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 0 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i0-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 0 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i0-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 1 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i1-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 1 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i1-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 1 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i1-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 1 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i1-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 2 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i2-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 2 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i2-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 2 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i2-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 200 --index 2 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m200-i2-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 0 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i0-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 0 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i0-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 0 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i0-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 0 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i0-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 1 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i1-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 1 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i1-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 1 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i1-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 1 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i1-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 2 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i2-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 2 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i2-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 2 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i2-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family dense --m 50 --index 2 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/dense-m50-i2-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 100 --output results/ilp-baseline-20261115/shortage-e100.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 12 --output results/ilp-baseline-20261115/shortage-e12.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 16 --output results/ilp-baseline-20261115/shortage-e16.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 2 --output results/ilp-baseline-20261115/shortage-e2.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 20 --output results/ilp-baseline-20261115/shortage-e20.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 200 --output results/ilp-baseline-20261115/shortage-e200.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 30 --output results/ilp-baseline-20261115/shortage-e30.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 4 --output results/ilp-baseline-20261115/shortage-e4.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 50 --output results/ilp-baseline-20261115/shortage-e50.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family shortage --e 8 --output results/ilp-baseline-20261115/shortage-e8.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 0 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i0-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 0 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i0-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 0 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i0-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 0 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i0-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 1 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i1-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 1 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i1-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 1 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i1-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 1 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i1-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 2 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i2-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 2 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i2-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 2 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i2-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 1000 --index 2 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m1000-i2-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 0 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i0-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 0 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i0-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 0 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i0-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 0 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i0-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 1 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i1-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 1 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i1-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 1 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i1-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 1 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i1-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 2 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i2-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 2 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i2-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 2 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i2-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 200 --index 2 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m200-i2-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 0 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i0-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 0 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i0-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 0 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i0-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 0 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i0-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 1 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i1-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 1 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i1-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 1 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i1-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 1 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i1-FREE-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 2 --variant FIX-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i2-FIX-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 2 --variant FIX-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i2-FIX-yes.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 2 --variant FREE-cut --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i2-FREE-cut.jsonl
bash results/ilp-baseline-20261115/run.sh bench --family sparse --m 50 --index 2 --variant FREE-yes --seed 20261113 --output results/ilp-baseline-20261115/sparse-m50-i2-FREE-yes.jsonl
