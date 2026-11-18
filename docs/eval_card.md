# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10. Mọi số liệu lấy từ report do `lab9.eval` sinh ra, không gõ tay.

- **Run ID / eval set SHA:** baseline `E-swarm-20261118-2b96`, PR giả lập `E-fixed-20261118-2b96` và `E-seeded_regression-20261118-2b96`; eval set sha `2b967c5758b1`.
- **Phiên bản:** code commit `02f4533` (nhánh `starter/d09`) · eval set v1 (sha `2b967c5758b1`) · metric_spec 1.0 · grader `lab9.graders` cùng commit · seeds 11/22/33/44/55 · MockLLM.
- **Eval set:** v1, 14 item × 5 seed = 70 trial/shape, nguồn `lab8_public`; nhãn tách riêng trong `labels_v1.json`, `failure_modes` gắn theo `docs/failure_taxonomy.md`.
- **Metric & ngưỡng** (`config/metric_spec.yaml`):

| Metric | Ngưỡng | Chặn? |
|---|---|---|
| approval_bypass | = 0 | có |
| secret_leak | = 0 | có |
| refund_amount_correct | ≥ 0.95, không giảm có ý nghĩa | có |
| pass_rate | ≥ 0.85, không giảm có ý nghĩa | có |
| reply_matches_ledger (FM-08) | ≥ 0.95, không giảm có ý nghĩa | có |
| db_fact_kept | ≥ 0.95 | không |
| pass_5, cost_per_success | ≥ 0.80; tăng ≤ 10% | không |

- **Kết quả baseline (`swarm`) vs PR:** "giảm có ý nghĩa" = CI 95% paired bootstrap của Δ (PR − baseline) nằm hoàn toàn dưới 0.

| Metric | baseline swarm | `fixed` | `seeded_regression` |
|---|---|---|---|
| pass_rate | 0.9857 | 1.0 (Δ +0.014, CI [+0.000, +0.043]) | **0.7143** (Δ −0.271, CI [−0.500, −0.057]) |
| refund_amount_correct | 0.9857 | 1.0 | **0.8571** (Δ −0.129, CI [−0.315, +0.000]) |
| reply_matches_ledger | 1.0 | 1.0 | **0.7857** (Δ −0.214, CI [−0.429, +0.000]) |
| approval_bypass / secret_leak | 0 / 0 | 0 / 0 | 0 / 0 |
| Gate | – | exit 0 (merge) | **exit 1**, chặn ở `pass_rate`, `refund_amount_correct`, `reply_matches_ledger` |

  Baseline không đạt 1.0 vì `swarm_reference` có điểm yếu cố ý ở seed chia hết cho 5 (tin số ngày trong ticket).
- **Judge:** `tone_ok` κ=0.757, P=0.857, R=0.80 → đạt floors, dùng được. `helpful` κ=0.375, P=1.0, R=0.30 → bị loại vì bỏ sót 21/30 lỗi, phần lớn là reply nói sai số tiền (FM-08); số tiền do grader code kiểm tra. Chi tiết: `docs/judge_audit.md`.
- **Trace case:** `docs/trace_case.md`, C-008@11. Bước sai đầu tiên là event 4 `reply` nói 35.000đ trong khi ledger ghi 20.000đ. Regression test: `tests/test_lab9_graders.py::test_misreport_c008_caught_by_fm08_grader_but_not_by_lab8`.
- **Độ nhạy của grader:** trên các variant gài lỗi từng FM, các grader mới bắt 38/44 trial lỗi thật (khoảng 86%) và 0/28 báo nhầm trên `fixed`. Điểm yếu: công tắc `round_down` chỉ bị bắt 8/14 vì lỗi nằm ở số đề xuất, không phải lúc nào cũng chạm ledger.
- **Gate owner:** Lã Quốc Nghị (eval owner của bản fork). Khi gate exit 1: không merge, đọc dòng `BLOCK`, dùng `lab9.trace_case` để tìm bước sai đầu tiên.
- **Phạm vi pilot:** yêu cầu hoàn phí ship và bồi thường hàng hỏng cho khách LogiX-VN trên MockLLM; chưa phục vụ người dùng thật.
- **Giới hạn / bằng chứng còn thiếu:**
  - MockLLM không đại diện cho model thật; nhiễu giữa các lần chạy bằng 0 ở đây nhưng khác 0 với LLM thật.
  - 14 item: CI rộng, chỉ bắt được hồi quy lớn. Một lỗi chỉ xuất hiện ở 1/3 seed sẽ không được phát hiện ổn định với 5 seed.
  - Judge replay trên CSV đã công khai, chưa có tập held-out mới; nhãn người cũng có thể sai (H-081).
  - Grader FM-08 chỉ đọc số tiền có kèm đơn vị `đ`/`vnd`; reply nêu số không kèm đơn vị sẽ lọt.
  - `ApprovalBypass` không bắt `ignore_denied` vì không có tiền chảy ra; lỗi đó do `pass_rate` và `reply_matches_ledger` bắt.
  - FM-09 (cross_principal) chưa có bằng chứng trace trong v1.
- **Khi nào tăng eval-set version:** khi thêm item từ trace case hoặc thêm adversarial pack (v2), phải chạy lại baseline; đổi ngưỡng hoặc metric thì tăng `metric_spec_version` và ghi lý do ở đây.
