function set_cookie(key, val) {
    var d = new Date();
    d.setTime(d.getTime() + (24*60*60*1000)); // expire after 1 day
    const expires = "expires="+ d.toUTCString();
    document.cookie = key.concat("=", val, "; ", expires);
}

function get_cookie(key) {
    var decodedCookie = decodeURIComponent(document.cookie);
    var cs = decodedCookie.split(';');
    for(var i = 0; i < cs.length; i++) {
        var pair = cs[i].split("=", 2);
        if (key === pair[0].trim()) {
            return pair[1].trim();
        }
    }
    return null;
}

const AppStatus = Object.freeze({"new_or_join":"new_or_join", "awaiting_begin":"awaiting_begin", "begun":"begun"})

class App extends React.Component {
    constructor(props) {
        super(props);
        this.ws = null;
        this.state = {
            ws_connected: true,
            status: AppStatus.new_or_join,
            /* player state */
            identity: undefined,
            prompt: undefined,
            /* board state */
            players: [],
            eliminated_players: [],
            president: undefined,
            chancellor: undefined,
            nominated_chancellor: null,
            unused_tiles: undefined,
            discarded_tiles: undefined,
            drawn_tiles: undefined,
            liberal_progress: 0,
            fascist_progress: 0,
            fascist_powers: undefined
        }
        this.game_id = undefined;
        this.player_id = undefined;
        this.is_host = false;

        this.on_user_choice = this.on_user_choice.bind(this);
        this.on_new_game_submit = this.on_new_game_submit.bind(this);
        this.on_join_game_submit = this.on_join_game_submit.bind(this);
        this.on_begin_game_submit = this.on_begin_game_submit.bind(this);
    }

    componentDidMount() {
        this.connect();
    }

    /* WebSocket comms functions */
    connect() {
        if (ws && ws.readyState !== WebSocket.CLOSED) return;

        var ws = new WebSocket("ws://" + location.host + "/ws");
        const timeout = 250;
        var connectInterval;
        
        ws.onopen = () => {
            console.log("WebSocket connection established");
            this.ws = ws;
            this.setState({ws_connected: true});
            clearTimeout(connectInterval);
            // reconnection logic
            const game_id = this.game_id || get_cookie("game_id");
            const player_id = this.player_id || get_cookie("player_id");
            if (get_cookie("game_id") && get_cookie("player_id")) {
                ws.send(JSON.stringify({
                    type: "reconnect",
                    game_id: get_cookie("game_id"),
                    player_id: get_cookie("player_id")
                }));
                this.update_game_id(game_id);
                this.update_player_id(player_id);
            }
        };

        ws.onclose = (e) => {
            console.log("WebSocket connection closed. Reconnecting ...");
            this.setState({ws_connected: false});
            connectInterval = setTimeout(this.connect.bind(this), timeout);
        };

        ws.onerror = (e) => {
            console.error("WebSocket error. Will Retry.");
            ws.close();
        }

        ws.onmessage = this.handle_server_update;
    }

    /* ws comms semantics */
    handle_server_update(message) {
        console.log("Received message:\n" + message.data);
        const data = JSON.parse(message.data);
        // TODO: error handling
        if (data.type === "game_id") {
            this.update_game_id(data.game_id);
        } else if (data.type === "player_id") {
            this.update_player_id(data.player_id);
            this.setState({
                status: AppStatus.awaiting_begin
            });
        } else if (data.type == "game_begun") {
            this.setState({
                status: AppStatus.begun
            });
        } else if (data.type === "prompt") {
            this.setState({
                prompt: {
                    action: prompt.action,
                    prompt: prompt.prompt,
                    choices: prompt.choices
                }
            });
        } else if (data.type === "state_update") {
            this.setState(data.updates);
        } else if (data.type === "error") {
            console.log("[Server Error]: " + data.msg);
        } else if (data.type === "success") {
            console.log("[Success]: " + data.msg);
        } else {
            console.log("Unrecognized response type: " + data.type);
        }
    }

    update_game_id(game_id) {
        set_cookie("game_id", game_id);
        this.game_id = game_id;
    }

    update_player_id(player_id) {
        set_cookie("player_id", player_id);
        this.player_id = player_id;
    }

    /* component-facing functions */
    async on_user_choice(choice) {
        console.log("sending user choice: " + choice);
        this.ws.send(choice);
    }

    on_new_game_submit(host) {
        this.is_host = true;
        this.ws.send(JSON.stringify({
            type: "new_game",
            host: host
        }));
    }

    on_join_game_submit(game_id, player_name) {
        this.ws.send(JSON.stringify({
            type: "join_game",
            game_id: game_id,
            player_id: player_id
        }));
    }

    on_begin_game_submit() {
        this.ws.send(JSON.stringify({
            type: "begin_game"
        }));
    }

    render() {
        var connection_indicator_class = "connection-indicator";
        if (!this.state.ws_connected)
            connection_indicator_class += " lost-connection";
        
        if (this.state.status === AppStatus.new_or_join) {
            return (
                <div className="pre-game">
                    <h1>Welcome to Secret Hitler<span className={connection_indicator_class}></span></h1>
                    <p>Please create a new game or join an existing game:</p>
                    <NewOrJoinForms
                        on_new_game_submit={this.on_new_game_submit}
                        on_join_game_submit={this.on_join_game_submit} />
                </div>
            );
        }

        if (this.state.status === AppStatus.awaiting_begin) {
            return (
                <div className="pre-game">
                    <h1>Welcome to Secret Hitler<span className={connection_indicator_class}></span></h1>
                    <p>Waiting for users to join:</p>
                    <WaitingRoomPlayers
                        is_host={this.is_host}
                        players={this.state.players}
                        on_begin_game_submit={this.on_begin_game_submit} />
                </div>
            );
        }
        
        return (
            <div className="game">
                <h1>Secret Hitler<span className={connection_indicator_class}></span></h1>
                <ProgressBoard
                    name="Liberal"
                    powers={["","","","",""]}
                    progress={this.state.liberal_progress} />
                <ProgressBoard
                    name="Fascist"
                    powers={this.state.fascist_powers}
                    progress={this.state.fascist_progress} />
                <TileDeck name="Unused Tiles" size={this.state.unused_tiles} />
                <TileDeck name="Discarded Tiles" size={this.state.discarded_tiles} />
                <PlayerContainer
                    live_players={this.state.players}
                    dead_players={this.state.eliminated_players} />
                <UserChoiceSelector
                    on_user_choice={this.on_user_choice}
                    prompt={this.state.prompt.prompt}
                    choices={this.state.prompt.choices} />
            </div>
        );
    }
}

/* Pre-Game */
class NewOrJoinForms extends React.Component {
    constructor(props) { // on_new_game_submit, on_join_game_submit
        super(props);
        this.state = {
            new_game_host: "",
            join_game_id: "",
            player_name: "",
            submitted: false
        };

        this.handleChange = this.handleChange.bind(this);
        this.handleSubmit = this.handleSubmit.bind(this);
    }

    handleChange(event) {
        const target = event.target;
        this.setState({
            [target.name]: target.value
        });
    }

    handleSubmit(event) {
        const target_name = event.target.name;
        if (target_name === "new-form") {
            this.setState({submitted: true});
            console.log("Creating a new game by: " + this.state.new_game_host);
            this.props.on_new_game_submit(this.state.new_game_host);
        } else if (target_name == "join-form") {
            this.setState({submitted: true});
            console.log("Joining game: " + this.state.join_game_id + ", for player: " + this.state.player_name);
            this.props.on_join_game_submit(this.state.join_game_id, this.state.player_name);
        }
        event.preventDefault();
    }

    render() {
        return (
            <div className="new-or-join">
                <div className="new-form-wrapper">
                    <p>Create New Game:</p>
                    <form onSubmit={this.handleSubmit} name="new-form">
                        <label>
                        Player Name:
                        <input type="text"
                            name="new_game_host"
                            value={this.state.new_game_host}
                            onChange={this.handleChange} />
                        </label>
                        <input type="submit" value="Create" disabled={this.state.submitted} />
                    </form>
                </div>
                <div className="join-form-wrapper">
                    <p>Join Existing Game:</p>
                    <form onSubmit={this.handleSubmit} name="join-form">
                        <label>
                        Game ID:
                        <input type="text"
                            name="join_game_id"
                            value={this.state.join_game_id}
                            onChange={this.handleChange} />
                        </label>
                        <label>
                        Player Name:
                        <input type="text"
                            name="player_name"
                            value={this.state.player_name}
                            onChange={this.handleChange} />
                        </label>
                        <input type="submit" value="Join" disabled={this.state.submitted} />
                    </form>
                </div>
            </div>
        );
    }
}

class WaitingRoomPlayers extends React.Component {
    constructor(props) { // is_host, players, on_begin_game_submit
        super(props);
        this.state = {
            submitted: false
        }
        this.handleSubmit = this.handleSubmit.bind(this);
    }

    handleSubmit(event) {
        console.log("Starting game!");
        this.setState({submitted: true});
        this.props.on_begin_game_submit();
        event.preventDefault();
    }

    render() {
        const players = this.props.players.map((name) => {
            <span>name</span>
        });
        const conditional_begin_game_button = this.props.is_host ? (
            <form onSubmit={this.handleSubmit} name="">
                <input type="submit" value="Start Game!" disabled={this.state.submitted} />
            </form>
        ) : "";
        return (
            <div className="waiting-room">
                <p>Users online:</p>
                <p>{players}</p>
                {conditional_begin_game_button}
            </div>
        );
    }
}


/* Game Proper */
class ProgressSlot extends React.Component {
    constructor(props) { // power, filled
        super(props);
    }

    render() {
        var classes = "progress-slot";
        if (this.props.filled)
            classes += " filled";
        return (
            <div className={classes}>
                <p>{this.props.power}</p>
            </div>
        );
    }
}

class ProgressBoard extends React.Component {
    constructor(props) { // name, powers, progress
        super(props);
    }

    render() {
        const slots = this.props.powers.map((power, idx) =>
            <ProgressSlot
                key={idx.toString()}
                power={power}
                filled={idx < this.props.progress} />
        );
        return (
            <div className={"progress-board " + this.props.name}>
                <div className="board-title">{this.props.name} Board</div>
                <div className="slots-container">
                    {slots}
                </div>
            </div>
        );
    }
}

class TileDeck extends React.Component {
    constructor(props) { // name, size
        super(props);
    }

    render() {
        return (
            <div className="tiledeck">
                {this.props.name}: {this.props.size}
            </div>
        );
    }
}

const PositionEnum = Object.freeze({"none":"none", "president":"president", "chancellor":"chancellor"})
class PlayerInfo extends React.Component {
    constructor(props) { // name, alive, position
        super(props);
    }

    render() {
        let classes = "player-info position-" + this.props.position;
        if (!this.props.alive)
            classes += " eliminated";
        return (
            <div className={classes}>
                {this.props.name}
            </div>
        );
    }
}

class PlayerContainer extends React.Component {
    constructor(props) { // live_players, dead_players
        super(props);
        this.state = {
            president: 0,
            chancellor: -1
        };
    }

    render() {
        const alives = this.props.live_players.map((name, idx) => {
            var position = PositionEnum.none;
            if (idx == this.state.president)
                position = PositionEnum.president;
            else if (idx == this.state.chancellor)
                position = PositionEnum.chancellor;
            return <PlayerInfo name={name} position={position} alive={true} key={name} />
        });
        const deads = this.props.dead_players.map((name) => {
            return <PlayerInfo name={name} alive={false} key={name} />
        });
        return (
            <div>
                Players:
                <div className="player-container">
                    {alives}
                    {deads}
                </div>
            </div>
        );
    }
}

class UserChoiceItem extends React.Component {
    constructor(props) { // choice, is_selected, on_select
        super(props);
        this.on_self_selected = this.on_self_selected.bind(this);
    }

    on_self_selected() {
        this.props.on_select(this.props.choice)
    }

    render() {
        var classes = "user-choice-item";
        if (this.props.is_selected)
            classes += " selected"
        return (
            <div className={classes} onClick={this.on_self_selected}>
                {this.props.choice}
            </div>
        );
    }
}

class UserChoiceSelector extends React.Component {
    constructor(props) { // on_user_choice, prompt, choices
        super(props);
        this.on_child_selected = this.on_child_selected.bind(this);
        this.on_submit = this.on_submit.bind(this);
        this.state = {
            selected: undefined,
            submission: undefined
        };
    }

    on_child_selected(key) {
        this.setState({
            selected: key
        });
    }

    on_submit() {
        this.setState((state, props) => {
            this.props.on_user_choice(state.selected);
            return {submission: state.selected};
        });
        
    }

    render() {
        const selections = this.props.choices.map((choice) =>
            <UserChoiceItem
                key={choice}
                choice={choice}
                is_selected={choice === this.state.selected}
                on_select={this.on_child_selected} />
        );
        
        return (
        <div className="user-choice-selector">
            <div>{this.props.prompt}</div>
            {this.state.submission === undefined
              ? <div className="item-container">{selections}</div>
              : <div>You have selected {this.state.submission}</div>
            }
            <button
                type="button"
                onClick={this.on_submit}
                disabled={this.state.selected === undefined || this.state.submission !== undefined}>
                    Submit
            </button>
        </div>
        );
    }
}

ReactDOM.render(
    <App />,
    document.getElementById("root")
);
