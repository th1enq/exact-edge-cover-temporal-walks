#!/usr/bin/env bash
# Tải dữ liệu giao thông của Kujala et al. 2018 (Zenodo, record 1186215, bản 1.2) và chỉ giữ
# network_temporal_day.csv của mỗi thành phố, tại data/raw/transit/<city>/.
# Cách dùng: bash fetch_transit.sh [city ...]   (mặc định: turku grenoble adelaide kuopio)
set -euo pipefail

record=1186215
dest="$(cd "$(dirname "$0")/.." && pwd)/data/raw/transit"
cities=("$@")
[ ${#cities[@]} -eq 0 ] && cities=(turku grenoble adelaide kuopio)
mkdir -p "$dest"

echo "Lấy danh sách file của record $record ..."
curl -fsSL --retry 3 "https://zenodo.org/api/records/$record" -o "$dest/record-$record.json"

for city in "${cities[@]}"; do
  dir="$dest/$city"
  if [ -s "$dir/network_temporal_day.csv" ]; then
    echo "$city: đã có, bỏ qua"; continue
  fi
  url=$(python3 -I - "$dest/record-$record.json" "$city" <<'EOF'
import json, sys
files = json.load(open(sys.argv[1]))["files"]
want = sys.argv[2].lower() + ".zip"
for f in files:
    if f["key"].lower() == want:
        print(f["links"]["self"]); break
else:
    sys.exit("không thấy " + want + "; các file có: " + ", ".join(f["key"] for f in files))
EOF
)
  mkdir -p "$dir"
  echo "$city: tải $url"
  curl -fL --retry 3 -C - "$url" -o "$dir/$city.zip"
  python3 -I - "$dir/$city.zip" "$dir/network_temporal_day.csv" <<'EOF'
import shutil, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    names = [n for n in z.namelist() if n.endswith("network_temporal_day.csv")]
    if len(names) != 1:
        sys.exit("cần đúng một network_temporal_day.csv, thấy: %s" % names)
    with z.open(names[0]) as src, open(sys.argv[2], "wb") as dst:
        shutil.copyfileobj(src, dst)
EOF
  rm -f "$dir/$city.zip"
  echo "$city: $(wc -l < "$dir/network_temporal_day.csv") dòng"
done
echo "Xong: $dest"
