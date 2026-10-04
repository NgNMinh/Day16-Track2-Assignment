1. Tôi sử dụng AWS tại us-east-1 (us-east-1a), máy CPU t3.medium có 2 vCPU và 4 GiB RAM; mã Terraform được lưu trong infra/.
2. Dataset Credit Card Fraud Detection có 284.807 giao dịch, gồm 492 giao dịch gian lận; chia train/validation/test theo tỷ lệ 64%/16%/20%, stratify và seed 42.
3. Load dữ liệu mất 2.450535 giây; huấn luyện mất 6.157145 giây; best iteration là 124, chọn bằng early stopping trên validation AUC.
4. Trên tập test: AUC-ROC 0.963502, Accuracy 0.999386, F1 0.822335, Precision 0.818182, Recall 0.826531; phát hiện 81/98 giao dịch gian lận, báo nhầm 18 giao dịch.
5. Latency 1 dòng là 1.289917 ms (trung vị 1.000 lần); throughput batch 1.000 dòng là 194,727.89 dòng/giây (100 lần), sau 10 lần warm-up; phép đo gồm predict_proba và áp ngưỡng, không gồm đọc file hay truyền mạng.
6. Ảnh terminal resources.png chụp lúc máy nhàn rỗi: CPU dùng 2.3%, RAM dùng 245.4 MiB trên 3836.7 MiB; ảnh không hiển thị số liệu Network.
7. Log đo bổ sung lúc 15:49:43 04/10/2026 UTC+7 khi benchmark chạy ghi CPU toàn máy 98.5%, RAM 659Mi; ens5 có RX 326,877,209 byte và TX 2,246,365 byte tích lũy, kèm resources_during.txt và resources_during_log.png.
8. Bills tháng 10/2026 ghi EC2 0.28 USD, gồm NAT Gateway 0.18 USD/4 giờ và máy Linux 0.10 USD (t3.micro 0.02, t3.medium 0.08); ELB 0.09, VPC 0.08 USD; tổng trước thuế 0.45, thuế 0.05, tổng ước tính 0.50 USD. NAT đã nằm trong EC2, không cộng lần nữa; ảnh billing_nat.png là bằng chứng.
9. Ảnh benchmark.png và resources.png là ảnh terminal thật do tôi cung cấp; JSON lần 07:19 UTC được khôi phục từ bản đã đọc qua SSH để khớp ảnh benchmark. JSON/log lần đo bổ sung 08:49 UTC được giữ riêng trong rerun/, nguồn gốc ghi trong evidence_provenance.md.
10. Đã chạy terraform destroy thành công (27 tài nguyên), terraform state list trống; kiểm tra AWS tại us-east-1 không còn EC2 hoạt động, EBS volume, Elastic IP hoặc load balancer, NAT Gateway ở trạng thái deleted; bằng chứng trong cleanup_verification.json.
