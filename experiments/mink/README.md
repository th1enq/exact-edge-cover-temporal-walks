# Cận số walk tối thiểu trên dữ liệu giao thông

Thực hiện từ thư mục gốc của kho, không cần cài thêm thư viện:

```sh
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j 4
python3 experiments/mink/bounds.py
bash experiments/mink/run.sh
python3 experiments/mink/table.py
```

`bounds.py` sử dụng bộ nạp transit hiện có: toàn bộ ngày, thời gian không giảm,
loại chuyến không nhất quán, self-loop và các chuyến trùng hoàn toàn. Mỗi chuyến
đóng góp một token tại điểm xuất phát. Instance FREE không có vector đích;
thời gian được nén thứ hạng, giữ nguyên quan hệ bằng nhau và thứ tự.
Kết quả được lưu trong `results/mink-20261030/`.

Cận tĩnh là giá trị lớn hơn giữa một nửa số đỉnh bậc lẻ (làm tròn lên) và số
thành phần liên thông có cạnh của đa đồ thị bỏ qua thời gian. Bậc tính cả các
cạnh song song. Cận snapshot là số thành phần liên thông có cạnh lớn nhất tại
một thời điểm. Mỗi thành phần như vậy cần ít nhất một walk tại thời điểm đó.
Hai phép tính dùng danh sách kề và duyệt đồ thị, tổng thời gian O(n+m), bộ nhớ
O(n+m); không sắp xếp cạnh trong bước tính cận. Cột LB lấy giá trị lớn hơn của
hai cận trên.

`nscover_mink` kiểm tra vector ban đầu bằng pair-flow và kiểm tra witness.
Ứng dụng xáo trộn thứ tự đỉnh bằng seed 20261030, trải token theo thứ tự này,
thử xóa từng khối, rồi giảm nửa kích thước khối sau mỗi lượt. Các khối
cùng kích thước tại cùng một đỉnh tạo cùng vector nên không kiểm tra lặp lại
sau khi đã bị từ chối. Chỉ chấp nhận
xóa khi solver trả YES và witness hợp lệ. Mỗi phép thử gọi thư viện trong cùng
tiến trình. Luồng giám sát lưu nguyên tử vector YES cuối cùng và vị trí duyệt
khi hết 40 giây; lần chạy tiếp theo dùng lại checkpoint. Phép thử đang dở sẽ
được thử lại. Nếu lần kiểm tra ban đầu chưa xong trước thời hạn, chương trình
báo lỗi và không tạo checkpoint chưa được xác minh. `checks` và `seconds`
được cộng dồn, gồm cả lần xác minh checkpoint ở mỗi lượt chạy.

Mỗi lượt `run.sh` dùng ba tiến trình đồng thời, giới hạn toàn lượt dưới 280
giây. Mã 124 biểu thị hết hạn toàn lượt; checkpoint đã ghi vẫn được giữ lại.
Chạy tối đa sáu lượt hoặc dừng khi toàn bộ thành phố hội tụ. Thành phố đã hội
tụ được bỏ qua; các thành phố có ít thời gian tích lũy được ưu tiên. Nếu tiến
trình bị giới hạn toàn lượt ngắt trước khi lưu, lượt sau tiếp tục từ checkpoint
trước đó. Không chạy hai lượt đồng thời trên cùng thư mục kết quả.

UB là tổng token của vector YES đã kiểm chứng. Hội tụ chỉ chứng minh tính tối
thiểu theo phép xóa từng token trong vector hiện tại; không chứng minh tối ưu
khi cho phép chuyển điểm xuất phát. Chỉ khi UB = LB mới kết luận k* được chứng
minh (`proven=true`). Vector tối ưu có thể nằm ngoài miền vector nhỏ hơn hoặc
bằng vector ban đầu theo từng thành phần. `table.py` tạo bảng JSON và Markdown.

Sau khi lập bảng, chạy `python3 experiments/mink/validate.py` để gọi lại CLI
trên ba thành phố đã hội tụ có ít cạnh nhất và lưu instance với vector đã
thu nhỏ trong `validation/`. Script kiểm tra mọi vector xóa một token của
thành phố nhỏ nhất theo số cạnh, rồi theo số đỉnh. Các token cùng đỉnh tạo
cùng một vector nên chỉ cần một phép thử cho mỗi tọa độ dương; báo cáo ghi rõ
số token tương đương được bao phủ. Kết quả CLI và trạng thái kiểm tra được
lưu trong `validation/report.json`.
