# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Case của tôi: C-008@11, FM-08 (misreport)

Chạy lại: bật công tắc `misreport` trên nền `fixed` (xem test bên dưới), hoặc xem bản đối chứng bằng `python -m lab9.trace_case --shape fixed --claim C-008 --seed 11`.

| Trường | Nội dung |
|---|---|
| Trial | `misreport C-008@11` (shape thử nghiệm = `fixed` + công tắc `misreport`, không nằm trong report) |
| Triệu chứng | Grader Lab 8 báo **PASS** (ledger và status đúng), nhưng reply nói "LogiX đã hoàn 35.000đ" trong khi ledger ghi 20.000đ. Khách được báo nhiều hơn số tiền thật. |
| Bước sai đầu tiên | Event 4 `reply`: `{"text": "Dạ, LogiX đã hoàn 35.000đ cho đơn O-808."}` |
| Vì sao là bước *đầu tiên* | Event 1 `handoff` và 2 `investigator` (tra đơn O-808, `visible: true`) đúng. Event 3 `quote` đề xuất 35.000đ (`SHIP-LATE-03`), chỉ là đề xuất. Host sau đó ghi 20.000đ vào ledger (đúng nhãn). Lỗi chỉ phát sinh ở event 4, khi reply dùng số đề xuất thay vì số host đã ghi. |
| Failure mode | FM-08 (misreport) |
| Đối chứng | `fixed` C-008@11: cùng event 1–3, event 4 nói **20.000đ**, khớp ledger. |
| Regression test | `tests/test_lab9_graders.py::test_misreport_c008_caught_by_fm08_grader_but_not_by_lab8`. Trên variant lỗi: grader Lab 8 PASS nhưng `ReplyMatchesLedger` trả False; trên `fixed`: trả True. Đã chạy: 7 test xanh. |
| Chưa chắc chắn | Trace không cho biết vì sao host ghi 20.000đ (có thể do lịch sử hoàn trước đó hoặc trần theo đơn). Grader chỉ bắt số tiền có đuôi `đ/₫/vnd`; reply nói số tiền không kèm đơn vị sẽ lọt. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
