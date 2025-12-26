"""
Dropdown and status value translations.

Maps dropdown options and status icons to Persian.
Icons (✓, ❌, ⏳) are kept as-is since they're universal.
"""

# Status values (for Result/Status columns)
STATUS_VALUES = {
    "PASS": "تأیید",
    "FAIL": "رد",
    "WARN": "هشدار",
    "INFO": "اطلاعات",
    "N/A": "نامشخص",
    "OK": "تأیید",
    "ERROR": "خطا",
}

# Risk levels
RISK_LEVELS = {
    "Low": "کم",
    "Medium": "متوسط",
    "High": "بالا",
    "Critical": "بحرانی",
}

# Change types (Action Log)
CHANGE_TYPES = {
    "Fixed": "رفع شده",
    "Regression": "بازگشت",
    "New": "جدید",
    "Open": "باز",
    "Closed": "بسته",
    "Exception": "استثنا",
    "Pending": "در انتظار",
}

# Change type with icons (as displayed in dropdowns)
CHANGE_TYPE_OPTIONS = {
    "⏳ Open": "⏳ باز",
    "✓ Fixed": "✓ رفع شده",
    "✓ Exception": "✓ استثنا",
    "❌ Regression": "❌ بازگشت",
    "✓ Closed": "✓ بسته",
}

# Action categories
ACTION_CATEGORIES = {
    "SA Account": "حساب SA",
    "Configuration": "پیکربندی",
    "Backup": "پشتیبان",
    "Login": "لاگین",
    "Permissions": "مجوزها",
    "Service": "سرویس",
    "Database": "پایگاه‌داده",
    "Other": "سایر",
}

# Review status
REVIEW_STATUS = {
    "Pending": "در انتظار",
    "Reviewed": "بررسی شده",
    "Exception": "استثنا",
    "Approved": "تأیید شده",
    "Rejected": "رد شده",
}

# Boolean display
BOOLEAN_VALUES = {
    "Yes": "بله",
    "No": "خیر",
    "True": "بله",
    "False": "خیر",
    "Enabled": "فعال",
    "Disabled": "غیرفعال",
}
