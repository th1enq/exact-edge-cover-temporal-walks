#!/usr/bin/env bash
# Chạy transit_full.py (chỉ thuật toán đường tăng, không nhánh-cận) cho mọi thành phố đã tải
# trong data/raw/transit/, cả FIX và FREE.  Bỏ qua cặp (thành phố, bài toán) đã có kết quả.
# Toàn bộ lần gọi dừng sau BUDGET giây (mặc định 290) để không vượt 5 phút; gọi lại để chạy tiếp.
# Cách dùng: [WINDOW=3 OUT=...] bash run_transit_cities.sh [city ...]  (mặc định: mọi thành phố đã tải)
# WINDOW=H: chỉ khung H giờ đông chuyến nhất (cho thành phố quá lớn); nên đặt OUT riêng.
set -uo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
out="${OUT:-$root/results/transit-more-20261025}"
budget="${BUDGET:-290}"
jobs="${JOBS:-3}"
mkdir -p "$out"
cd "$root"

cities=("$@")
if [ ${#cities[@]} -eq 0 ]; then
  for f in data/raw/transit/*/network_temporal_day.csv; do
    cities+=("$(basename "$(dirname "$f")")")
  done
fi

list=""
for c in "${cities[@]}"; do
  for p in fix free; do
    [ -s "$out/$c-$p.json" ] || list+="$c $p"$'\n'
  done
done
[ -z "$list" ] && { echo "không còn việc"; exit 0; }

start=$(date +%s)
printf '%s' "$list" | timeout "$budget" xargs -P "$jobs" -L 1 sh -c '
  left=$(( '"$start"' + '"$budget"' - 5 - $(date +%s) ))
  [ "$left" -gt 10 ] || { echo "hết giờ, chưa chạy: $0 $1"; exit 0; }
  timeout "$left" python3 experiments/transit_full.py data/raw/transit/$0/network_temporal_day.csv \
    --problem $1 --branch-seconds 0 ${WINDOW:+--window-hours $WINDOW} --output '"$out"'/$0-$1.json > /dev/null 2> '"$out"'/$0-$1.err \
    || echo "chưa xong hoặc lỗi: $0 $1"'
find "$out" -maxdepth 1 -name '*.err' -empty -delete
echo "thời gian: $(( $(date +%s) - start )) s"
