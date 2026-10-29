from app.tracking import get_package_status, process_tracking_scan

TRACKING_ID = "TRK1002"

print(process_tracking_scan(3, 2, "In Transit"))
print(get_package_status(TRACKING_ID))