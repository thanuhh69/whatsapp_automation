import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Recipient
from backend.services.google_sheets import sync_google_sheets

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_sync_idempotency_and_deduplication(db_session):
    mock_sheet_rows = [
        {
            "Name": "Alice Smith",
            "Mobile": "9876543210",
            "Email": "alice@q9x.org",
            "WhatsApp Consent": "YES",
            "Registration Date": "2026-01-01 10:00:00"
        },
        {
            "Name": "Alice Smith Updated",
            "Mobile": "+91 98765 43210", # Same phone normalized (919876543210)
            "Email": "alice.updated@q9x.org",
            "WhatsApp Consent": "YES",
            "Registration Date": "2026-01-02 10:00:00" # Newer date
        },
        {
            "Name": "Bob Jones",
            "Mobile": "9876543211",
            "Email": "bob@q9x.org",
            "WhatsApp Consent": "NO", # No consent -> ignored
            "Registration Date": "2026-01-01 10:00:00"
        }
    ]

    # First sync run
    report1 = sync_google_sheets(db_session, rows_override=mock_sheet_rows)
    assert report1["added"] == 1
    assert report1["ignored"] == 1
    assert report1["invalid"] == 0

    recs = db_session.query(Recipient).all()
    assert len(recs) == 1
    assert recs[0].name == "Alice Smith Updated"
    assert recs[0].email == "alice.updated@q9x.org"

    # Second sync run with unchanged sheet data -> IDEMPOTENCY CHECK
    report2 = sync_google_sheets(db_session, rows_override=mock_sheet_rows)
    assert report2["added"] == 0
    assert report2["updated"] == 0
    assert report2["ignored"] == 1

    recs_after = db_session.query(Recipient).all()
    assert len(recs_after) == 1
