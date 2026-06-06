import { NavLink } from "react-router-dom";

export function Header({ onTutorial }: { onTutorial: () => void }) {
  return (
    <header className="topbar">
      <div className="brand">
        CYBER<b>DEFENSE</b> MAS
      </div>
      <nav className="nav">
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/inspector">Agent Inspector</NavLink>
        <NavLink to="/validator">Validator</NavLink>
      </nav>
      <div className="spacer" />
      <button className="btn primary" onClick={onTutorial}>
        ▶ Guided Tour
      </button>
      <span className="live-pill">
        <span className="live-dot" /> SIMULATION ACTIVE
      </span>
    </header>
  );
}
