from sqlalchemy import Column, Integer, Text, Numeric, Date
from database import Base

class Tent(Base):
    __tablename__ = "tents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    brand = Column(Text)
    price = Column(Integer)
    capacity = Column(Numeric)
    weight_kg = Column(Numeric)
    size_w = Column(Numeric)
    size_d = Column(Numeric)
    size_h = Column(Numeric)
    pack_w = Column(Numeric)
    pack_d = Column(Numeric)
    pack_h = Column(Numeric)
    material = Column(Text)
    purchase_date = Column(Date)
