import pygame

from Environment import Env
from components.my_bot import MyBot
from components.character import Character

screen = pygame.display.set_mode((800, 800))

def main():
    # Environment parameters.
    world_width = 1280
    world_height = 1280
    display_width = 800
    display_height = 800
    n_of_obstacles  = 25

    load_back = True
    state_size = 34

    # Create the environment with frame skipping for faster training
    env = Env(training=True,
              use_game_ui=False,
              world_width=world_width,
              world_height=world_height,
              display_width=display_width,
              display_height=display_height,
              n_of_obstacles=n_of_obstacles,
              frame_skip=8)  # Use frame skipping to accelerate training
    screen = env.world_surface
    world_bounds = env.get_world_bounds()

    # Setup two players (characters) with starting positions.
    # The players will be stuck if closer than 5 pixels to the border.
    players = [
        Character((world_bounds[2] - 100, world_bounds[3] - 100),
                  screen, boundaries=world_bounds, username="Ninja"),
        Character((world_bounds[0] + 10, world_bounds[1]+10),
                  screen, boundaries=world_bounds, username="Faze Jarvis")
    ]

    # Define the state size based on the info returned by get_info().
    # In this example, we assume:
    #   - location: 2 values
    #   - rotation: 1 value
    #   - current_ammo: 1 value
    #   - rays: 8 values (adjust as needed)
    # Total state size = 2 + 1 + 1 + 8 = 12


    bots = [MyBot(action_size=56), MyBot(action_size=56)]

    if load_back:
        for idx, bot in enumerate(bots):
            save_path = f"bot_model_{idx}.pth"
            try:
                bot.load(save_path)
                print(f"Load model for player {players[idx].username} from {save_path}")
            except:
                print(f"Failed to load model for player {players[idx].username} from {save_path}")

    # Link players, bots, and obstacles into the environment.
    env.set_players_bots_objects(players, bots)

    # Training / Game parameters.
    tick_limit = 1200  # Reduced ticks per episode since we're using frame skipping (8x faster)
    num_epochs = 500  # Increased number of episodes for more thorough training

    # Track rewards for monitoring learning progress
    episode_rewards = {player.username: [] for player in players}
    avg_rewards = {player.username: [] for player in players}

    for epoch in range(num_epochs):
        print(f"Starting epoch {epoch + 1}/{num_epochs}")
        env.reset(randomize_objects=True)
        # Reset the step counter at the beginning of each episode
        env.steps = 0

        # Reset episode rewards
        current_episode_rewards = {player.username: 0 for player in players}

        while True:
            # If the tick limit for this episode has been reached, break.
            if env.steps > tick_limit:
                print("Tick limit reached for this episode.")
                break

            # Take a step in the environment.
            # The environment calls each player's .act() method, which in turn uses the bot.
            finished, info = env.step(debugging=False)

            # For each player, calculate reward, update bot memory, and train the bot.
            for player, bot in zip(players, bots):
                # Calculate the reward for the current step (adjust calculate_reward as needed).
                reward = env.calculate_reward(info, player.username)
                # Accumulate rewards for this episode
                current_episode_rewards[player.username] += reward

                # Retrieve the updated state for the player.
                next_info = player.get_info()
                # Store the transition (last state, action, reward, next state, done).
                bot.remember(reward, next_info, finished)

                # Training is now handled in the remember method based on train_freq

            # If the game/episode is over, break out of the loop.
            if finished:
                print(f"Episode {epoch + 1} finished, took {env.steps} ticks.")
                break

        # Record and display episode rewards
        for player in players:
            episode_rewards[player.username].append(current_episode_rewards[player.username])
            avg_reward = sum(episode_rewards[player.username][-10:]) / min(10, len(episode_rewards[player.username]))
            avg_rewards[player.username].append(avg_reward)
            print(f"Episode {epoch + 1} - {player.username}: Reward = {current_episode_rewards[player.username]:.2f}, Avg(10) = {avg_reward:.2f}, Epsilon = {player.related_bot.epsilon:.4f}")

        # Save the model weights more frequently (every 5 epochs) to prevent loss of progress
        if (epoch + 1) % 5 == 0 or epoch == num_epochs - 1:
            for idx, bot in enumerate(bots):
                save_path = f"bot_model_{idx}.pth"
                bot.save(save_path)
                print(f"Saved model for player {players[idx].username} to {save_path}")

    pygame.quit()

if __name__ == "__main__":
    main()
