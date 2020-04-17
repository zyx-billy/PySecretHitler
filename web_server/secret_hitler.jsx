class App extends React.Component {
    constructor(props) {
        super(props);
    }

    render() {
        return (
            <div className="app">
                <ProgressBoard name="Liberal" powers={["", "", "", "", ""]} />
                <ProgressBoard name="Fascist" powers={["", "execute a player", "view something"]} />
                <TileDeck name="Unused Tiles" size={0} />
                <TileDeck name="Discarded Tiles" size={0} />
                <PlayerContainer names={["alice", "bob", "charlie", "david"]} />
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

ReactDOM.render(
    <App />,
    document.getElementById("root")
);
