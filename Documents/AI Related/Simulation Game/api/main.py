import os
import random
import string
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeSerializer, BadSignature
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from optimizer.engine import evaluate_decision
from api import models
from api.db import get_db, init_db


class User(BaseModel):
    id: str
    email: str
    role: str = "student"


class AuthRequest(BaseModel):
    email: str
    password: str
    role: str = "student"


class AuthResponse(BaseModel):
    token: str
    user: User


class TeamCreateRequest(BaseModel):
    name: str


class TeamJoinRequest(BaseModel):
    code: str


class Team(BaseModel):
    id: str
    name: str
    join_code: str
    created_by: str
    members: List[str] = Field(default_factory=list)


class ConstraintsSnapshot(BaseModel):
    forecast_range: Dict[str, List[int]]
    capacity: Dict[str, int]
    costs: Dict[str, Dict[str, float]]
    service_targets: Dict[str, float]
    carbon_cap: int
    cash_on_hand: float


class PlantDecision(BaseModel):
    plant_id: str
    production_qty: Dict[str, int] = Field(default_factory=dict)
    overtime_hours: Optional[int] = 0
    outsourcing_qty: Dict[str, int] = Field(default_factory=dict)
    allocation_priority: List[str] = Field(default_factory=list)


class RoutingOverride(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    sku: str
    ratio: float


class DecisionPayload(BaseModel):
    team_id: str
    round: int
    scenario_id: str
    seed: int
    plants: List[PlantDecision]
    inventory_policy: Dict[str, Dict[str, int]]
    transport_priorities: List[str] = Field(default_factory=list)
    routing_overrides: List[RoutingOverride] = Field(default_factory=list)
    capacity_rules: Dict[str, str] = Field(default_factory=dict)
    constraints_snapshot: ConstraintsSnapshot


class RoundState(BaseModel):
    round: int
    scenario_id: str
    seed: int
    constraints: ConstraintsSnapshot
    status: str = "open"
    industry_news: List[str] = Field(default_factory=list)
    theory: Optional[str] = None
    theory_description: Optional[str] = None


class ResultPayload(BaseModel):
    team_id: str
    round: int
    feasible: bool
    messages: List[Dict[str, str]]
    kpis: Dict[str, object]
    usage: Dict[str, object]
    disruption: Dict[str, object]
    next_state_seed: int


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
ALLOWED_ORIGINS = os.environ.get("ALLOW_ORIGINS", "http://localhost:8501").split(",")

serializer = URLSafeSerializer(SECRET_KEY, salt="auth")

app = FastAPI(title="Adaptive Operations Lab API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


def _generate_id(prefix: str = "id") -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{suffix}"


def _generate_join_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=4))


def _default_constraints() -> ConstraintsSnapshot:
    return ConstraintsSnapshot(
        forecast_range={"SKU-A": [450, 650], "SKU-B": [250, 380]},
        capacity={"P1": 900},
        costs={
            "unit_cost": {"SKU-A": 12, "SKU-B": 9},
            "overtime_cost_per_hour": {"_": 35},
            "outsourcing_cost": {"SKU-A": 20, "SKU-B": 16},
        },
        service_targets={"SKU-A": 0.95, "SKU-B": 0.9},
        carbon_cap=1200,
        cash_on_hand=75000,
    )


def _scenario_for(round_number: int, team_seed: int = 0) -> Dict[str, Any]:
    """Generate scenario with team-specific variations based on seed."""
    rng = random.Random(team_seed + round_number * 1000)
    
    # Round 1: EUT - Each team gets different probability/payoff combinations
    supplier_reliability = rng.choice([55, 60, 65, 70])  # % on-time delivery
    high_demand_prob = rng.choice([45, 50, 55, 60])  # % chance high demand
    high_payoff = rng.choice([7500, 8000, 8500, 9000])
    low_payoff = rng.choice([1500, 2000, 2500, 3000])
    conservative_payoff = rng.choice([3800, 4000, 4200, 4500])
    
    # Calculate which option is actually optimal for this team
    high_ev = (high_demand_prob/100) * high_payoff + (1 - high_demand_prob/100) * low_payoff
    optimal_choice = "High-volume" if high_ev > conservative_payoff else "Conservative"
    
    scenarios: Dict[int, Dict[str, Any]] = {
        1: {
            "scenario_id": "S1-EUT",
            "theory": "Expected Utility Theory",
            "theory_description": "Choose the option with the highest expected utility by computing probability × utility for each outcome.",
            "optimal_strategy": optimal_choice,
            "constraints": ConstraintsSnapshot(
                forecast_range={"SKU-A": [450, 650], "SKU-B": [250, 380]},
                capacity={"P1": 900},
                costs={
                    "unit_cost": {"SKU-A": 12, "SKU-B": 9},
                    "overtime_cost_per_hour": {"_": 35},
                    "outsourcing_cost": {"SKU-A": 20, "SKU-B": 16},
                },
                service_targets={"SKU-A": 0.95, "SKU-B": 0.9},
                carbon_cap=1200,
                cash_on_hand=75000,
            ).model_dump(),
            "industry_news": [
                "THEORY: Expected Utility Theory - Evaluate choices under uncertainty",
                f"Supplier has {supplier_reliability}% chance of delivering on time, {100-supplier_reliability}% chance of 2-week delay",
                f"High-volume production yields {high_payoff} profit if demand is high ({high_demand_prob}% chance), {low_payoff} if low",
                f"Conservative production yields {conservative_payoff} profit regardless of demand",
                f"Calculate expected values to determine optimal strategy (hint: compute probability × payoff for each outcome)",
            ],
        },
        2: {
            "scenario_id": "S2-PT",
            "theory": "Prospect Theory",
            "theory_description": "Losses loom larger than gains. Avoid excessive loss aversion that prevents optimal decisions.",
            "optimal_strategy": "Risk-taking (Option B)",
            "constraints": ConstraintsSnapshot(
                forecast_range={"SKU-A": [500, 750], "SKU-B": [300, 450], "SKU-C": [180, 260]},
                capacity={"P1": 950, "P2": 600},
                costs={
                    "unit_cost": {"SKU-A": 12, "SKU-B": 9, "SKU-C": 7},
                    "overtime_cost_per_hour": {"_": 42},
                    "outsourcing_cost": {"SKU-A": 22, "SKU-B": 17, "SKU-C": 12},
                },
                service_targets={"SKU-A": 0.96, "SKU-B": 0.92, "SKU-C": 0.9},
                carbon_cap=1100,
                cash_on_hand=70000,
            ).model_dump(),
            "industry_news": [
                "THEORY: Prospect Theory - Recognize loss aversion bias",
                f"Option A: Guaranteed to avoid {rng.choice([4500, 5000, 5500])} loss by maintaining excess inventory (costs {rng.choice([2800, 3000, 3200])})",
                f"Option B: {rng.choice([45, 50, 55])}% chance of {rng.choice([5500, 6000, 6500])} gain, {rng.choice([45, 50, 55])}% chance of {rng.choice([1800, 2000, 2200])} loss",
                "Loss-averse managers often choose the 'safe' option, but calculate the expected value of both",
                "Your decision framing affects choices: teams avoiding losses excessively will underperform over multiple rounds",
            ],
        },
        3: {
            "scenario_id": "S3-Bayesian",
            "theory": "Bayesian Updating",
            "theory_description": "Update beliefs continuously based on new evidence to improve forecasts and decisions.",
            "optimal_strategy": "Bayesian updating",
            "constraints": ConstraintsSnapshot(
                forecast_range={"SKU-A": [400, 600], "SKU-B": [220, 360], "SKU-C": [150, 240]},
                capacity={"P1": 800, "P2": 500},
                costs={
                    "unit_cost": {"SKU-A": 11, "SKU-B": 8, "SKU-C": 6},
                    "overtime_cost_per_hour": {"_": 38},
                    "outsourcing_cost": {"SKU-A": 20, "SKU-B": 15, "SKU-C": 11},
                },
                service_targets={"SKU-A": 0.95, "SKU-B": 0.93, "SKU-C": 0.9},
                carbon_cap=1000,
                cash_on_hand=72000,
            ).model_dump(),
            "industry_news": [
                "THEORY: Bayesian Updating - Revise forecasts with new data",
                f"Initial forecast: {rng.choice([55, 60, 65])}% chance demand will be 'high', {rng.choice([35, 40, 45])}% 'low'",
                f"New signal: Early order data shows {rng.choice([65, 70, 75])}% of indicators point to 'high' demand",
                f"Signal reliability: Historical data shows this signal is {rng.choice([75, 80, 85])}% accurate",
                "Update your prior belief using Bayes' rule: P(High|Signal) = P(Signal|High) × P(High) / P(Signal)",
                "Teams that properly update forecasts will set optimal production levels",
            ],
        },
        4: {
            "scenario_id": "S4-MCDA",
            "theory": "Multi-Criteria Decision Analysis",
            "theory_description": "Balance multiple competing objectives (cost, quality, time, sustainability) systematically.",
            "optimal_strategy": "MCDA weighted scoring",
            "constraints": ConstraintsSnapshot(
                forecast_range={"SKU-A": [520, 780], "SKU-B": [320, 480], "SKU-D": [200, 340]},
                capacity={"P1": 900, "P2": 650},
                costs={
                    "unit_cost": {"SKU-A": 13, "SKU-B": 9, "SKU-D": 10},
                    "overtime_cost_per_hour": {"_": 45},
                    "outsourcing_cost": {"SKU-A": 24, "SKU-B": 18, "SKU-D": 17},
                },
                service_targets={"SKU-A": 0.95, "SKU-B": 0.9, "SKU-D": 0.9},
                carbon_cap=1150,
                cash_on_hand=68000,
            ).model_dump(),
            "industry_news": [
                "THEORY: Multi-Criteria Decision Analysis - Evaluate trade-offs",
                f"Supplier A: Cost ({rng.choice([95, 100, 105])}k), Quality ({rng.choice([6, 7, 8])}/10), Carbon ({rng.choice([750, 800, 850])}kg), Speed ({rng.choice([2, 2.5, 3])} weeks)",
                f"Supplier B: Cost ({rng.choice([125, 130, 135])}k), Quality ({rng.choice([8, 9, 9])}/10), Carbon ({rng.choice([380, 400, 420])}kg), Speed ({rng.choice([3, 3.5, 4])} weeks)",
                f"Supplier C: Cost ({rng.choice([145, 150, 155])}k), Quality ({rng.choice([9, 9, 10])}/10), Carbon ({rng.choice([330, 350, 370])}kg), Speed ({rng.choice([4, 4.5, 5])} weeks)",
                f"Your company weights: Cost ({rng.choice([25, 30, 35])}%), Quality ({rng.choice([20, 25, 30])}%), Sustainability ({rng.choice([20, 25, 30])}%), Speed ({rng.choice([15, 20, 25])}%)",
                "Normalize scores 0-100 for each criterion, then calculate weighted sum to identify best supplier",
            ],
        },
        5: {
            "scenario_id": "S5-Bounded",
            "theory": "Bounded Rationality & Satisficing",
            "theory_description": "Under time and information constraints, seek 'good enough' solutions rather than perfect optimization.",
            "optimal_strategy": "Satisficing (Option A)",
            "constraints": ConstraintsSnapshot(
                forecast_range={"SKU-A": [480, 700], "SKU-B": [280, 420], "SKU-C": [200, 320], "SKU-D": [150, 260]},
                capacity={"P1": 950, "P2": 700},
                costs={
                    "unit_cost": {"SKU-A": 12, "SKU-B": 9, "SKU-C": 7, "SKU-D": 9},
                    "overtime_cost_per_hour": {"_": 40},
                    "outsourcing_cost": {"SKU-A": 21, "SKU-B": 17, "SKU-C": 12, "SKU-D": 15},
                },
                service_targets={"SKU-A": 0.96, "SKU-B": 0.92, "SKU-C": 0.91, "SKU-D": 0.9},
                carbon_cap=1080,
                cash_on_hand=75000,
            ).model_dump(),
            "industry_news": [
                "THEORY: Bounded Rationality - Make timely 'good enough' decisions",
                f"Time pressure: Decision must be made in {rng.choice([8, 10, 12])} minutes",
                f"Incomplete information: Only {rng.choice([55, 60, 65])}% of supplier data available",
                f"Option A meets {rng.choice([80, 85, 88])}% of requirements and is immediately implementable (cost: {rng.choice([2000, 2500, 3000])})",
                f"Option B could meet {rng.choice([92, 95, 97])}% but requires {rng.choice([2.5, 3, 3.5])} more hours of analysis (cost: {rng.choice([1500, 2000, 2500])} + opportunity cost)",
                f"Analysis paralysis penalty: Each hour of delay costs {rng.choice([800, 1000, 1200])} in lost opportunities",
                "Satisficing beats optimization when marginal gains don't justify time/information costs",
            ],
        },
    }
    return scenarios.get(round_number, scenarios[1])


def _seed_for(team_id: str, round_number: int) -> int:
    random.seed(f"{team_id}-{round_number}")
    return random.randint(10000, 99999)


def _team_seed(team_id: str) -> int:
    """Generate consistent seed for team-specific variations."""
    return hash(team_id) % 100000


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = header.replace("Bearer ", "").strip()
    try:
        payload = serializer.loads(token)
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("user_id")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return User(id=user.id, email=user.email, role=user.role.value)


@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(body: AuthRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    user_id = _generate_id("user")
    user_model = models.User(
        id=user_id,
        email=body.email,
        password_hash=bcrypt.hash(body.password),
        role=models.UserRole(body.role),
    )
    db.add(user_model)
    db.commit()
    token = serializer.dumps({"user_id": user_id})
    return AuthResponse(token=token, user=User(id=user_id, email=body.email, role=body.role))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: AuthRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not bcrypt.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = serializer.dumps({"user_id": user.id})
    return AuthResponse(token=token, user=User(id=user.id, email=user.email, role=user.role.value))


@app.get("/api/session", response_model=User)
def session(user: User = Depends(get_current_user)):
    return user


@app.post("/api/teams", response_model=Team)
def create_team(body: TeamCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team_id = _generate_id("team")
    team_model = models.Team(
        id=team_id,
        name=body.name,
        join_code=_generate_join_code(),
        created_by=user.id,
    )
    db.add(team_model)
    db.flush()
    member = models.TeamMember(user_id=user.id, team_id=team_id)
    db.add(member)
    db.commit()
    return Team(id=team_id, name=team_model.name, join_code=team_model.join_code, created_by=user.id, members=[user.id])


@app.post("/api/teams/join", response_model=Team)
def join_team(body: TeamJoinRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team_model = db.query(models.Team).filter(models.Team.join_code == body.code).first()
    if not team_model:
        raise HTTPException(status_code=404, detail="Team not found")
    existing_member = (
        db.query(models.TeamMember)
        .filter(models.TeamMember.team_id == team_model.id, models.TeamMember.user_id == user.id)
        .first()
    )
    if not existing_member:
        db.add(models.TeamMember(team_id=team_model.id, user_id=user.id))
        db.commit()
    member_ids = [tm.user_id for tm in db.query(models.TeamMember).filter(models.TeamMember.team_id == team_model.id)]
    return Team(
        id=team_model.id,
        name=team_model.name,
        join_code=team_model.join_code,
        created_by=team_model.created_by,
        members=member_ids,
    )


@app.get("/api/teams/{team_id}", response_model=Team)
def get_team(team_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team_model = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team_model:
        raise HTTPException(status_code=404, detail="Team not found")
    member_ids = [tm.user_id for tm in db.query(models.TeamMember).filter(models.TeamMember.team_id == team_model.id)]
    return Team(
        id=team_model.id,
        name=team_model.name,
        join_code=team_model.join_code,
        created_by=team_model.created_by,
        members=member_ids,
    )


@app.get("/api/rounds/current", response_model=RoundState)
def current_round(
    team_id: str = Query(...), round_number: int = Query(1), user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    team_model = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team_model:
        raise HTTPException(status_code=404, detail="Team not found")
    round_key = f"{team_id}-{round_number}"
    round_model = db.query(models.Round).filter(models.Round.id == round_key).first()
    team_seed = _team_seed(team_id)
    if not round_model:
        scenario = _scenario_for(round_number, team_seed)
        round_model = models.Round(
            id=round_key,
            team_id=team_id,
            scenario_id=scenario["scenario_id"],
            number=round_number,
            seed=_seed_for(team_id, round_number),
            status="open",
            constraints_json=scenario["constraints"],
        )
        db.add(round_model)
        db.commit()
    constraints_data = round_model.constraints_json or _scenario_for(round_model.number, team_seed)["constraints"]
    scenario = _scenario_for(round_model.number, team_seed)
    return RoundState(
        round=round_model.number,
        scenario_id=round_model.scenario_id or "S1",
        seed=round_model.seed,
        constraints=ConstraintsSnapshot(**constraints_data),
        status=round_model.status,
        industry_news=scenario.get("industry_news", []),
        theory=scenario.get("theory"),
        theory_description=scenario.get("theory_description"),
    )


@app.post("/api/rounds/submit", status_code=202, response_model=ResultPayload)
def submit_decision(body: DecisionPayload, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    round_id = f"{body.team_id}-{body.round}"
    round_model = db.query(models.Round).filter(models.Round.id == round_id).first()
    if not round_model:
        round_model = models.Round(
            id=round_id,
            team_id=body.team_id,
            scenario_id=body.scenario_id,
            number=body.round,
            seed=body.seed,
            status="open",
            constraints_json=body.constraints_snapshot.model_dump(),
        )
        db.add(round_model)
        db.flush()
    decision_id = _generate_id("dec")
    decision = models.Decision(
        id=decision_id,
        round_id=round_model.id,
        team_id=body.team_id,
        user_id=user.id,
        payload_json=body.model_dump(by_alias=True),
        status="submitted",
    )
    db.add(decision)
    db.commit()
    result = evaluate_decision(body.model_dump(by_alias=True))
    result_payload = ResultPayload(**result)
    result_model = models.Result(
        id=_generate_id("res"),
        round_id=round_model.id,
        team_id=body.team_id,
        payload_json=result_payload.model_dump(),
    )
    db.add(result_model)
    db.commit()
    return result_payload


@app.get("/api/rounds/{round_id}/results", response_model=ResultPayload)
def get_results(round_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result_model = db.query(models.Result).filter(models.Result.round_id == round_id).first()
    if not result_model:
        raise HTTPException(status_code=404, detail="Result not found")
    return ResultPayload(**result_model.payload_json)


@app.post("/api/admin/rounds/{round_id}/control")
def control_round(
    round_id: str,
    action: str = Query(..., pattern="^(start|pause|lock)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "instructor":
        raise HTTPException(status_code=403, detail="Instructor only")
    round_model = db.query(models.Round).filter(models.Round.id == round_id).first()
    if not round_model:
        raise HTTPException(status_code=404, detail="Round not found")
    round_model.status = action
    db.commit()
    return {"round_id": round_id, "status": round_model.status}


@app.get("/api/admin/export")
def export_logs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "instructor":
        raise HTTPException(status_code=403, detail="Instructor only")
    export = {
        "users": [
            {"id": u.id, "email": u.email, "role": u.role.value, "created_at": u.created_at.isoformat()}
            for u in db.query(models.User).all()
        ],
        "teams": [
            {"id": t.id, "name": t.name, "join_code": t.join_code, "created_by": t.created_by}
            for t in db.query(models.Team).all()
        ],
        "decisions": [d.payload_json for d in db.query(models.Decision).all()],
        "results": [r.payload_json for r in db.query(models.Result).all()],
    }
    return JSONResponse(content=export)
