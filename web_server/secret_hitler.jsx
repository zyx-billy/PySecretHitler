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

class App extends React.Component {
    constructor(props) {
        super(props);
        this.on_user_choice = this.on_user_choice.bind(this);
        this.ws = null;
        this.state = {
            ws_connected: true,
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
        self.game_id = game_id;
    }

    update_player_id(player_id) {
        set_cookie("player_id", player_id);
        self.player_id = player_id;
    }

    /* component-facing functions */
    async on_user_choice(choice) {
        console.log("sending user choice: " + choice);
        this.ws.send(choice);
    }

    render() {
        var connection_indicator_class = "connection-indicator";
        if (!this.state.ws_connected)
            connection_indicator_class += " lost-connection";
        return (
            <div className="app">
                <h1>Secret Hitler<span className={connection_indicator_class}></span></h1>
                <ProgressBoard name="Liberal" powers={["", "", "", "", ""]} />
                <ProgressBoard name="Fascist" powers={["", "execute a player", "view something"]} />
                <TileDeck name="Unused Tiles" size={0} />
                <TileDeck name="Discarded Tiles" size={0} />
                <PlayerContainer names={["alice", "bob", "charlie", "david"]} />
                <UserChoiceSelector
                    on_user_choice={this.on_user_choice}
                    prompt="vote for chancellor"
                    choices={["ja","nein","what?"]} />
            </div>
        );
    }
}

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
    constructor(props) { // name, powers
        super(props);
    }

    render() {
        const slots = this.props.powers.map((power, idx) =>
            <ProgressSlot power={power} key={idx.toString()} />
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
    constructor(props) { // name, position
        super(props);
    }

    render() {
        return (
            <div className={"player-info position-" + this.props.position}>
                {this.props.name}
            </div>
        );
    }
}

class PlayerContainer extends React.Component {
    constructor(props) { // names
        super(props);
        this.state = {
            president: 0,
            chancellor: -1
        };
    }

    render() {
        const players = this.props.names.map((name, idx) => {
            var position = PositionEnum.none;
            if (idx == this.state.president)
                position = PositionEnum.president;
            else if (idx == this.state.chancellor)
                position = PositionEnum.chancellor;
            return <PlayerInfo name={name} position={position} key={idx.toString()} />
        });
        return (
            <div>
                Players:
                <div className="player-container">
                    {players}
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
