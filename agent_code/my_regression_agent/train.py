import pickle
import random
from collections import namedtuple, deque
from typing import List
import numpy as np
import collections
from matplotlib import pyplot as plt

import events as e
from .callbacks import state_to_features

# This is only an example!
Transition = namedtuple('Transition',
                        ('state', 'action', 'next_state', 'reward'))

# Hyper parameters -- DO modify
# TODO: modify
TRANSITION_HISTORY_SIZE = 1000  # keep only ... last transitions
RECORD_ENEMY_TRANSITIONS = 1.0  # record enemy transitions with probability ...
BATCH_SIZE=20
GAMMA = 0.95
LEARNING_RATE = 0.001
# Events
# TODO: zusätzliche events?
DISTANCE_2 = "DISTANCE_2"
DISTANCE_1 = "DISTANCE_1"
DISTANCE_0 = "DISTANCE_0"


def setup_training(self):
    """
    Initialise self for training purpose.

    This is called after `setup` in callbacks.py.

    :param self: This object is passed to all callbacks and you can set arbitrary values.
    """
    # Example: Setup an array that will note transition tuples
    # (s, a, r, s')
    self.transitions = deque(maxlen=TRANSITION_HISTORY_SIZE)
    self.last_positions = deque(maxlen=5)
    self.actions = {'UP': 0, 'RIGHT':1, 'DOWN':2, 'LEFT':3, 'WAIT':4, 'BOMB':5}
    self.all_rewards = []


def game_events_occurred(self, old_game_state: dict, self_action: str, new_game_state: dict, events: List[str]):
    """
    Called once per step to allow intermediate rewards based on game events.

    When this method is called, self.events will contain a list of all game
    events relevant to your agent that occurred during the previous step. Consult
    settings.py to see what events are tracked. You can hand out rewards to your
    agent based on these events and your knowledge of the (new) game state.

    This is *one* of the places where you could update your agent.

    :param self: This object is passed to all callbacks and you can set arbitrary values.
    :param old_game_state: The state that was passed to the last call of `act`.
    :param self_action: The action that you took.
    :param new_game_state: The state the agent is in now.
    :param events: The events that occurred when going from  `old_game_state` to `new_game_state`
    """
    self.logger.debug(f'Encountered game event(s) {", ".join(map(repr, events))} in step {new_game_state["step"]}')

    # Idea: Add your own events to hand out rewards
    # TODO: own events?
    current_pos = new_game_state['self'][3]

    t=0
    if len(self.last_positions) == 5:
        dis_2 = np.sqrt((self.last_positions[2][0] - current_pos[0])**2 + (self.last_positions[2][1] - current_pos[1])**2)
        dis_1 = np.sqrt(
            (self.last_positions[1][0] - current_pos[0]) ** 2 + (self.last_positions[1][1] - current_pos[1]) ** 2)
        dis_0 = np.sqrt(
            (self.last_positions[0][0] - current_pos[0]) ** 2 + (self.last_positions[0][1] - current_pos[1]) ** 2)
        if dis_2 < 1:
            events.append(DISTANCE_2)
        if dis_1 < 2:
            events.append(DISTANCE_1)
        if dis_0 < 3:
            events.append(DISTANCE_0)
    self.last_positions.append(current_pos)

    reward = reward_from_events(self, events)
    self.all_rewards.append(reward)
    if self_action:
        self.transitions.append(Transition(state_to_features(old_game_state), self_action, state_to_features(new_game_state), reward))


def end_of_round(self, last_game_state: dict, last_action: str, events: List[str]):
    """
    Called at the end of each game or when the agent died to hand out final rewards.

    This is similar to reward_update. self.events will contain all events that
    occurred during your agent's final step.

    This is *one* of the places where you could update your agent.
    This is also a good place to store an agent that you updated.

    :param self: The same object that is passed to all of your callbacks.
    """
    self.logger.debug(f'Encountered event(s) {", ".join(map(repr, events))} in final step')
    reward = reward_from_events(self, events)
    self.all_rewards.append(reward)
    self.transitions.append(Transition(state_to_features(last_game_state), last_action, None, reward))
    if len(self.transitions) < BATCH_SIZE:
        return
    batch = random.sample(self.transitions, int(len(self.transitions) / 1))
    X = []
    targets = []
    for state, action, state_next, reward in batch:
        q_update = reward
        q_values = []
        if self.is_fit:
            q_values = self.model.predict([state])
        else:
            q_values = np.zeros(6).reshape(1, -1)

        if state_next is not None:
            if self.is_fit:
                #q_update = (reward + GAMMA * np.amax(self.model.predict(state_next)[0]))
                q_value = q_values[0][self.actions[action]]
                new_q_value = np.max(self.model.predict([state_next]))
                q_update = q_value + LEARNING_RATE * (reward + GAMMA * new_q_value - q_value)
            else:
                q_update = reward


        q_values[0][self.actions[action]] = q_update

        # print(state)
        # print(action)
        # print(q_values)
        X.append(state)
        targets.append(q_values[0])
    # print(X)
    # print(targets)
    self.model.fit(X, targets)
    self.isFit = True


    # save statistic
    #plt.plot(self.all_rewards);
    #plt.savefig("rewards_per_step")
    #plt.xlabel("step")
    #plt.ylabel("reward")
    with open("statistics", "a") as f:
        for reward in self.all_rewards:
            f.writelines(str(reward)+ "\n")
    self.all_rewards = []
    # Store the model
    with open("jessi-saved-model.pt", "wb") as file:
        pickle.dump(self.model, file)


def reward_from_events(self, events: List[str]) -> int:
    """
    *This is not a required function, but an idea to structure your code.*

    Here you can modify the rewards your agent get so as to en/discourage
    certain behavior.
    """
    game_rewards = {
        e.MOVED_LEFT: -1,
        e.MOVED_RIGHT: -1,
        e.MOVED_UP: -1,
        e.MOVED_DOWN: -1,
        e.WAITED: -10,
        e.INVALID_ACTION: -10,
        e.BOMB_EXPLODED: 0,
        e.BOMB_DROPPED: 0,
        e.CRATE_DESTROYED: 0,
        e.COIN_FOUND: 10,
        e.COIN_COLLECTED: 1000,
        e.KILLED_OPPONENT: 0,
        e.KILLED_SELF: 0,
        e.GOT_KILLED: 0,
        e.OPPONENT_ELIMINATED: 0,
        e.SURVIVED_ROUND: 0,
        DISTANCE_2: -10,
        DISTANCE_1: -20,
        DISTANCE_0: -30
    }
    reward_sum = 0
    for event in events:
        if event in game_rewards:
            reward_sum += game_rewards[event]
    self.logger.info(f"Awarded {reward_sum} for events {', '.join(events)}")
    return reward_sum