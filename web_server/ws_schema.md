# Websocket messages

## Types of requests (to server)

### new_game
Create a new game.
- host: string. Name of host user.

### join_game
Join an existing game.
- game_id: string. ID of the game to join.
- player_name: string. Name of the joining player.

### reconnect
Reconnect to a previously connected game.
- game_id: string. ID of the game to reconnect to.
- player_id: string. The previously assigned player_id.

### begin_game
Begin a game

### user_action
Perform a user action.
- action: string. Name of the action to perform.
- choice: string. Argument to the action.

## Types of responses (from server)

### game_id
Informs about the game id of the newly created game.
- game_id: string. ID of the newly created game.

### player_id
Informs of the player_id assigned to the player represented by this client.
- player_id: string. The ID assigned to the player.

### game_begun
Informs of the start of the game.

### is_host
Informs the recipient that they are the host (in case the host re-connected).

### prompt
Prompt for the next action the user need to perform.
- action: string. The name of the action.
- prompt: string. The message describing the action to the user.
- choices: List\[string\]. A list of choices for the user to select one from.

### state_update
Inform about updates to particular fields of the game state.
- updates: Object. Key-value pairs representing the subset of the game state that has been updated.

### error
Inform about an error in executing a previous request from this client.
- msg: string. Description of the error.

### success
Inform about the successful execution of a previous request from this client.
- msg: string. Description of the success.
