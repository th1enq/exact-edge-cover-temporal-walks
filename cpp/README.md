# NS-FIX và NS-FREE bằng C++17

Bản cài đặt độc lập của các thuật toán trong `../nscover/`. Hạt nhân thuật toán là
C++17 thuần, tách header công khai và source; executable không gọi Python. Công cụ
JSON dùng thư viện header nlohmann/json của hệ thống. Các script Python trong
`tests/` chỉ làm cầu nối kiểm chứng với bản tham chiếu và bộ nạp dữ liệu hiện có.

## Biên dịch

Cần compiler C++17, CMake >= 3.16 và nlohmann/json >= 3.2. Trên Debian/Ubuntu, gói
JSON là `nlohmann-json3-dev`. Chạy các lệnh từ `ns-thesis/`:

```sh
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j 4
ctest --test-dir cpp/build --output-on-failure
```

Không có bước tải dependency qua mạng trong CMake. `libnscover.a` chứa toàn bộ
thuật toán; `libnscover_io.a` bổ sung chuyển đổi JSON.

## Chạy bộ giải

```sh
cpp/build/nscover_solve cpp/examples/nonstrict-path.json
cpp/build/nscover_solve cpp/examples/aaai-counterexample.json --verify-backtrack
cpp/build/nscover_solve input.json --solver branch --max-flows 2000 --seconds 10
cpp/build/nscover_solve input.json --solver backtrack --max-states 2000000 --seconds 10
cpp/build/nscover_solve input.json --backend dinic --verify-branch --verify-backtrack
cpp/build/nscover_solve --batch --summary < instances.jsonl > results.jsonl
```

Đầu vào tương thích `Instance.to_json()` của Python: `num_vertices`, `edges`
(`u`, `v`, `time`), `start`, tùy chọn `end` và `name`. Bỏ `end` hoặc đặt `null` để
giải NS-FREE. Đỉnh và ID cạnh bắt đầu từ 0; ID cạnh là vị trí trong mảng đầu vào.
Thời điểm là số nguyên 64 bit có dấu; thứ tự cạnh đầu vào tùy ý. Mỗi cạnh song song
có một ID riêng; không cho self-loop. Walk được phép rỗng, chờ và dùng nhiều cạnh
cùng thời điểm.

Đầu ra JSON chứa `status`, thống kê và, với YES của pair/branch, `tails`, `walks`
và `witness: "checked"`. Mỗi phần tử `walks` có `start` và danh sách ID cạnh theo
thứ tự đi. Mọi YES của pair/branch đều dựng và kiểm tra walk theo định nghĩa, kể cả
khi dùng `--summary` (chỉ bỏ các mảng lớn khỏi đầu ra). Bộ backtracking chỉ trả
trạng thái và số trạng thái đã duyệt, tương tự `brute_force` của Python.

Mạng chuỗi có bốn backend; cả bốn phải cho cùng tính khả thi nhưng có thể có
orientation và D khác nhau:

- `--backend online` (mặc định) duyệt cạnh theo thời gian, gán tham lam, và khi
  một cạnh bị kẹt thì tìm đường tăng ngay, lúc chỉ các cạnh trước đó đã được định
  hướng. Thêm tail tại slot s của w được khi không slot nào >= s chặt; nếu không,
  với T là slot chặt đầu tiên >= s, bỏ một tail bất kỳ của w ở slot <= T rồi đảo
  cạnh đó sang đầu kia. Slack mỗi đỉnh nằm trong cây phân đoạn (cộng hậu tố, tìm
  slot chặt đầu tiên), nên tương lai còn trống và việc tìm đường chỉ cục bộ. Cạnh
  kẹt không tới được slack nào thì max-flow < m (tập không tới được sink đóng).
- `--backend phased` gán tham lam như online, rồi tìm đường tăng theo pha: một BFS
  từ mọi cạnh chưa định hướng, áp dụng các đường rời nhau về cạnh, mỗi lần áp dụng
  được kiểm lại với cận tiền tố và hoàn tác nếu vi phạm. Đúng nhưng chậm hơn online
  1-4 lần trên 25 mạng giao thông (mỗi pha duyệt cả mạng, không còn cục bộ), và chưa
  có cận số pha, nên chỉ để đối chứng.
- `--backend greedy` gán tham lam toàn bộ rồi dùng Dinic trên mạng dư.
- `--backend dinic` giải mạng chuỗi từ đầu, làm đối chứng độc lập.

 C++ không phụ thuộc SciPy; hai backend SciPy của Python
được dùng làm đối chứng qua bản tham chiếu.

`--verify-backtrack` và `--verify-branch` chạy thêm bộ giải đối chứng. Trường
`*_verified` chỉ true khi cả hai đã kết luận và khớp nhau. `LIMIT` luôn khác `NO`.
Mã thoát 0 nghĩa là xử lý thành công, kể cả NO/LIMIT; mã 2 là lỗi input, lỗi kiểm
chứng hoặc lỗi bất biến. Khi dùng batch, lỗi dừng tiến trình và giữ các dòng trước.

## Module và API

| Header / source | Trách nhiệm |
|---|---|
| `instance` | Mô hình, số đếm và thời điểm 64 bit, kiểm tra input và tràn số |
| `timeline` | Snapshot, thành phần liên thông, lần xuất hiện, parity và thành phần chẵn |
| `maxflow` | Dinic dạng lặp trên mảng kề CSR, mạng định hướng với bậc vào cho trước |
| `chainflow` | Capacity tiền tố, max-flow ban đầu và đếm walk trước từng thành phần |
| `solver.hpp`, `branch.cpp` | Kết quả chung, nhánh-cận trên thành phần chẵn chết |
| `solver.hpp`, `pairflow.cpp` | Luồng cặp, BFS đa nguồn, trao đổi M-lồi, định hướng lại |
| `backtrack` | Oracle duyệt cạnh và di chuyển token trực tiếp theo định nghĩa |
| `walks` | Dựng walk bằng Euler và bộ kiểm tra độc lập |
| `io` | JSON tương thích Python |

Ví dụ sử dụng thư viện:

```cpp
#include "nscover/solver.hpp"
#include "nscover/walks.hpp"

nscover::Instance input{3, {{0, 1, 5}, {1, 2, 5}},
                        {1, 0, 0}, std::vector<nscover::Count>{0, 0, 1}, "path"};
auto result = nscover::solve_pairflow(input);
if (result.status == nscover::Status::Yes) {
    auto walks = nscover::build_walks(input, result.tails);
    nscover::check_walks(input, walks);
}
```

Các hàm kiểm tra dùng exception, có hiệu lực cả khi build Release với `NDEBUG`.
Mạng luồng, Euler và backtracking dùng stack/queue tường minh. Backtracking ghi nhớ
trạng thái `(snapshot, token counts, unused edge bitset)`; bitset hỗ trợ snapshot
có hơn 64 cạnh. Nó không gọi timeline, max-flow hay bổ đề đặc trưng.

Trong pair-flow, `flow` lưu số cặp trên cung chờ, `x` lưu trạng thái cục bộ hợp lệ,
và `d = boundary(flow) - x`. Với mỗi thành phần chết, yêu cầu một cặp vào/ra tạo
một đơn vị lệch dương. BFS tìm đường từ dương sang âm; các phép trao đổi được tính
trên trạng thái trước bước tăng, rồi áp dụng đồng thời và định hướng lại thành
phần bị đổi. Bản cài đặt kiểm tra không âm, không làm rỗng thành phần chẵn, khả thi
của orientation và phương trình boundary sau mỗi bước. Số bước tăng phải <= D. Mỗi bước tăng chỉ kiểm tra các cổng đã đổi và chi phí
tỉ lệ số cổng BFS đã thăm; phương trình boundary trên mọi cổng được kiểm tra lúc
khởi tạo và trước khi trả YES.

## Kiểm chứng

```sh
# Kiểm tra thêm nhiều hạt giống; mỗi base graph tạo cả FIX và FREE.
cpp/build/nscover_verify --mode small --cases 50000 --seed 11
cpp/build/nscover_verify --mode large --cases 50000 --seed 23

# Python và C++ đối chiếu cả trạng thái và walk.
python3 cpp/tests/differential.py --cases 2000
python3 cpp/tests/differential.py --large --cases 2000 --seed 29

# Sanitizer.
cmake -S cpp -B cpp/build-sanitize -DCMAKE_BUILD_TYPE=RelWithDebInfo -DNSCOVER_SANITIZE=ON
cmake --build cpp/build-sanitize -j 2
ctest --test-dir cpp/build-sanitize --output-on-failure

# Dữ liệu giao thông đã tải: mỗi mạng chạy FIX và FREE.
python3 cpp/tests/replay_transit.py --branch-seconds 2 \
    --output results/cpp17-20261026/transit.jsonl
```

CTest bao gồm phản ví dụ AAAI, walk nhiều cạnh cùng giờ, cạnh song song, đồ thị
rỗng, đỉnh cô lập, đếm/parity không hợp lệ, input JSON sai, witness sai, giới hạn
tài nguyên, số 64 bit, snapshot 70 cạnh, timeline 20.000 cạnh, họ instance khó,
68.040 instance vét cạn và hai bộ test ngẫu nhiên. Vét cạn xét mọi đa tập tối đa
4 cạnh trên 3 đỉnh và 2 thời điểm, mọi start trong `{0,1,2}^3`, NS-FREE và mọi
end có cùng tổng. Mỗi ca so sánh ba backend pair-flow với backtracking và
nhánh-cận; mọi YES đều dựng và kiểm tra walk. Khi có lỗi, ghi `failure.json`
tại thư mục đang chạy để phát lại.

Replay giao thông dùng bộ nạp non-strict hiện tại, bỏ các chuyến trùng hoàn toàn.
Mạng trên 250.000 cạnh dùng khối 3 giờ có nhiều đoạn chuyến nhất. Do đó kết quả
không mặc nhiên đồng nhất với census cũ dùng strict loader. Mọi instance này có
nghiệm biết trước: một walk cho mỗi chuyến; C++ vẫn phải dựng witness riêng và
kiểm tra. Nhánh-cận có giới hạn riêng cho mỗi instance.

## Giới hạn thực tế

- Backtracking theo định nghĩa là hàm mũ; chỉ các ca nhỏ mới dùng nó làm oracle.
  Các ca lớn dùng nhánh-cận và witness; ca nhánh-cận LIMIT được báo riêng.
- Giới hạn thời gian được kiểm tra giữa các trạng thái backtracking hoặc giữa
  các nút nhánh-cận; một lần max-flow đang chạy không bị ngắt giữa chừng.
- Node/edge ID dùng `int`; kích thước vượt khả năng đánh chỉ số bị từ chối.
  Tổng số đếm hoặc `start[v] + degree[v]` vượt int64 bị báo overflow.
- Witness tường minh cần O(k+m) bộ nhớ, kể cả walk rỗng; API quyết định khả thi
  xử lý được số walk lớn hơn khả năng xuất một witness tường minh.
- Phần định hướng lại dùng max-flow từ đầu giống Python; cận dùng warm-start
  orientation trong chứng minh chưa được tối ưu vào bước này.
- Đối chiếu hữu hạn và sanitizer hỗ trợ kiểm tra cài đặt; không thay thế chứng
  minh toán học cho mọi instance.

Kết quả chạy thực tế, lệnh và giới hạn được lưu tại
[`../results/cpp17-20261026/`](../results/cpp17-20261026/).
