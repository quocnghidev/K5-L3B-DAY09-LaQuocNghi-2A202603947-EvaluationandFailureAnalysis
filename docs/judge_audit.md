# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5` (replay, không cần API key). FAIL là lớp dương: việc của judge là tìm lỗi.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có (cả 3) | **Dùng**, kèm hiệu chỉnh Rogan-Gladen khi báo tỉ lệ lỗi |
| helpful | 100 | 0.375 | 1.000 | 0.300 | **Không** (κ và recall trượt) | **Loại** khỏi gate |

Ma trận nhầm lẫn (tp/fp/fn/tn): tone_ok 24/4/6/66; helpful 9/0/21/70.

## ≥5 case audit thủ công (tone_ok, 10 bất đồng; chọn 6 đại diện)
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú và hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | H-081 "đơn O-107 chưa đủ điều kiện hoàn theo chính sách hiện hành ạ" | FAIL | PASS | **Judge** | Đơn O-107 đủ điều kiện hoàn (claim C-001 hoàn 35.000đ), nên từ chối là sai sự thật dù giọng lịch sự. Người gắn nhãn đọc nhầm ticket. **Hành động:** sửa nhãn người H-081 thành FAIL; rubric ghi rõ "lịch sự không bù được cho nội dung sai". Ca này cũng là lỗi nội dung, nên thuộc grader code chứ không phải judge tone.
| 2 | H-042 "đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ." | FAIL | PASS | **Người** | Ngắn nhưng đủ ý. Judge phạt vì "thiếu xin lỗi". Rubric thêm: xin lỗi chỉ bắt buộc khi claim có lỗi của LogiX, không bắt buộc ở mọi reply. |
| 3 | H-051 "đã refund 90.000đ" | FAIL | PASS | **Người** | CS LogiX cho phép từ "refund". Rubric thêm: thuật ngữ nghiệp vụ tiếng Anh trong danh sách cho phép không bị trừ. |
| 4 | H-008 "Em đã hoàn tiền cho anh rồi nha" | PASS | FAIL | **Người** | Xưng "em" và "nha" quá suồng sã. Rubric thêm ví dụ âm: kết thúc bằng "nha/nhé" và xưng "bạn/em" với khách là FAIL. |
| 5 | H-029 "không cần nhắn thêm" | PASS | FAIL | **Người** | Giọng ra lệnh; judge chỉ thấy "Dạ, vui lòng" ở đầu câu. Rubric thêm: đọc cả câu, câu mệnh lệnh phủ định gửi khách là FAIL. |
| 6 | H-063 "đã hoàn 20.000đ và sẽ hoàn thêm" | PASS | FAIL | **Người** | Hứa hoàn thêm ngoài kết quả hệ thống. Lỗi này nằm ở **độ chính xác nội dung** chứ không phải giọng điệu, nên **không nên giao cho judge tone**: dùng grader code ở M3 (số tiền trong reply so với ledger). |

Các ca còn lại cùng một kiểu: H-070 (emoji khi khiếu nại) và H-094 (mất dấu tiếng Việt) judge bỏ sót, rubric cần liệt kê emoji và văn bản mất dấu là FAIL; H-088 ("Dạ, dạ" do lỗi gõ) người cho qua nhưng judge phạt, nên coi lỗi gõ lặp từ là nhẹ và không FAIL.

Quy luật chung: judge **bỏ sót** lỗi khi chỉ cần nhìn một từ ("Dạ", "xin lỗi") là có vẻ lịch sự, và **báo nhầm** khi áp rubric quá cứng (bắt buộc xin lỗi, cấm tiếng Anh). Sửa rubric theo hai hướng đó.

## Kết luận
- **Loại judge `helpful`.** Precision 1.0 nhưng recall 0.3 và κ 0.375: nó bỏ sót 21/30 lỗi thật (ma trận 9/0/21/70), nên làm gate sẽ cho bản tệ lọt qua. Tỉ lệ lỗi đo được 0.09 sau Rogan-Gladen là 0.30, tức tệ gấp 3 so với con số judge báo.
- **Nguyên nhân cụ thể:** 18/21 ca bị bỏ sót là reply nêu số tiền khác ledger (ví dụ HL-015: reply 55.000đ, ledger 40.000đ; HL-087: reply 60.000đ, ledger 90.000đ), tức FM-08. Judge bị đánh lừa bởi câu xin lỗi dài, trong khi 3 ca còn lại (HL-047, HL-091, HL-097: "Ok bạn, đơn … xử lý rồi nhé") là reply cộc lốc, không nêu số tiền. Số tiền phải do **grader code** đối chiếu với ledger (metric FM-08 ở M3), không giao cho judge.
- **Dùng `tone_ok`** cho tiêu chí giọng điệu (κ 0.757, P 0.857, R 0.8), vẫn sai 10/100 ca. Tỉ lệ lỗi quan sát 0.28, hiệu chỉnh Rogan-Gladen ra 0.30.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật. Nhãn người cũng có thể sai (H-081), nên cần ít nhất hai người gắn nhãn cho tập held-out.
