import PropTypes from 'prop-types';

export default function Card({ title, kicker, action, children }) {
  return (
    <section className="card">
      <header className="card__header">
        <div>
          {kicker && <p className="kicker">{kicker}</p>}
          <h3>{title}</h3>
        </div>
        {action && <div className="card__action">{action}</div>}
      </header>
      <div className="card__body">{children}</div>
    </section>
  );
}

Card.propTypes = {
  title: PropTypes.string.isRequired,
  kicker: PropTypes.string,
  action: PropTypes.node,
  children: PropTypes.node.isRequired,
};
