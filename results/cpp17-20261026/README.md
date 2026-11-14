# Kiểm chứng bản C++17

Phạm vi: NS-FIX và NS-FREE, cạnh song song, thời điểm không giảm, walk rỗng;
đặc tả tham chiếu là `nscover/`. Bản cài đặt và hướng dẫn:
[`../../cpp/README.md`](../../cpp/README.md).

## Kết quả kiểm chứng lõi

| Kiểm tra | Số instance / kiểm tra | Kết quả |
|---|---:|---|
| Vét cạn: mọi đa tập <=4 cạnh trên 3 đỉnh, 2 thời điểm, start trong `{0,1,2}^3`, FREE và mọi end cùng tổng | 68.040 | PASS |
| Ngẫu nhiên nhỏ, CTest seed 1 và seed 11, 31, 97; đối chiếu backtracking độc lập | 310.000 | PASS |
| Ngẫu nhiên lớn hơn, CTest seed 2 và seed 23, 43, 101; đối chiếu nhánh-cận | 310.000 | PASS |
| Python–C++, cả hai backend C++, ca nhỏ và lớn hơn | 8.000 | PASS |
| CLI: JSON, batch, witness, lỗi input, giới hạn và trạng thái LIMIT | 25 | PASS |
| Public header biên dịch riêng với C++17 và `-Werror` | 8 | PASS |
| Release CTest | 4 nhóm | PASS |
| ASan + UBSan + LeakSanitizer, chạy ngoài sandbox | 4 nhóm | PASS |

Như vậy **378.040 instance nhỏ** trong bộ C++ được kiểm tra bằng backtracking
theo định nghĩa, ngoài các ca đơn vị và 4.000 instance nhỏ đối chiếu Python.
Số liệu là số lượt kiểm tra; không khẳng định mọi đồ thị giữa các lượt đều khác nhau.
Ca lớn có tối đa 120 cạnh trong bộ ngẫu nhiên. Không có ca nhánh-cận LIMIT trong
các lượt release ngẫu nhiên đã ghi. `seeds-*.jsonl` lưu thống kê từng seed.

Mỗi instance trong bộ C++ được chạy pair-flow với hai backend mạng chuỗi
(`greedy`, `dinic`) và nhánh-cận. Mọi YES dựng walk và kiểm tra theo input gốc.
Oracle backtracking chỉ thử cạnh chưa dùng, chiều di chuyển và số token hiện tại;
nó không gọi orientation, timeline hay max-flow. Các bộ ngẫu nhiên yêu cầu thực sự
gặp nhánh tăng thành công, nhánh không có đường tăng, D>=2 và NO sau một số bước tăng.
Các bộ lớn đạt D tới 19 và tới 17 bước tăng; xem từng dòng kết quả để biết seed.

Đối chiếu Python còn kiểm tra walk C++ xuất ra bằng `check_walks` của Python,
và dựng lại witness bằng Python từ orientation C++. Ca nhỏ dùng thêm cả oracle
Python và oracle C++; ca lớn dùng các bộ pair-flow/nhánh-cận của hai ngôn ngữ.

Ca đơn vị bao gồm phản ví dụ AAAI, equal-time path, đồ thị rỗng, không có walk,
đỉnh cô lập, parity/end sai, cạnh song song, JSON và witness sai, giới hạn tài nguyên,
số đếm 64 bit, timestamp nhỏ nhất của int64, snapshot 65/70 cạnh, timeline 20.000
cạnh, đường tăng Dinic sâu 20.000 cung, residual cut và họ instance thiếu cặp.

## Lệnh chạy lại

Từ `ns-thesis/`:

```sh
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j 4
ctest --test-dir cpp/build --output-on-failure -j 2
```

Mỗi lệnh sau tạo 100.000 instance (50.000 base graph, mỗi graph FIX và FREE):

```sh
cpp/build/nscover_verify --mode small --cases 50000 --seed 11
cpp/build/nscover_verify --mode small --cases 50000 --seed 31
cpp/build/nscover_verify --mode small --cases 50000 --seed 97
cpp/build/nscover_verify --mode large --cases 50000 --seed 23
cpp/build/nscover_verify --mode large --cases 50000 --seed 43
cpp/build/nscover_verify --mode large --cases 50000 --seed 101
python3 cpp/tests/differential.py --cases 2000
python3 cpp/tests/differential.py --large --cases 2000 --seed 29
python3 cpp/tests/cli.py
```

Sanitizer:

```sh
cmake -S cpp -B cpp/build-sanitize -DCMAKE_BUILD_TYPE=RelWithDebInfo -DNSCOVER_SANITIZE=ON
cmake --build cpp/build-sanitize -j 2
ctest --test-dir cpp/build-sanitize --output-on-failure -j 2
```

Lượt đầu trong sandbox bị LeakSanitizer từ chối do ptrace; ca throughput timeline
Dinic cũng chạm timeout khi instrument. Log thất bại môi trường được giữ tại
`ctest-sanitize-sandbox-console.log`. Độ sâu Dinic sau đó được kiểm tra trực tiếp
bằng một đường tăng 20.000 cung, timeline 20.000 cạnh được kiểm tra bằng backend
tham lam, và timeline 512 cạnh bằng backend Dinic. Cách này giữ kiểm tra stack sâu
mà không lặp hàng chục nghìn lần cùng một đường dài trong test đơn vị. Toàn bộ
CTest sau cùng chạy ngoài sandbox thành công với ASan, UBSan và LeakSanitizer
mặc định; không tắt kiểm tra rò rỉ. Kết quả cuối là `ctest-sanitize.log` và
`ctest-sanitize.json`.

## Dữ liệu thật

Đã hoàn thành **50/50 instance trên 25 thành phố**; mọi câu trả lời YES có witness
được kiểm tra. Có 48 ca cần đường tăng; D và số bước tăng lớn nhất là 467. Instance
lớn nhất có 387.467 cạnh. Nhánh-cận kết luận trùng ở 2 ca và LIMIT ở 48 ca còn lại;
chỉ 2 ca đó được tính là đối chiếu nhánh-cận thành công. Xem `summary.json` và
`transit.jsonl` để đọc kết quả đầy đủ.

```sh
python3 cpp/tests/replay_transit.py --branch-seconds 2 \
    --output results/cpp17-20261026/transit.jsonl
```

Chạy cả FIX và FREE trên 25 mạng có sẵn trong `data/raw/transit/`. Bộ nạp hiện tại
giữ non-strict và bỏ chuyến trùng hoàn toàn. Mạng cả ngày trên 250.000 cạnh được
thay bằng khối 3 giờ có nhiều đoạn chuyến nhất; khối đó vẫn có thể trên 250.000 cạnh.
Mỗi instance có nghiệm theo cách dựng (một walk mỗi chuyến), và C++ phải tự dựng
walk riêng rồi kiểm tra. Nhánh-cận có tối đa 2.000 max-flow và 2 giây giữa các nút;
một max-flow đang chạy không bị ngắt nên thời gian thực có thể vượt 2 giây.

`transit.jsonl` ghi từng ca, `branch_verified` và LIMIT; dòng cuối `complete: true`
xác nhận đã xử lý hết danh sách. Không coi LIMIT là một kết quả NO hay một ca
đối chiếu đã đạt. Không chạy oracle thử mọi thứ tự cạnh trên các mạng lớn vì chi
phí hàm mũ. Dữ liệu này khác census lịch sử dùng strict loader; không dùng để thay
số liệu của khóa luận nếu chưa thống nhất lại protocol thực nghiệm.

## Tệp bằng chứng và giới hạn

- `ctest-release.log`, `ctest-sanitize.log`: output gốc của từng nhóm CTest.
- `ctest-*.json`, `seeds-*.jsonl`: số ca, nhánh tăng, số flow và trạng thái.
- `differential-*.json`, `cli.json`, `headers.json`: đối chiếu ngôn ngữ và giao diện.
- `python-agreement*.json`, `python-existing-checks.json`: chạy lại kiểm tra Python
  hiện có; ba bài agreement/agreement_large/backends dùng 30 giây mỗi bài.
- `environment.json`: compiler, thư viện, hệ điều hành và cờ build.
- `source-sha256.json`: mã băm các tệp triển khai C++ và công cụ kiểm chứng.
- `summary.json`: tổng hợp máy đọc được.

Thời gian đo là development, có các tiến trình chạy đồng thời; không dùng để kết
luận speedup so với các số đo Python cũ. Các kiểm tra hữu hạn này kiểm tra cài đặt,
không thay thế kiểm toán chứng minh M-lồi và bổ đề đường tăng.
