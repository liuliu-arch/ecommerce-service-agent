"""第 41 课后端入口。"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from course_runtime.course_logging import configure_course_logging, course_access_log_enabled
configure_course_logging(Path(__file__).resolve().parent)

import uvicorn

from api.routes import app


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, access_log=course_access_log_enabled(), log_config=None, reload=True)
