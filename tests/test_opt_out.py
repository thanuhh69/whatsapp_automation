import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import OptOut, InboundMessage
from backend.services.whatsapp_inbox import InboxPoller

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_auto_opt_out_keyword_matching(db_session):
    # Test 'STOP' inbound message
    created1 = InboxPoller.process_inbound_message(db_session, "9876543210", "STOP")
    assert created1 is True

    opt = db_session.query(OptOut).filter_by(phone="919876543210").first()
    assert opt is not None
    assert opt.source == "auto_keyword"
    assert "STOP" in opt.reason

    # Test non-opt-out inbound message
    created2 = InboxPoller.process_inbound_message(db_session, "9876543211", "Hello team")
    assert created2 is False

    opt2 = db_session.query(OptOut).filter_by(phone="919876543211").first()
    assert opt2 is None

    inbound = db_session.query(InboundMessage).filter_by(phone="919876543211").first()
    assert inbound is not None
    assert inbound.body == "Hello team"
