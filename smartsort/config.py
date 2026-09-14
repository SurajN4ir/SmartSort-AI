"""Static configuration: category rules and application constants."""

from pathlib import Path

APP_NAME = "SmartSort"
APP_DATA_DIR = Path.home() / ".smartsort"
DATABASE_PATH = APP_DATA_DIR / "smartsort.db"

# Extension -> category rules. Order does not matter; lookups are by extension.
CATEGORY_RULES: dict[str, str] = {
    # Documents
    ".pdf": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".txt": "Documents",
    ".rtf": "Documents",
    ".odt": "Documents",
    ".md": "Documents",
    ".csv": "Spreadsheets",
    ".xls": "Spreadsheets",
    ".xlsx": "Spreadsheets",
    ".ods": "Spreadsheets",
    ".ppt": "Presentations",
    ".pptx": "Presentations",
    ".odp": "Presentations",
    # Images
    ".jpg": "Images",
    ".jpeg": "Images",
    ".png": "Images",
    ".gif": "Images",
    ".bmp": "Images",
    ".svg": "Images",
    ".webp": "Images",
    ".heic": "Images",
    ".tiff": "Images",
    ".ico": "Images",
    # Videos
    ".mp4": "Videos",
    ".mkv": "Videos",
    ".avi": "Videos",
    ".mov": "Videos",
    ".wmv": "Videos",
    ".flv": "Videos",
    ".webm": "Videos",
    ".m4v": "Videos",
    # Audio
    ".mp3": "Audio",
    ".wav": "Audio",
    ".flac": "Audio",
    ".aac": "Audio",
    ".ogg": "Audio",
    ".m4a": "Audio",
    ".wma": "Audio",
    # Archives
    ".zip": "Archives",
    ".rar": "Archives",
    ".7z": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".bz2": "Archives",
    ".iso": "Archives",
    # Applications
    ".exe": "Applications",
    ".msi": "Applications",
    ".apk": "Applications",
    ".dmg": "Applications",
    ".appimage": "Applications",
    ".deb": "Applications",
    # Code
    ".py": "Code",
    ".js": "Code",
    ".ts": "Code",
    ".tsx": "Code",
    ".jsx": "Code",
    ".java": "Code",
    ".c": "Code",
    ".cpp": "Code",
    ".h": "Code",
    ".cs": "Code",
    ".go": "Code",
    ".rs": "Code",
    ".rb": "Code",
    ".php": "Code",
    ".html": "Code",
    ".css": "Code",
    ".json": "Code",
    ".sh": "Code",
    ".ps1": "Code",
    ".sql": "Code",
    # Ebooks
    ".epub": "Ebooks",
    ".mobi": "Ebooks",
    ".azw3": "Ebooks",
    # Fonts
    ".ttf": "Fonts",
    ".otf": "Fonts",
    ".woff": "Fonts",
    ".woff2": "Fonts",
}

DEFAULT_CATEGORY = "Others"

# Ordered for display: known categories first, "Others" always last.
CATEGORY_ORDER = [
    "Documents",
    "Spreadsheets",
    "Presentations",
    "Images",
    "Videos",
    "Audio",
    "Archives",
    "Applications",
    "Code",
    "Ebooks",
    "Fonts",
    DEFAULT_CATEGORY,
]

CATEGORY_ICONS = {
    "Documents": "📄",
    "Spreadsheets": "📊",
    "Presentations": "📽",
    "Images": "🖼",
    "Videos": "🎬",
    "Audio": "🎵",
    "Archives": "🗜",
    "Applications": "💽",
    "Code": "💻",
    "Ebooks": "📚",
    "Fonts": "🔤",
    "Others": "📦",
}
