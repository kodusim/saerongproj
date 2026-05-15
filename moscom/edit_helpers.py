"""수정 이력 기록 헬퍼."""
from .models import EditLog


def log_change(table, row_id, field, old_value, new_value, edited_by=''):
    """단일 필드 변경 1줄을 EditLog에 기록."""
    if str(old_value) == str(new_value):
        return None
    return EditLog.objects.create(
        table=table[:50], row_id=row_id, field=field[:50],
        old_value=str(old_value)[:8000], new_value=str(new_value)[:8000],
        edited_by=(edited_by or '')[:50],
    )
