import os
import json
import random
import pandas as pd
import requests
import streamlit as st

API_HOST = os.environ.get("API_HOST", "http://localhost:8000")


def api_request(method: str, path: str, token: str = "", **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{API_HOST}{path}"
    resp = requests.request(method, url, headers=headers, **kwargs)
    if resp.status_code >= 400:
        raise Exception(f"{resp.status_code}: {resp.text}")
    if resp.text:
        return resp.json()
    return {}


def ensure_session_state():
    for key, default in [
        ("token", None),
        ("user", None),
        ("team", None),
        ("round_state", None),
        ("result", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default


def inject_styles():
    st.markdown(
        """
        <style>
        .hero {
            background: linear-gradient(135deg, #111827 0%, #1f2937 40%, #0ea5e9 100%);
            color: #e5e7eb;
            padding: 20px 24px;
            border-radius: 12px;
            margin-bottom: 16px;
        }
        .card {
            padding: 12px 14px;
            border-radius: 10px;
            background: #0b1220;
            border: 1px solid rgba(255,255,255,0.06);
            color: #e5e7eb;
        }
        .pill {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            background: #0ea5e9;
            color: #0b1220;
            margin-right: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def industry_news(round_state):
    if not round_state:
        return []
    seed = (round_state.get("seed") or 0) + round_state.get("round", 0)
    rng = random.Random(seed)
    headlines = [
        "Supplier capacity squeeze expected; spot prices rising",
        "Logistics slowdown at coastal ports; plan extra lead time",
        "Carbon audit upcoming; emissions visibility under scrutiny",
        "Regional demand uptick projected for premium SKUs",
        "Overtime regulations tightening; monitor hours",
        "Industry peers shifting to dual sourcing to hedge risk",
    ]
    rng.shuffle(headlines)
    return headlines[:2]


def auth_section():
    st.header("Adaptive Operations Lab")
    st.markdown(
        "<div class='hero'><strong>Scenario: Adaptive Operations Lab</strong><br/>"
        "Make production, outsourcing, and priority calls under uncertainty. Each round draws demand and throws disruptions — aim for profit, service, and reputation.</div>",
        unsafe_allow_html=True,
    )
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_signup:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pw")
        role = st.selectbox("Role", ["student", "instructor"])
        if st.button("Create account"):
            data = api_request(
                "POST",
                "/api/auth/signup",
                json={"email": email, "password": password, "role": role},
            )
            st.session_state.token = data["token"]
            st.session_state.user = data["user"]
            st.success("Account created.")

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            data = api_request(
                "POST",
                "/api/auth/login",
                json={"email": email, "password": password},
            )
            st.session_state.token = data["token"]
            st.session_state.user = data["user"]
            st.success("Logged in.")


def team_section():
    st.subheader("Team")
    if not st.session_state.user:
        st.info("Login to create or join a team.")
        return

    if st.session_state.team:
        team = st.session_state.team
        st.success(f"On team: {team['name']} (code: {team['join_code']})")
        return

    col1, col2 = st.columns(2)
    with col1:
        team_name = st.text_input("New team name")
        if st.button("Create team"):
            team = api_request(
                "POST",
                "/api/teams",
                token=st.session_state.token,
                json={"name": team_name or "Team"},
            )
            st.session_state.team = team
            st.success(f"Created team {team['name']}. Join code: {team['join_code']}")

    with col2:
        code = st.text_input("Join code")
        if st.button("Join team"):
            team = api_request(
                "POST",
                "/api/teams/join",
                token=st.session_state.token,
                json={"code": code},
            )
            st.session_state.team = team
            st.success(f"Joined team {team['name']}.")


def round_section():
    st.subheader("Round play")
    if not st.session_state.team:
        st.info("Create or join a team first.")
        return
    team_id = st.session_state.team["id"]
    round_number = st.number_input("Round number", min_value=1, max_value=8, step=1, value=1)
    if st.button("Load current round"):
        round_state = api_request(
            "GET",
            f"/api/rounds/current?team_id={team_id}&round_number={round_number}",
            token=st.session_state.token,
        )
        st.session_state.round_state = round_state
        st.session_state.result = None

    round_state = st.session_state.round_state
    if not round_state:
        return

    st.write(f"Round {round_state['round']} | Scenario {round_state['scenario_id']} | Seed {round_state['seed']}")
    
    # Display theory information if available
    theory = round_state.get("theory")
    theory_desc = round_state.get("theory_description")
    if theory:
        st.info(f"**Decision Theory Focus: {theory}**\n\n{theory_desc}")
    
    news = round_state.get("industry_news") or industry_news(round_state)
    if news:
        st.markdown("**Industry Signals & Scenario Context**")
        for item in news:
            if item.startswith("THEORY:"):
                st.markdown(f"### {item}")
            else:
                st.markdown(f"• {item}")

    constraints = round_state["constraints"]
    with st.expander("Scenario 1 snapshot", expanded=True):
        st.markdown(
            """
            - Demand is uncertain within forecast ranges; realized demand is drawn each round.
            - Profit, service, emissions are affected by demand variation, disruptions, overtime, and outsourcing.
            """
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("**Forecast range**")
            for sku, rng in constraints["forecast_range"].items():
                st.write(f"{sku}: {rng[0]}–{rng[1]}")
        with c2:
            st.write("**Capacity / service**")
            for plant, cap in constraints["capacity"].items():
                st.write(f"{plant}: {cap}")
            st.write("Service targets")
            for sku, target in constraints["service_targets"].items():
                st.write(f"{sku}: {int(target*100)}%")
        with c3:
            st.write("**Costs**")
            costs = constraints.get("costs", {})
            unit = costs.get("unit_cost", {})
            for sku, cost in unit.items():
                st.write(f"{sku} unit: {cost}")
            overtime = costs.get("overtime_cost_per_hour", {})
            if overtime:
                st.write(f"Overtime/hr: {list(overtime.values())[0]}")
            outsourcing = costs.get("outsourcing_cost", {})
            if outsourcing:
                for sku, cost in outsourcing.items():
                    st.write(f"{sku} outsource: {cost}")
            st.write(f"Carbon cap: {constraints['carbon_cap']}")
            st.write(f"Cash: {constraints['cash_on_hand']}")
        # Simple scenario table for quick scan
        st.markdown("**Scenario 1 at a glance**")
        table_rows = []
        for sku, rng in constraints["forecast_range"].items():
            unit_cost = costs.get("unit_cost", {}).get(sku, 0)
            outsource_cost = costs.get("outsourcing_cost", {}).get(sku, "-")
            target = constraints["service_targets"].get(sku, 0)
            table_rows.append(
                {
                    "SKU": sku,
                    "Forecast": f"{rng[0]}–{rng[1]}",
                    "Unit cost": f"{int(unit_cost)}",
                    "Outsource": f"{int(outsource_cost)}" if outsource_cost != "-" else "-",
                    "Target service": f"{int(target*100)}%",
                }
            )
        st.table(table_rows)

    with st.expander("How to decide", expanded=True):
        st.markdown(
            """
            1. Cover likely demand: produce near mid-range of forecast to balance service and cost.
            2. Use overtime sparingly: boosts service but raises emissions and cost.
            3. Outsource for spikes: fill gaps for high-margin SKUs when capacity is tight.
            4. Prioritize SKUs: choose which products get scarce capacity if demand spikes.
            5. Watch carbon and cash: higher overtime/outsourcing can hurt emissions and cash end.
            6. Track trends: watch service and emissions trends round to round; adjust mix if service dips.
            """
        )

    st.markdown("#### Decision")
    plants = []
    skus = list(constraints["forecast_range"].keys())
    for pid in constraints["capacity"].keys():
        plant_entry = {"plant_id": pid, "production_qty": {}, "outsourcing_qty": {}, "overtime_hours": 0, "allocation_priority": skus}
        st.write(f"**{pid}**")
        for sku in skus:
            qty = st.number_input(
                f"{pid} produce {sku}",
                min_value=0,
                step=10,
                key=f"{pid}-{sku}",
            )
            if qty:
                plant_entry["production_qty"][sku] = qty
            outsource_qty = st.number_input(
                f"{pid} outsource {sku}",
                min_value=0,
                step=10,
                key=f"{pid}-out-{sku}",
            )
            if outsource_qty:
                plant_entry["outsourcing_qty"][sku] = outsource_qty
        ot = st.number_input(f"{pid} overtime hours", min_value=0, step=1, key=f"{pid}-ot")
        plant_entry["overtime_hours"] = ot
        priority = st.multiselect(
            f"{pid} allocation priority",
            options=skus,
            default=skus,
            key=f"{pid}-prio",
        )
        plant_entry["allocation_priority"] = priority
        plants.append(plant_entry)

    if st.button("Submit decision"):
        total_units = sum(sum(p["production_qty"].values()) for p in plants)
        if total_units <= 0:
            st.warning("Enter at least one positive production quantity.")
            return
        payload = {
            "team_id": team_id,
            "round": round_state["round"],
            "scenario_id": round_state["scenario_id"],
            "seed": round_state["seed"],
            "plants": plants,
            "inventory_policy": {"targets": {}, "reorder_triggers": {}},
            "transport_priorities": list(constraints["forecast_range"].keys()),
            "routing_overrides": [],
            "capacity_rules": {"scarce_capacity_allocation": "service-first"},
            "constraints_snapshot": constraints,
        }
        result = api_request(
            "POST",
            "/api/rounds/submit",
            token=st.session_state.token,
            json=payload,
        )
        st.session_state.result = result
        st.success("Decision submitted.")

    if st.session_state.result:
        st.markdown("#### Results")
        res = st.session_state.result
        kpis = res.get("kpis", {})
        usage = res.get("usage", {})
        disruption = res.get("disruption", {})

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Profit", f"{kpis.get('profit', 0):,.0f}")
        m2.metric("Service (overall)", f"{kpis.get('service_level', {}).get('overall', 0)*100:.1f}%")
        m3.metric("Emissions", f"{kpis.get('emissions', 0):,.0f}")
        m4.metric("Reputation", f"{kpis.get('reputation', 0):.0f}")

        c1, c2 = st.columns(2)
        with c1:
            st.write("**Service by SKU**")
            service_data = {
                "sku": [sku for sku in kpis.get("service_level", {}) if sku != "overall"],
                "service": [val * 100 for sku, val in kpis.get("service_level", {}).items() if sku != "overall"],
            }
            if service_data["sku"]:
                df_service = pd.DataFrame(
                    {"sku": service_data["sku"], "service %": service_data["service"]}
                )
                st.bar_chart(df_service, x="sku", y="service %")
            stockouts = kpis.get("stockouts", {})
            if stockouts:
                st.write("**Stockouts**")
                df_so = pd.DataFrame(
                    {"sku": list(stockouts.keys()), "stockouts": list(stockouts.values())}
                )
                st.bar_chart(df_so, x="sku", y="stockouts")
        with c2:
            st.write("**Resource use**")
            cap_used = usage.get("capacity_used", {})
            if cap_used:
                df_cap = pd.DataFrame(
                    {"plant": list(cap_used.keys()), "units": list(cap_used.values())}
                )
                st.bar_chart(df_cap, x="plant", y="units")
            st.write(f"Overtime hours: {usage.get('overtime_used_hours', 0)}")
            st.write(f"Cash end: {usage.get('cash_end', 0):,.0f}")
            inv = usage.get("inventory_end", {})
            if inv:
                st.write("Ending inventory")
                for sku, qty in inv.items():
                    st.write(f"{sku}: {qty}")

        if disruption:
            with st.expander("Disruption"):
                st.write(f"Type: {disruption.get('type')}")
                for k, v in disruption.get("details", {}).items():
                    st.write(f"{k}: {v}")

        # Student-facing trend (round history in session)
        history = st.session_state.get("result_history", [])
        history.append(
            {
                "round": st.session_state.round_state.get("round", len(history) + 1) if st.session_state.round_state else len(history) + 1,
                "profit": kpis.get("profit", 0),
                "service": kpis.get("service_level", {}).get("overall", 0) * 100,
                "emissions": kpis.get("emissions", 0),
            }
        )
        st.session_state.result_history = history[-8:]  # keep last 8
        if history:
            st.markdown("**Your trend (last rounds)**")
            st.line_chart(
                {
                    "round": [h["round"] for h in history],
                    "profit": [h["profit"] for h in history],
                    "service %": [h["service"] for h in history],
                    "emissions": [h["emissions"] for h in history],
                },
                x="round",
            )


def instructor_section():
    user = st.session_state.user
    if not user or user.get("role") != "instructor":
        return
    
    st.title("📊 Instructor Dashboard")
    
    # Auto-load data on page load
    if "admin_export" not in st.session_state:
        try:
            export = api_request("GET", "/api/admin/export", token=st.session_state.token)
            st.session_state["admin_export"] = export
        except Exception as e:
            st.error(f"Failed to load data: {e}")
    
    # Manual refresh button
    if st.button("🔄 Refresh Data"):
        export = api_request("GET", "/api/admin/export", token=st.session_state.token)
        st.session_state["admin_export"] = export
        st.success("Data refreshed!")
    
    # Round control section
    with st.expander("⚙️ Round Control", expanded=False):
        export = st.session_state.get("admin_export", {})
        teams = export.get("teams", [])
        results = export.get("results", [])
        
        # Build list of actual round IDs
        round_ids = []
        for r in results:
            team_id = r.get("team_id")
            round_num = r.get("round")
            if team_id and round_num:
                round_id = f"{team_id}-{round_num}"
                if round_id not in round_ids:
                    round_ids.append(round_id)
        
        if round_ids:
            selected_round = st.selectbox("Select Round", options=round_ids)
            action = st.selectbox("Action", ["start", "pause", "lock"])
            if st.button("Apply Action"):
                try:
                    res = api_request(
                        "POST",
                        f"/api/admin/rounds/{selected_round}/control",
                        token=st.session_state.token,
                        params={"action": action},
                    )
                    st.success(f"Updated {res['round_id']} to {res['status']}")
                except Exception as e:
                    st.error(f"Failed to update round: {e}")
        else:
            st.info("No rounds have been played yet. Students need to submit decisions first.")
    
    st.markdown("---")

    export = st.session_state.get("admin_export")
    if export:
        teams = export.get("teams", [])
        users = export.get("users", [])
        results = export.get("results", [])

        st.write(f"Teams: {len(teams)} | Users: {len(users)} | Results: {len(results)}")
        t1, t2 = st.columns(2)
        with t1:
            if teams:
                st.write("Teams roster")
                st.table(teams)
        with t2:
            if users:
                st.write("Users")
                st.table(users)

        if results:
            # Round-by-round winner analysis
            st.markdown("### 🏆 Round Winners & Performance Analysis")
            
            # Group results by round
            rounds_data = {}
            for r in results:
                round_num = r.get("round", 0)
                team_id = r.get("team_id", "unknown")
                kpis = r.get("kpis", {})
                
                if round_num not in rounds_data:
                    rounds_data[round_num] = []
                
                rounds_data[round_num].append({
                    "team_id": team_id,
                    "profit": kpis.get("profit", 0),
                    "service": kpis.get("service_level", {}).get("overall", 0) * 100,
                    "emissions": kpis.get("emissions", 0),
                    "reputation": kpis.get("reputation", 0),
                    "feasible": r.get("feasible", True),
                    "messages": r.get("messages", [])
                })
            
            # Display winner for each round
            for round_num in sorted(rounds_data.keys()):
                round_teams = rounds_data[round_num]
                
                # Find winner (highest profit among feasible solutions)
                feasible_teams = [t for t in round_teams if t["feasible"]]
                if not feasible_teams:
                    feasible_teams = round_teams
                
                winner = max(feasible_teams, key=lambda x: x["profit"])
                
                with st.expander(f"📊 Round {round_num} - Winner: {winner['team_id']} (Profit: {winner['profit']:,.0f})", expanded=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("#### Team Performance Comparison")
                        comparison_df = pd.DataFrame([
                            {
                                "Team": t["team_id"],
                                "Profit": round(t["profit"], 0),
                                "Service %": round(t["service"], 1),
                                "Emissions": round(t["emissions"], 0),
                                "Reputation": round(t["reputation"], 0),
                                "Status": "✓ Feasible" if t["feasible"] else "✗ Infeasible"
                            }
                            for t in sorted(round_teams, key=lambda x: x["profit"], reverse=True)
                        ])
                        st.dataframe(comparison_df, use_container_width=True)
                        
                        # Visual comparison
                        st.markdown("**Profit Comparison**")
                        chart_data = pd.DataFrame({
                            "Team": [t["team_id"] for t in sorted(round_teams, key=lambda x: x["profit"], reverse=True)],
                            "Profit": [t["profit"] for t in sorted(round_teams, key=lambda x: x["profit"], reverse=True)]
                        })
                        st.bar_chart(chart_data.set_index("Team"))
                    
                    with col2:
                        st.markdown("#### Why They Won")
                        st.metric("Winner Profit", f"{winner['profit']:,.0f}")
                        st.metric("Service Level", f"{winner['service']:.1f}%")
                        st.metric("Emissions", f"{winner['emissions']:,.0f}")
                        
                        # Calculate performance vs others
                        avg_profit = sum(t["profit"] for t in round_teams) / len(round_teams)
                        profit_advantage = ((winner["profit"] - avg_profit) / avg_profit * 100) if avg_profit != 0 else 0
                        
                        st.markdown(f"**Performance Advantage:**")
                        st.write(f"• {profit_advantage:+.1f}% above average profit")
                        
                        if winner.get("messages"):
                            st.markdown("**Key Decisions:**")
                            for msg in winner["messages"][:3]:
                                msg_type = msg.get("type", "info")
                                msg_text = msg.get("message", "")
                                if msg_type == "success":
                                    st.success(msg_text, icon="✓")
                                elif msg_type == "warning":
                                    st.warning(msg_text, icon="⚠")
                                else:
                                    st.info(msg_text)

            # Overall leaderboard
            st.markdown("### 📈 Overall Leaderboard (Cumulative)")
            leaderboard = {}
            for r in results:
                team_id = r.get("team_id")
                kpis = r.get("kpis", {})
                usage = r.get("usage", {})
                if not team_id:
                    continue
                agg = leaderboard.setdefault(
                    team_id,
                    {"profit": 0, "service": [], "emissions": [], "reputation": [], "cash_end": [], "rounds_played": 0},
                )
                agg["profit"] += kpis.get("profit", 0)
                agg["rounds_played"] += 1
                svc_overall = kpis.get("service_level", {}).get("overall")
                if svc_overall is not None:
                    agg["service"].append(svc_overall)
                if "emissions" in kpis:
                    agg["emissions"].append(kpis["emissions"])
                if "reputation" in kpis:
                    agg["reputation"].append(kpis["reputation"])
                if "cash_end" in usage:
                    agg["cash_end"].append(usage["cash_end"])

            lb_rows = []
            for tid, agg in leaderboard.items():
                svc = sum(agg["service"]) / len(agg["service"]) if agg["service"] else 0
                em = sum(agg["emissions"]) / len(agg["emissions"]) if agg["emissions"] else 0
                rep = sum(agg["reputation"]) / len(agg["reputation"]) if agg["reputation"] else 0
                cash = agg["cash_end"][-1] if agg["cash_end"] else 0
                lb_rows.append(
                    {
                        "Rank": 0,
                        "Team": tid,
                        "Rounds": agg["rounds_played"],
                        "Total Profit": round(agg["profit"], 0),
                        "Avg Service %": round(svc * 100, 1),
                        "Avg Emissions": round(em, 0),
                        "Avg Reputation": round(rep, 0),
                        "Final Cash": round(cash, 0),
                    }
                )
            if lb_rows:
                lb_rows = sorted(lb_rows, key=lambda x: (x["Total Profit"], x["Avg Service %"]), reverse=True)
                for i, row in enumerate(lb_rows):
                    row["Rank"] = i + 1
                
                lb_df = pd.DataFrame(lb_rows)
                st.dataframe(lb_df, use_container_width=True, hide_index=True)

            # Charts
            st.markdown("**KPIs over time (all teams)**")
            profit_series = [r.get("kpis", {}).get("profit", 0) for r in results]
            svc_series = [r.get("kpis", {}).get("service_level", {}).get("overall", 0) * 100 for r in results]
            em_series = [r.get("kpis", {}).get("emissions", 0) for r in results]
            st.line_chart(
                {
                    "profit": profit_series,
                    "service %": svc_series,
                    "emissions": em_series,
                }
            )

            # Per-team time series
            st.markdown("**Per-team trends**")
            team_options = [t.get("id") for t in teams]
            selected_team = st.selectbox("Team", options=team_options) if team_options else None
            if selected_team:
                team_results = [r for r in results if r.get("team_id") == selected_team]
                team_results = sorted(team_results, key=lambda x: x.get("round", 0))
                if team_results:
                    st.line_chart(
                        {
                            "profit": [r.get("kpis", {}).get("profit", 0) for r in team_results],
                            "service %": [
                                r.get("kpis", {}).get("service_level", {}).get("overall", 0) * 100 for r in team_results
                            ],
                            "emissions": [r.get("kpis", {}).get("emissions", 0) for r in team_results],
                        }
                    )

            st.markdown("### 📋 Recent Results (Last 5 Submissions)")
            recent_results = []
            for r in results[-5:]:
                kpis = r.get("kpis", {})
                recent_results.append({
                    "Team": r.get("team_id", "N/A"),
                    "Round": r.get("round", "N/A"),
                    "Profit": f"{kpis.get('profit', 0):,.0f}",
                    "Service %": f"{kpis.get('service_level', {}).get('overall', 0) * 100:.1f}",
                    "Emissions": f"{kpis.get('emissions', 0):,.0f}",
                    "Reputation": f"{kpis.get('reputation', 0):.0f}",
                    "Feasible": "✓" if r.get("feasible", True) else "✗"
                })
            
            if recent_results:
                recent_df = pd.DataFrame(recent_results)
                st.dataframe(recent_df, use_container_width=True, hide_index=True)
            else:
                st.info("No results yet. Students need to submit decisions first.")

        st.download_button("Download logs", json.dumps(export, indent=2), file_name="logs.json")


def main():
    inject_styles()
    ensure_session_state()
    auth_section()
    
    # Check if user is logged in and their role
    user = st.session_state.user
    
    if user and user.get("role") == "instructor":
        # Instructor sees only analytics dashboard
        instructor_section()
    elif user:
        # Students see the game interface
        team_section()
        round_section()
    else:
        # Not logged in - show nothing else
        st.info("Please login to continue")


if __name__ == "__main__":
    main()
