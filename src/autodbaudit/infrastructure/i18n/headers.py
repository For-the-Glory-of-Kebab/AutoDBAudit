"""
Column header translations.

Maps English column headers to Persian equivalents.
Organized by sheet for maintainability.
"""

# Common columns used across multiple sheets
COMMON_HEADERS = {
    # Identification
    "ID": "شناسه",
    "Server": "سرور",
    "Instance": "نمونه",
    "Database": "پایگاه‌داده",
    "Name": "نام",
    "Type": "نوع",
    # Status columns
    "Status": "وضعیت",
    "State": "حالت",
    "Result": "نتیجه",
    "Risk Level": "سطح ریسک",
    # Audit trail
    "Notes": "یادداشت‌ها",
    "Justification": "توجیه",
    "Last Revised": "آخرین بازبینی",
    "Last Reviewed": "آخرین بررسی",
    "Review Status": "وضعیت بررسی",
    "Detected Date": "تاریخ شناسایی",
    "Created": "ایجاد شده",
    "Modified": "تغییر یافته",
    # Boolean flags
    "Enabled": "فعال",
    "Disabled": "غیرفعال",
    "Active": "فعال",
    "Inactive": "غیرفعال",
    # Actions
    "Recommendation": "توصیه",
    "Finding": "یافته",
    "Description": "توضیحات",
    "Change Description": "توضیح تغییر",
    "Change Type": "نوع تغییر",
    "Category": "دسته‌بندی",
}

# Sheet-specific headers (overrides common if same key)
INSTANCE_HEADERS = {
    "Config Name": "نام پیکربندی",
    "Server Name": "نام سرور",
    "Instance Name": "نام نمونه",
    "Machine Name": "نام ماشین",
    "IP Address": "آدرس IP",
    "TCP Port": "پورت TCP",
    "Version": "نسخه",
    "Edition": "ویرایش",
    "Product Level": "سطح محصول",
    "Is Clustered": "کلاستر شده",
    "Is HADR": "HADR فعال",
    "OS Info": "اطلاعات سیستم‌عامل",
    "CPU Count": "تعداد CPU",
    "Memory GB": "حافظه (گیگابایت)",
    "CU Level": "سطح CU",
    "Build Number": "شماره ساخت",
    "Version Status": "وضعیت نسخه",
}

LOGIN_HEADERS = {
    "Login Name": "نام لاگین",
    "Login Type": "نوع لاگین",
    "Default Database": "پایگاه‌داده پیش‌فرض",
    "Is Disabled": "غیرفعال",
    "Is Policy Checked": "بررسی سیاست",
    "Is Expiration Checked": "بررسی انقضا",
    "Create Date": "تاریخ ایجاد",
    "Modify Date": "تاریخ تغییر",
    "Password Last Set": "آخرین تنظیم رمز",
    "Has Sysadmin": "دسترسی Sysadmin",
    "Roles": "نقش‌ها",
}

DATABASE_HEADERS = {
    "Database Name": "نام پایگاه‌داده",
    "Owner": "مالک",
    "Compatibility Level": "سطح سازگاری",
    "Recovery Model": "مدل بازیابی",
    "Collation": "ترتیب‌بندی",
    "Size MB": "حجم (مگابایت)",
    "Data Size": "حجم داده",
    "Log Size": "حجم لاگ",
    "Is Read Only": "فقط خواندنی",
    "Is Encrypted": "رمزنگاری شده",
    "Last Backup": "آخرین پشتیبان",
}

SERVICE_HEADERS = {
    "Service Name": "نام سرویس",
    "Display Name": "نام نمایشی",
    "Service Account": "حساب سرویس",
    "Start Mode": "حالت شروع",
    "Current State": "وضعیت فعلی",
    "Expected Account": "حساب مورد انتظار",
    "Account Risk": "ریسک حساب",
}

CONFIG_HEADERS = {
    "Setting Name": "نام تنظیم",
    "Current Value": "مقدار فعلی",
    "Expected Value": "مقدار مورد انتظار",
    "Min Value": "حداقل مقدار",
    "Max Value": "حداکثر مقدار",
    "Is Dynamic": "پویا",
    "Requires Restart": "نیاز به ریستارت",
}

ACTION_HEADERS = {
    "Action ID": "شناسه اقدام",
    "Finding": "یافته",
    "Risk Level": "سطح ریسک",
    "Change Description": "توضیح تغییر",
    "Change Type": "نوع تغییر",
    "Detected Date": "تاریخ شناسایی",
}

# Aggregate all headers
ALL_HEADERS = {
    **COMMON_HEADERS,
    **INSTANCE_HEADERS,
    **LOGIN_HEADERS,
    **DATABASE_HEADERS,
    **SERVICE_HEADERS,
    **CONFIG_HEADERS,
    **ACTION_HEADERS,
}
