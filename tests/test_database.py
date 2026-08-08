import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Recipient, OptOut, Campaign

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_database_recipient_creation(db_session):
    rec = Recipient(
        name="Test User",
        phone="919876543210",
        phone_raw="9876543210",
        email="test@q9x.org",
        consent=True
    )
    db_session.add(rec)
    db_session.commit()

    saved = db_session.query(Recipient).filter_by(phone="919876543210").first()
    assert saved is not None
    assert saved.name == "Test User"

def test_opt_out_unique_constraint(db_session):
    opt1 = OptOut(phone="919876543210", source="manual")
    db_session.add(opt1)
    db_session.commit()

    opt2 = OptOut(phone="919876543210", source="manual")
    db_session.add(opt2)
    with pytest.raises(Exception):
        db_session.commit()
