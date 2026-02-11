import uuid
from django.db import models


class DailySummary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default='')
    summary_text = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('collecting', 'Collecting Data'),
            ('complete', 'Complete'),
            ('error', 'Error'),
        ],
        default='pending',
    )
    error_message = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Daily Summaries'

    def __str__(self):
        return f"Summary for {self.date}"


class Meeting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    daily_summary = models.ForeignKey(
        DailySummary, on_delete=models.CASCADE, related_name='meetings'
    )
    graph_event_id = models.CharField(max_length=512, blank=True)
    subject = models.CharField(max_length=500)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    organizer_name = models.CharField(max_length=255, blank=True)
    organizer_email = models.EmailField(blank=True)
    attendees_json = models.JSONField(default=list)
    body_preview = models.TextField(blank=True)
    location = models.CharField(max_length=500, blank=True)
    is_online_meeting = models.BooleanField(default=False)
    online_meeting_url = models.URLField(max_length=2000, blank=True)
    web_link = models.URLField(max_length=2000, blank=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.subject} ({self.start_time})"


class Transcript(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name='transcripts'
    )
    transcript_graph_id = models.CharField(max_length=512, blank=True)
    content_vtt = models.TextField(blank=True)
    content_plain = models.TextField(blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Transcript for {self.meeting.subject}"


class NoteReference(models.Model):
    CHANGE_TYPE_CHOICES = [
        ('new', 'New'),
        ('updated', 'Updated'),
        ('unchanged', 'Unchanged'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    daily_summary = models.ForeignKey(
        DailySummary, on_delete=models.CASCADE, related_name='note_references'
    )
    notebook_name = models.CharField(max_length=500, blank=True)
    section_name = models.CharField(max_length=500, blank=True)
    page_title = models.CharField(max_length=500)
    page_graph_id = models.CharField(max_length=512, blank=True)
    content_snippet = models.TextField(blank=True)
    content_text = models.TextField(blank=True, default='')
    changes_summary = models.TextField(blank=True, default='')
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        default='new',
    )
    web_url = models.URLField(max_length=2000, blank=True)
    last_modified = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-last_modified']

    def __str__(self):
        return f"Note: {self.page_title}"


class WordDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    daily_summary = models.ForeignKey(
        DailySummary, on_delete=models.CASCADE, related_name='word_documents'
    )
    file_name = models.CharField(max_length=500)
    file_path = models.CharField(max_length=2000)
    content_text = models.TextField(blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    size_bytes = models.IntegerField(default=0)

    class Meta:
        ordering = ['-modified_at']

    def __str__(self):
        return f"Doc: {self.file_name}"


class Recording(models.Model):
    FILE_TYPE_CHOICES = [
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('transcript', 'Transcript'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    daily_summary = models.ForeignKey(
        DailySummary, on_delete=models.CASCADE, related_name='recordings'
    )
    file_name = models.CharField(max_length=500)
    file_path = models.CharField(max_length=2000)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    transcript_text = models.TextField(blank=True, default='')
    modified_at = models.DateTimeField(null=True, blank=True)
    size_bytes = models.IntegerField(default=0)

    class Meta:
        ordering = ['-modified_at']

    def __str__(self):
        return f"Recording: {self.file_name} ({self.file_type})"
