import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class Recipient(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    phone_raw = Column(String, nullable=False)
    email = Column(String, nullable=True)
    consent = Column(Boolean, default=True, nullable=False)
    registration_date = Column(DateTime, nullable=True)
    status = Column(String, default="ACTIVE", nullable=False) # ACTIVE, DEACTIVATED
    last_synced_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    campaign_messages = relationship("CampaignMessage", back_populates="recipient", cascade="all, delete-orphan")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    message_template = Column(Text, nullable=False)
    status = Column(String, default="DRAFT", nullable=False) # DRAFT, PENDING, SENDING, COMPLETED, PAUSED, STOPPED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    is_test_mode = Column(Boolean, default=True)

    messages = relationship("CampaignMessage", back_populates="campaign", cascade="all, delete-orphan")


class CampaignMessage(Base):
    __tablename__ = "campaign_messages"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False)
    rendered_message = Column(Text, nullable=False)
    status = Column(String, default="PENDING", nullable=False) # PENDING, SENDING, SENT, FAILED, SKIPPED, OPTED_OUT
    error = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    campaign = relationship("Campaign", back_populates="messages")
    recipient = relationship("Recipient", back_populates="campaign_messages")


class OptOut(Base):
    __tablename__ = "opt_outs"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    reason = Column(String, nullable=True)
    source = Column(String, nullable=False) # manual | auto_keyword
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class InboundMessage(Base):
    __tablename__ = "inbound_messages"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    received_at = Column(DateTime, default=datetime.datetime.utcnow)
    matched_keyword = Column(String, nullable=True)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=False)
