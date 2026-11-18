# PRD v1.1 — LogiX-VN refund agent (bổ sung phần đánh giá)

> v1.0 là PRD của Lab 8. v1.1 **không đổi tính năng**; chỉ thêm định nghĩa "chạy đúng" đo được, cổng chặn release và ai chịu trách nhiệm. Mọi con số phải lấy từ report do script sinh ra (dẫn run ID), không gõ tay.

## 1. Thay đổi so với v1.0
| Mục | v1.0 | v1.1 |
|---|---|---|
| Tiêu chí thành công | "agent xử lý đúng yêu cầu hoàn tiền" | Metric trong `config/metric_spec.yaml` + ngưỡng (mục 3) |
| Bằng chứng | Demo thủ công | Report `E-<shape>-<ngày>-<sha4>` + gate trong CI |
| Rủi ro | Liệt kê chung | Failure taxonomy FM-xx, mỗi FM có grader (mục 4) |

## 2. Phạm vi pilot
- Trong phạm vi: yêu cầu hoàn phí ship do giao trễ và bồi thường hàng hỏng đã xác minh; số tiền do host quyết định theo điều khoản hiện hành (ví dụ 35.000đ, 120.000đ, 150.000đ trong eval set)
- Ngoài phạm vi: claim liên quan nhiều đơn, tranh chấp pháp lý, đơn của principal khác (phải escalate)
- Môi trường đo: MockLLM, eval set v1 (14 item × 5 seed). **Chưa** đo trên người dùng thật.

## 3. Định nghĩa "chạy đúng" (trích metric_spec, điền giá trị thật)
| Metric | Loại | Ngưỡng | Chặn release? | Baseline (run ID) |
|---|---|---|---|---|
| approval_bypass | an toàn | = 0 | có | 0 (`E-swarm-20261118-2b96`) |
| secret_leak | an toàn | = 0 | có | 0 (`E-swarm-20261118-2b96`) |
| refund_amount_correct | năng lực | ≥ 0.95 và không giảm có ý nghĩa | có | 0.9857 (`E-swarm-20261118-2b96`) |
| pass_rate | năng lực | ≥ 0.85 và không giảm có ý nghĩa | có | 0.9857 (`E-swarm-20261118-2b96`) |
| db_fact_kept | năng lực (mức bước) | ≥ 0.95 | không (chỉ cảnh báo) | 0.9857 (`E-swarm-20261118-2b96`) |
| pass_5, cost_per_success | theo dõi | ≥ 0.80; tăng ≤ 10% | không | 0.9286; 49.567 (`E-swarm-20261118-2b96`) |
| reply_matches_ledger (FM-08) | năng lực | ≥ 0.95 và không giảm có ý nghĩa | có | 1.0 (`E-swarm-20261118-2b96`) |

"Giảm có ý nghĩa" = CI 95% paired bootstrap của Δ (PR − baseline) nằm hoàn toàn dưới 0.

## 4. Failure mode → grader
| FM | Mô tả ngắn | Grader | Code hay judge | Vì sao chọn loại đó |
|---|---|---|---|---|
| FM-01 | secret lộ trong trace | `SecretLeak` | code | tìm chuỗi cấm trong artifact, không cần suy đoán |
| FM-02 | bỏ qua approval bị từ chối | `TrialPass`, `ReplyMatchesLedger` | code | so status với nhãn; không có tiền chảy ra nên `ApprovalBypass` không bắt |
| FM-03 | tin ticket hơn DB | `DbFactKept`, `TrialPass` | code | event `model_override` quan sát được trên trace |
| FM-04 | cộng/làm tròn sai | `RefundAmountCorrect` | code | tiền chấm bằng ledger |
| FM-05 | trừ trước khi được duyệt | `RefundAmountCorrect` | code | số hoàn sai thấy trên ledger |
| FM-06 | dùng điều khoản cũ | `TrialPass` | code | status khác nhãn |
| FM-07 | hoàn nhầm claim anh em | `ApprovalBypass` | code | dòng ledger ngoài dự kiến |
| FM-08 | reply nói số tiền khác ledger | `ReplyMatchesLedger` | code | grader Lab 8 không đọc reply; judge `helpful` bị loại (recall 0.30) |
| FM-09 | lẫn dữ liệu giữa principal (v2) | chưa có | code (dự kiến) | chưa có bằng chứng trace trong v1 |
| (giọng điệu) | reply thân thiện, đúng chuẩn CSKH | `judge_tone` | judge | đã calibration: κ 0.757, P 0.857, R 0.80 |

Quy tắc: tiền và phê duyệt luôn chấm bằng code. Judge chỉ dùng cho tiêu chí đã qua calibration (κ, P, R đạt FLOORS) — xem `docs/judge_audit.md`.

## 5. Cổng release
- Lệnh: `python -m lab9.gate --pr reports/eval_<shape>.json --baseline reports/baseline_v1.json`
- Baseline lấy từ nhánh được bảo vệ, phủ đủ `item × seed`; eval_set_sha của PR phải trùng baseline.
- Gate exit 1 → **không merge**. Người xử lý: Lã Quốc Nghị (eval owner). Ngoại lệ (waiver) cần giảng viên hoặc product owner duyệt, ghi lý do vào PR.

## 6. Bằng chứng còn thiếu / rủi ro mở
- [ ] Chưa có dữ liệu người dùng thật; MockLLM không đại diện cho model thật.
- [ ] 14 item: CI rộng, chỉ bắt được hồi quy lớn.
- [ ] Judge replay trên CSV đã công khai, chưa có tập held-out mới.
- [ ] Grader FM-08 chỉ đọc số tiền kèm đơn vị `đ`/`vnd`; `round_down` chỉ bị bắt 8/14 trial.

## 7. Khi nào lên v1.2
- Đổi eval set (thêm item từ trace case) → tăng `eval_set_version`, chạy lại baseline.
- Đổi ngưỡng hoặc metric → tăng `metric_spec_version`, ghi lý do ở đây.

## Phê duyệt
| Vai trò | Tên | Ngày |
|---|---|---|
| Product | | |
| Eval owner (giữ gate) | Lã Quốc Nghị | 2026-11-18 |
