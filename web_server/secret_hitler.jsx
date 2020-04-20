class App extends React.Component {
    constructor(props) {
        super(props);
        this.on_user_choice = this.on_user_choice.bind(this);
    }

    async on_user_choice(choice) {
        console.log("received user choice: " + choice);
    }

    render() {
        return (
            <div className="app">
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
