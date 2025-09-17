import pytest
from datetime import datetime, timedelta

from app.models.communication import (
    Message,
    Notification,
    CallLog,
    EmailTemplate,
    CommunicationPreference,
    BulkCommunication,
)
from app.schemas.base import NotificationType, Priority


def test_message_mark_read_archive_and_overdue():
    msg = Message(
        sender_id=1,
        recipient_id=2,
        content="Hello",
        requires_response=True,
        response_deadline=datetime.utcnow() - timedelta(minutes=1),
    )

    # Overdue before read
    assert msg.is_overdue is True

    # Mark as read clears overdue
    msg.mark_as_read()
    assert msg.is_read is True
    assert msg.read_at is not None
    assert msg.is_overdue is False

    # Archive sets archived flags
    msg.archive()
    assert msg.is_archived is True
    assert msg.archived_at is not None


def test_notification_flow_and_channels():
    notif = Notification(
        user_id=1,
        title="Test",
        message="Body",
        notification_type=NotificationType.SYSTEM,
        send_email=True,
        send_sms=False,
        send_push=True,
        email_sent=False,
        push_sent=True,
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )

    channels = notif.delivery_status
    assert 'email_pending' in channels
    assert 'push' in channels

    # Expired
    assert notif.is_expired is True

    # Mark read
    notif.mark_as_read()
    assert notif.is_read is True
    assert notif.read_at is not None

    # Dismiss
    notif.dismiss()
    assert notif.is_dismissed is True
    assert notif.dismissed_at is not None


def test_calllog_displays():
    call = CallLog(
        caller_id=1,
        phone_number="123",
        call_type="outbound",
        call_direction="outgoing",
        started_at=datetime.utcnow(),
        duration_seconds=125,
        status="completed",
        cost_cents=1234,
    )
    assert call.duration_display == "02:05"
    assert call.cost_display == "$12.34"


def test_emailtemplate_render():
    tpl = EmailTemplate(
        name="Greeting",
        template_type="general",
        subject="Hi {{name}}",
        html_content="<p>Hello {{name}}</p>",
        text_content="Plain {{name}}",
    )
    rendered = tpl.render({"name": "Alice"})
    assert rendered["subject"] == "Hi Alice"
    assert rendered["html_content"] == "<p>Hello Alice</p>"
    assert rendered["text_content"] == "Plain Alice"


def test_communication_preferences():
    pref = CommunicationPreference(
        user_id=1,
        email_notifications=True,
        email_marketing=False,
        sms_notifications=True,
        sms_urgent_only=True,
    )
    # Marketing disabled
    assert pref.can_send_email("marketing") is False
    # Unknown type defaults to True
    assert pref.can_send_email("other") is True

    # SMS only urgent
    assert pref.can_send_sms(is_urgent=False) is False
    assert pref.can_send_sms(is_urgent=True) is True


def test_bulk_communication_rates_and_lifecycle():
    bc = BulkCommunication(
        name="Campaign",
        campaign_type="email",
        status="scheduled",
        sent_count=100,
        delivered_count=80,
        opened_count=40,
        clicked_count=10,
    )

    assert bc.delivery_rate == 80
    assert bc.open_rate == 50  # 40 / 80
    assert bc.click_rate == 25  # 10 / 40

    # Start campaign
    bc.start_campaign()
    assert bc.status == "sending"
    assert bc.started_at is not None

    # Complete campaign
    bc.complete_campaign()
    assert bc.status == "sent"
    assert bc.completed_at is not None
