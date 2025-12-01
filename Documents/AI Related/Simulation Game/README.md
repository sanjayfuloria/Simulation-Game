# Decision Theory Simulation Game

An interactive operations management simulation where teams apply decision theory concepts to make production, inventory, and supplier decisions under uncertainty.

## 🎮 How to Play

### For Students

1. **Sign Up & Create/Join a Team**

   - Open the game in your browser
   - Create an account with your email
   - Either create a new team or join an existing one with a team code

2. **Play Through 5 Rounds**
   Each round focuses on a different decision theory:

   - **Round 1**: Expected Utility Theory - Calculate probabilities and payoffs
   - **Round 2**: Prospect Theory - Overcome loss aversion bias
   - **Round 3**: Bayesian Updating - Revise forecasts with new data
   - **Round 4**: Multi-Criteria Decision Analysis - Balance competing objectives
   - **Round 5**: Bounded Rationality - Make "good enough" decisions under time pressure

3. **Make Decisions**

   - Read the theory and scenario context
   - Analyze your team-specific numbers (each team gets different values)
   - Set production quantities, overtime, and outsourcing levels
   - Submit your decision

4. **Review Results**
   - View profit, service level, emissions, and reputation
   - Compare your performance against other teams
   - Learn from each round's outcome

### Challenge

Each team receives unique numbers for the same scenario. You can't copy another team's answer - you must understand the theory and apply it correctly to your specific situation!

---

## 🚀 Quick Start (Running the Game)

### Prerequisites

- Python 3.10 or higher
- Terminal/Command line access

### Installation & Setup

1. **Clone or download this repository**

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Start the API server** (Terminal 1)

   ```bash
   make api
   ```

   Keep this terminal running. The API will start at `http://localhost:8000`

4. **Start the game interface** (Terminal 2 - new window/tab)

   ```bash
   make ui
   ```

   The game will automatically open in your browser at `http://localhost:8501`

5. **Play the game!**
   - Sign up as a student
   - Create or join a team
   - Start playing rounds

### Alternative: Docker Setup

```bash
docker compose -f infra/docker-compose.yml up
```

---

## 📚 For Instructors

### Viewing Analytics

1. Sign up with role "instructor"
2. Access the instructor controls at the bottom of the page
3. View leaderboards, team performance, and export data

### Theory Framework

The simulation teaches these foundational theories:

1. **Expected Utility Theory** (von Neumann & Morgenstern, 1944)

   - Rational choice under uncertainty
   - Computing probability × utility

2. **Prospect Theory** (Kahneman & Tversky, 1979)

   - Loss aversion and decision biases
   - Asymmetric evaluation of gains/losses

3. **Bayesian Updating** (Berger, 1985)

   - Belief revision with new evidence
   - Data-driven decision making

4. **Multi-Criteria Decision Analysis** (Saaty, 1980; Keeney & Raiffa, 1993)

   - Balancing competing objectives
   - Weighted scoring methods

5. **Bounded Rationality** (Simon, 1955)
   - Satisficing under constraints
   - "Good enough" vs. optimal solutions

---

## 📁 Project Structure

```
├── app/          # Streamlit UI (game interface)
├── api/          # FastAPI backend (game logic & data)
├── optimizer/    # Decision evaluation engine
├── db/           # Database migrations
├── infra/        # Docker configuration
└── tests/        # Test suite
```

---

## 🛠️ Troubleshooting

**"Connection refused" error**

- Make sure the API server is running in a separate terminal (`make api`)
- Check that port 8000 is not already in use

**Module not found errors**

- Run `pip install -r requirements.txt` again
- Make sure you're using Python 3.10 or higher

**Can't see other terminals**

- You need TWO terminal windows/tabs running simultaneously
- Terminal 1: API server (keep running)
- Terminal 2: Game interface (keep running)

---

## 📝 Notes

- Uses SQLite database by default (no setup required)
- Each team gets unique scenario variations based on their team ID
- All data is stored locally in `dev.db`
- Reset game: delete `dev.db` file and restart

---

## 🎓 Learning Outcomes

Students will:

- Apply decision theory frameworks to real-world scenarios
- Calculate expected utilities and update beliefs with Bayesian methods
- Recognize and overcome cognitive biases (loss aversion)
- Make structured multi-criteria decisions
- Balance optimization vs. satisficing under constraints

---

## 📖 References

- von Neumann, J., & Morgenstern, O. (1944). _Theory of Games and Economic Behavior_
- Kahneman, D., & Tversky, A. (1979). Prospect Theory: An Analysis of Decision under Risk
- Berger, J. O. (1985). _Statistical Decision Theory and Bayesian Analysis_
- Saaty, T. L. (1980). _The Analytic Hierarchy Process_
- Simon, H. A. (1955). A Behavioral Model of Rational Choice
