import random
from collections import defaultdict
import pickle

class GamifiedTunerAgent:
    def __init__(self, actions=None, alpha=0.1, gamma=0.9, delta=0.9, epsilon=1.0, epsilon_min=0.05, epsilon_decay=0.995):
        self.actions = actions or ["increase_difficulty", "decrease_difficulty", "give_hint", "show_motivation"]
        self.q_table = defaultdict(lambda: {a: 0.0 for a in self.actions})
        self.alpha = alpha  # learning rate
        self.gamma = gamma  # discount factor
        self.delta = delta  # Q-learning discount for future rewards
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        self.load_q_table()

    def get_state(self, logs):
        # Example: state is a tuple of (performance, time_taken, engagement, difficulty, proficiency)
        return (
            logs.get("performance", 0),
            logs.get("time_taken", 0),
            logs.get("engagement", 0),
            logs.get("difficulty", 1),
            logs.get("proficiency", 0)
        )

    def engagement_dynamics(self, E, R, D, alpha=1.0, beta=1.0):
        # dE/dt = αR(t) − βD(t)
        return E + alpha * R - beta * D

    def task_adaptation(self, Ti, U, Si, gamma=1.0):
        # Ti(t+1) = Ti(t) + γ(U(t)−Si(t))
        return Ti + gamma * (U - Si)

    def reward_optimization(self, G, C, w1=1.0, w2=1.0):
        # R(a) = w1*G(a) − w2*C(a)
        return w1 * G - w2 * C

    def choose_action(self, state):
        # Epsilon-greedy policy with decaying epsilon
        if random.random() < self.epsilon or state not in self.q_table:
            action = random.choice(self.actions)
        else:
            action = max(self.q_table[state], key=self.q_table[state].get)
        # Decay epsilon after each action
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        return action

    def update_q_table(self, state, action, reward, next_state):
        old_value = self.q_table[state][action]
        next_max = max(self.q_table[next_state].values())
        # Q(st,at) = rt + δ * max Q(st+1,a)
        new_value = (1 - self.alpha) * old_value + self.alpha * (reward + self.delta * next_max)
        self.q_table[state][action] = new_value

    def step(self, logs, user_action_metrics):
        # 1. Get current state
        state = self.get_state(logs)

        # 2. Choose action
        action = self.choose_action(state)

        # 3. Apply action (handled by the system)

        # 4. Compute reward based on user outcome (success/failure)
        # You must set 'gain' lower for failed runs and higher for successful runs in user_action_metrics
        G = user_action_metrics.get("gain", 1.0)  # e.g., 1.0 for success, 0.0 for failure
        C = user_action_metrics.get("cost", 0.1)
        D = user_action_metrics.get("disengagement", 0.05)
        R = self.reward_optimization(G, C)
        E = logs.get("engagement", 0)
        new_E = self.engagement_dynamics(E, R, D)
        logs["engagement"] = new_E

        # 5. Get next state
        next_state = self.get_state(logs)

        # 6. Update Q-table
        self.update_q_table(state, action, R, next_state)
        self.save_q_table()  # Save after each update (or batch for efficiency)

        # 7. Return chosen action and updated logs
        return action, logs

    def save_q_table(self, filepath="q_table.pkl"):
        with open(filepath, "wb") as f:
            pickle.dump(dict(self.q_table), f)

    def load_q_table(self, filepath="q_table.pkl"):
        try:
            with open(filepath, "rb") as f:
                q_table = pickle.load(f)
                self.q_table = defaultdict(lambda: {a: 0.0 for a in self.actions}, q_table)
        except FileNotFoundError:
            pass  # Start fresh if no file exists

def evaluate_logs(logs, total_testcases=10, expected_time=300, max_difficulty=5, max_skill=1.0):
    performance = logs.get("passed_testcases", 0) / total_testcases
    time_taken = min(logs.get("time_taken", 0) / expected_time, 2.0)
    engagement = min(logs.get("num_actions", 0) / 10, 1.0)  # Example normalization
    difficulty = (logs.get("difficulty", 1) - 1) / (max_difficulty - 1)
    proficiency = min(logs.get("proficiency", 0) / max_skill, 1.0)
    return performance, time_taken, engagement, difficulty, proficiency