import random
from typing import Any, Dict


def _simulate_demand(rng: random.Random, forecast_range: Dict[str, Any]) -> Dict[str, int]:
    return {sku: rng.randint(int(bounds[0]), int(bounds[1])) for sku, bounds in forecast_range.items()}


def _profit(production_qty: Dict[str, int], costs: Dict[str, Any], demand: Dict[str, int]) -> float:
    unit_costs = costs.get("unit_cost", {})
    revenue_per_unit = {sku: unit_costs.get(sku, 10) * 1.8 for sku in production_qty}
    sold = {sku: min(qty, demand.get(sku, 0)) for sku, qty in production_qty.items()}
    total_revenue = sum(sold[sku] * revenue_per_unit[sku] for sku in sold)
    total_cost = sum(production_qty[sku] * unit_costs.get(sku, 0) for sku in production_qty)
    return round(total_revenue - total_cost, 2)


def evaluate_decision(decision_input: Dict[str, Any]) -> Dict[str, Any]:
    seed = decision_input.get("seed", 0)
    rng = random.Random(seed)
    plants = decision_input.get("plants", [])
    constraints = decision_input.get("constraints_snapshot", {})
    costs = constraints.get("costs", {})
    forecast_range = constraints.get("forecast_range", {})

    # Probabilistic demand realization within forecast range
    demand = _simulate_demand(rng, forecast_range)

    production = {}
    overtime_used = 0
    outsourcing_used: Dict[str, int] = {}
    for plant in plants:
        production_qty = plant.get("production_qty", {})
        overtime_used += plant.get("overtime_hours", 0) or 0
        for sku, qty in plant.get("outsourcing_qty", {}).items():
            outsourcing_used[sku] = outsourcing_used.get(sku, 0) + qty
        for sku, qty in production_qty.items():
            production[sku] = production.get(sku, 0) + qty + plant.get("outsourcing_qty", {}).get(sku, 0)

    profit_val = _profit(production, costs, demand)

    service_level = {}
    stockouts = {}
    for sku, prod_qty in production.items():
        dem = demand.get(sku, 0)
        service = prod_qty / dem if dem else 1
        service_level[sku] = round(min(service, 1), 2)
        stockouts[sku] = max(0, dem - prod_qty)
    overall_service = round(sum(service_level.values()) / max(len(service_level), 1), 2)

    emissions = rng.randint(800, 1200) + int(overtime_used * 0.5)
    disruption_type = rng.choice(["machine_failure", "demand_spike", "supplier_delay", "transport_delay"])
    disruption_detail = {
        "machine_failure": {"capacity_loss": 0.1},
        "demand_spike": {"extra_demand_pct": 0.2},
        "supplier_delay": {"outsourcing_cut": 0.15},
        "transport_delay": {"delivery_slip_days": rng.randint(1, 3)},
    }.get(disruption_type, {})

    return {
        "team_id": decision_input.get("team_id"),
        "round": decision_input.get("round"),
        "feasible": True,
        "messages": [
            {"level": "info", "text": "Probabilistic demand realized"},
            {"level": "info", "text": f"Disruption: {disruption_type}"},
        ],
        "kpis": {
            "profit": profit_val,
            "service_level": {**service_level, "overall": overall_service},
            "stockouts": stockouts,
            "wip": rng.randint(50, 200),
            "emissions": emissions,
            "reputation": max(0, 100 - emissions // 20),
        },
        "usage": {
            "capacity_used": {plant.get("plant_id"): sum(plant.get("production_qty", {}).values()) for plant in plants},
            "overtime_used_hours": overtime_used,
            "outsourcing_used": outsourcing_used,
            "inventory_end": decision_input.get("inventory_policy", {}).get("targets", {}),
            "cash_end": constraints.get("cash_on_hand", 0) + profit_val,
        },
        "disruption": {
            "type": disruption_type,
            "details": {"note": "probabilistic outcome", **disruption_detail, "seed": seed},
        },
        "next_state_seed": rng.randint(10000, 99999),
    }
