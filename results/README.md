# Kết quả

Mỗi thư mục là một lượt chạy với mã `nscover` ở trạng thái cuối cùng (ngày 25/10/2026).
Mỗi lệnh ghi một tệp `.log` kèm mã thoát (`exit=...`) ở dòng cuối; mọi lệnh có giới hạn
`timeout 300`. Thời gian đo trên máy 4 nhân (i5-10210U), với 2–4 lệnh chạy song song, nên
có thể lệch khoảng 2 lần so với khi chạy một mình.

| Thư mục | Lệnh | Dùng trong khóa luận |
|---|---|---|
| `census-20261025/` | `experiments/census.py` trên 8 tệp dữ liệu; `summary.md` từ `summarize.py` | Bảng `tab:census`, mục `sec:exp-census` |
| `transit-full-20261025/` | `experiments/transit_full.py`, Turku và Grenoble cả ngày, FIX/FREE | Bảng `tab:transit` |
| `family-20261025/` | `experiments/family.py` | Bảng và hình của mục `sec:exp-family` |
| `adversarial-20261025/` | `experiments/adversarial.py`, hạt giống 1 và 2 | Bảng `tab:adversarial` |
| `checks-20261025/` | kiểm thử đơn vị, `tests/agreement.py`, `tests/agreement_large.py`, `tests/backends.py`, `experiments/gamma_mconvex.py`, `experiments/aaai_static_check.py` | Mục `sec:verification` |
| `pre-opt-20261025/` | Các lượt chạy trước hai tối ưu cuối của `pairflow.py` (nút trung gian cho FREE, đệm kề trong `_reach`) | Không; chỉ lưu trữ để đối chiếu |

Bảng LaTeX được sinh bằng `python3 experiments/tables.py results thesis/generated`.
