"""TrustCheck 도메인 모델 (러프 MVP).

플랫폼 전용 사용자 계정을 별도로 둔다(Django auth.User 와 분리).
역할: 발주자(client) / 전문가(expert) / 관리자(admin).
비밀번호는 Django make_password 로 해시 저장.
"""
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


# ---------------------------------------------------------------------------
# 사용자 / 역할
# ---------------------------------------------------------------------------
class TCUser(models.Model):
    ROLE_CLIENT = 'client'
    ROLE_EXPERT = 'expert'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_CLIENT, '발주자'),
        (ROLE_EXPERT, '전문가'),
        (ROLE_ADMIN, '관리자'),
    ]
    # 전문가 세부 유형
    EXPERT_PM = 'pm'
    EXPERT_LAWYER = 'lawyer'
    EXPERT_TYPE_CHOICES = [
        ('', '-'),
        (EXPERT_PM, 'IT PM'),
        (EXPERT_LAWYER, '변호사'),
    ]

    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    name = models.CharField(max_length=64)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    expert_type = models.CharField(max_length=16, choices=EXPERT_TYPE_CHOICES, blank=True, default='')

    # 전문가 승인 상태 (client/admin 은 항상 True 취급)
    is_approved = models.BooleanField(default=False)
    bio = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def set_password(self, raw):
        self.password = make_password(raw)

    def check_password(self, raw):
        return check_password(raw, self.password)

    @property
    def is_expert(self):
        return self.role == self.ROLE_EXPERT

    @property
    def approved(self):
        return self.role in (self.ROLE_CLIENT, self.ROLE_ADMIN) or self.is_approved

    def __str__(self):
        return f'{self.name}({self.get_role_display()})'


# ---------------------------------------------------------------------------
# 상담 게시글
# ---------------------------------------------------------------------------
class ConsultPost(models.Model):
    FIELD_CHOICES = [
        ('pm', 'IT PM (기획·견적)'),
        ('lawyer', '법률 (계약)'),
        ('both', '융합 (기술+법률)'),
        ('dispute', '분쟁 분석'),
    ]
    STATUS_OPEN = 'open'
    STATUS_MATCHED = 'matched'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, '모집중'),
        (STATUS_MATCHED, '매칭됨'),
        (STATUS_CLOSED, '종료'),
    ]

    author = models.ForeignKey(TCUser, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    field = models.CharField(max_length=16, choices=FIELD_CHOICES, default='pm')
    situation = models.TextField(help_text='상황 설명')
    budget = models.CharField(max_length=64, blank=True, default='', help_text='금액 규모')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


# ---------------------------------------------------------------------------
# 역매칭 — 전문가 어필 메시지
# ---------------------------------------------------------------------------
class ExpertMessage(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, '대기'),
        (STATUS_ACCEPTED, '수락'),
        (STATUS_REJECTED, '거절'),
    ]

    post = models.ForeignKey(ConsultPost, on_delete=models.CASCADE, related_name='appeals')
    expert = models.ForeignKey(TCUser, on_delete=models.CASCADE, related_name='appeals')
    message = models.TextField(help_text='어필 메시지')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('post', 'expert')]  # 중복 어필 방지

    def __str__(self):
        return f'{self.expert.name} → {self.post.title}'


# ---------------------------------------------------------------------------
# 채팅방 + 메시지 (15분 무료 타이머)
# ---------------------------------------------------------------------------
class ChatRoom(models.Model):
    post = models.ForeignKey(ConsultPost, on_delete=models.CASCADE, related_name='rooms')
    client = models.ForeignKey(TCUser, on_delete=models.CASCADE, related_name='client_rooms')
    expert = models.ForeignKey(TCUser, on_delete=models.CASCADE, related_name='expert_rooms')
    # 무료 채팅 타이머 (서버 기준)
    started_at = models.DateTimeField(auto_now_add=True)
    free_seconds = models.PositiveIntegerField(default=15 * 60)  # 15분
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'Room#{self.pk} {self.client.name}·{self.expert.name}'


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(TCUser, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='trustcheck/chat/', blank=True, null=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


# ---------------------------------------------------------------------------
# 상품 / 케이스 / 리포트
# ---------------------------------------------------------------------------
class Product(models.Model):
    """A/B/C/Premium 상품."""
    code = models.CharField(max_length=16, unique=True)  # A, B, C, PREMIUM
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True, default='')
    price = models.PositiveIntegerField(default=0)
    is_sequential = models.BooleanField(default=False)  # C형 순차(PM→변호사)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.code} · {self.name}'


class Case(models.Model):
    """결제 후 생성되는 검토 케이스."""
    STAGE_PAID = 'paid'
    STAGE_MATERIALS = 'materials'       # 자료 전달됨
    STAGE_REVIEWING = 'reviewing'       # 검토중
    STAGE_MEETING = 'meeting'           # 화상 상담 예정
    STAGE_PM_DONE = 'pm_done'           # C형: PM 완료 → 변호사 대기
    STAGE_REPORTED = 'reported'         # 리포트 발행
    STAGE_DONE = 'done'
    STAGE_CHOICES = [
        (STAGE_PAID, '결제완료'),
        (STAGE_MATERIALS, '자료전달'),
        (STAGE_REVIEWING, '검토중'),
        (STAGE_MEETING, '화상상담예정'),
        (STAGE_PM_DONE, 'PM완료(변호사대기)'),
        (STAGE_REPORTED, '리포트발행'),
        (STAGE_DONE, '완료'),
    ]

    client = models.ForeignKey(TCUser, on_delete=models.CASCADE, related_name='cases')
    expert = models.ForeignKey(TCUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='expert_cases')
    lawyer = models.ForeignKey(TCUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='lawyer_cases')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='cases')
    post = models.ForeignKey(ConsultPost, on_delete=models.SET_NULL, null=True, blank=True, related_name='cases')

    stage = models.CharField(max_length=16, choices=STAGE_CHOICES, default=STAGE_PAID)
    inquiry = models.TextField(blank=True, default='', help_text='질의사항')
    meet_url = models.URLField(blank=True, default='')
    meet_at = models.DateTimeField(null=True, blank=True)
    paid_amount = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Case#{self.pk} {self.product.code} {self.get_stage_display()}'


class CaseFile(models.Model):
    """케이스 첨부 자료 (계약서/기획서/견적서 등)."""
    KIND_CHOICES = [
        ('contract', '계약서'),
        ('plan', '기획서'),
        ('quote', '견적서'),
        ('etc', '기타'),
    ]
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='files')
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default='etc')
    file = models.FileField(upload_to='trustcheck/cases/')
    uploaded_by = models.ForeignKey(TCUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Report(models.Model):
    """검토 리포트 (PM/변호사 각각 작성 가능)."""
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='reports')
    author = models.ForeignKey(TCUser, on_delete=models.SET_NULL, null=True, related_name='reports')
    title = models.CharField(max_length=200)
    # 신호등: green/amber/red 요약
    summary = models.TextField(blank=True, default='')
    body = models.TextField(blank=True, default='')
    file = models.FileField(upload_to='trustcheck/reports/', blank=True, null=True)
    signal = models.CharField(
        max_length=8,
        choices=[('green', '안전'), ('amber', '주의'), ('red', '위험')],
        blank=True, default='',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
