from optimizer.engine import evaluate_decision


def test_optimizer_determinism():
    payload = {
        "team_id": "T1",
        "round": 1,
        "scenario_id": "S1",
        "seed": 12345,
        "plants": [
            {"plant_id": "P1", "production_qty": {"SKU-A": 100, "SKU-B": 50}, "overtime_hours": 10, "outsourcing_qty": {}}
        ],
        "inventory_policy": {"targets": {}, "reorder_triggers": {}},
        "transport_priorities": ["SKU-A", "SKU-B"],
        "routing_overrides": [],
        "capacity_rules": {"scarce_capacity_allocation": "service-first"},
        "constraints_snapshot": {
            "forecast_range": {"SKU-A": [90, 120], "SKU-B": [40, 70]},
            "capacity": {"P1": 200},
            "costs": {"unit_cost": {"SKU-A": 10, "SKU-B": 8}, "overtime_cost_per_hour": 30, "outsourcing_cost": {}},
            "service_targets": {"SKU-A": 0.95, "SKU-B": 0.9},
            "carbon_cap": 1000,
            "cash_on_hand": 20000,
        },
    }
    first = evaluate_decision(payload)
    second = evaluate_decision(payload)
    assert first == second
    assert first["team_id"] == "T1"
    assert first["kpis"]["profit"] != 0
