from rest_framework import serializers
from .models import (
    DailySummary, Meeting, Transcript, NoteReference, WordDocument, Recording,
    ActionItem,
)


class TranscriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcript
        fields = [
            'id', 'content_vtt', 'content_plain', 'created_at',
        ]


class MeetingSerializer(serializers.ModelSerializer):
    transcripts = TranscriptSerializer(many=True, read_only=True)

    class Meta:
        model = Meeting
        fields = [
            'id', 'graph_event_id', 'subject', 'start_time', 'end_time',
            'organizer_name', 'organizer_email', 'attendees_json',
            'body_preview', 'location', 'is_online_meeting',
            'online_meeting_url', 'web_link', 'transcripts',
        ]


class NoteReferenceSerializer(serializers.ModelSerializer):
    daily_summary = serializers.SerializerMethodField()

    class Meta:
        model = NoteReference
        fields = [
            'id', 'notebook_name', 'section_name', 'page_title',
            'content_snippet', 'content_text',
            'changes_summary', 'change_type', 'web_url', 'last_modified',
            'daily_summary',
        ]

    def get_daily_summary(self, obj):
        if obj.daily_summary_id:
            return {'date': str(obj.daily_summary.date)}
        return None


class WordDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WordDocument
        fields = [
            'id', 'file_name', 'file_path', 'content_text',
            'modified_at', 'size_bytes',
        ]


class RecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recording
        fields = [
            'id', 'file_name', 'file_path', 'file_type',
            'transcript_text', 'modified_at', 'size_bytes',
        ]


class ActionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionItem
        fields = [
            'id', 'daily_summary', 'meeting', 'text', 'completed',
            'priority', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DailySummaryListSerializer(serializers.ModelSerializer):
    meeting_count = serializers.IntegerField(
        source='meetings.count', read_only=True
    )
    note_count = serializers.IntegerField(
        source='note_references.count', read_only=True
    )
    doc_count = serializers.IntegerField(
        source='word_documents.count', read_only=True
    )
    recording_count = serializers.IntegerField(
        source='recordings.count', read_only=True
    )

    class Meta:
        model = DailySummary
        fields = [
            'id', 'date', 'status', 'summary_text', 'notes',
            'created_at', 'updated_at', 'meeting_count',
            'note_count', 'doc_count', 'recording_count',
        ]


class DailySummaryDetailSerializer(serializers.ModelSerializer):
    meetings = MeetingSerializer(many=True, read_only=True)
    note_references = NoteReferenceSerializer(many=True, read_only=True)
    word_documents = WordDocumentSerializer(many=True, read_only=True)
    recordings = RecordingSerializer(many=True, read_only=True)
    action_items = ActionItemSerializer(many=True, read_only=True)

    class Meta:
        model = DailySummary
        fields = [
            'id', 'date', 'status', 'summary_text', 'notes',
            'error_message', 'created_at', 'updated_at',
            'meetings', 'note_references', 'word_documents',
            'recordings', 'action_items',
        ]
