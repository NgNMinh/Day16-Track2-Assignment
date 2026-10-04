benchmark.png và resources.png là ảnh cửa sổ terminal thật do người dùng cung cấp, được sao chép nguyên bản.
benchmark.png khớp benchmark_result.json của lần 07:19 UTC; JSON được khôi phục từ output đầy đủ đã xác minh qua SSH trước đó. Xem ../evidence_provenance.md.
resources.png hiển thị CPU/RAM lúc máy nhàn rỗi; chưa có Network. resources_during_log.png bổ sung CPU/RAM/Network thực tế từ log lần benchmark 08:49 UTC.
benchmark_rerun_log.png là ảnh trang hiển thị log lần 08:49 UTC; JSON và log lần này nằm trong ../rerun/.
billing.png là ảnh AWS Billing Dashboard; các ảnh Bills bổ sung bên dưới cung cấp chi phí theo dịch vụ và NAT.
billing_bills.png là ảnh trang Bills tháng 10/2026 do người dùng cung cấp, tổng ước tính 0.50 USD, trạng thái Pending; chưa có chi tiết phí dịch vụ.
billing_services.png cho thấy bảng phí dịch vụ: EC2 0.28 USD, Load Balancing 0.09 USD, VPC 0.08 USD; trước thuế 0.45 USD, thuế 0.05 USD. Các hàng đang thu gọn nên chưa thấy phí NAT Gateway riêng.
billing_nat.png là ảnh Bills đã mở chi tiết EC2 tại US East (N. Virginia): NAT Gateway 0.18 USD/4 giờ, Linux 0.10 USD gồm t3.micro 0.02 USD và t3.medium 0.08 USD. Ảnh này đáp ứng phần Billing thể hiện EC2 và NAT; không cộng NAT lần nữa vào tổng EC2 0.28 USD.
