import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from api.db import Base


class UserRole(str, enum.Enum):
    student = "student"
    instructor = "instructor"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    teams = relationship("TeamMember", back_populates="user")


class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    join_code = Column(String, unique=True, nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    members = relationship("TeamMember", back_populates="team")
    rounds = relationship("Round", back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("user_id", "team_id", name="uq_member_team"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="teams")
    team = relationship("Team", back_populates="members")


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    config_json = Column(JSON, nullable=False, default={})
    created_by = Column(String, ForeignKey("users.id"), nullable=False)


class Round(Base):
    __tablename__ = "rounds"
    __table_args__ = (UniqueConstraint("team_id", "number", name="uq_round_team_number"),)

    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    scenario_id = Column(String, nullable=True)
    number = Column(Integer, nullable=False)
    seed = Column(Integer, nullable=False)
    status = Column(String, default="open", nullable=False)
    constraints_json = Column(JSON, nullable=False, default={})
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at: Optional[datetime] = Column(DateTime, nullable=True)

    team = relationship("Team", back_populates="rounds")
    decisions = relationship("Decision", back_populates="round")
    results = relationship("Result", back_populates="round")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True)
    round_id = Column(String, ForeignKey("rounds.id"), nullable=False, index=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    payload_json = Column(JSON, nullable=False, default={})
    status = Column(String, default="submitted", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    round = relationship("Round", back_populates="decisions")


class Result(Base):
    __tablename__ = "results"

    id = Column(String, primary_key=True)
    round_id = Column(String, ForeignKey("rounds.id"), nullable=False, index=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False, index=True)
    payload_json = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    round = relationship("Round", back_populates="results")


class Leaderboard(Base):
    __tablename__ = "leaderboard"

    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"), unique=True, nullable=False)
    total_profit = Column(Float, default=0)
    avg_service = Column(Float, default=0)
    emissions = Column(Float, default=0)
    reputation = Column(Float, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)
