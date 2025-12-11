import PropTypes from 'prop-types';

export default function PluginGrid({ plugins, selectedId, onSelect }) {
  return (
    <div className="plugin-grid">
      {plugins.map((plugin) => {
        const active = plugin.id === selectedId;
        return (
          <button
            key={plugin.id}
            type="button"
            className={`plugin-card ${active ? 'plugin-card--active' : ''}`}
            onClick={() => onSelect(plugin.id)}
          >
            <div className="plugin-card__row">
              <span className="pill">{plugin.category}</span>
              <span className="pill pill--subtle">{plugin.tags.join(' • ')}</span>
            </div>
            <h4>{plugin.name}</h4>
            <p className="plugin-card__description">{plugin.description}</p>
            <div className="plugin-card__parameters">
              {Object.entries(plugin.parameters).map(([key, value]) => (
                <span key={key} className="param-pill">
                  <strong>{key}</strong>
                  <span>{String(value)}</span>
                </span>
              ))}
            </div>
          </button>
        );
      })}
    </div>
  );
}

PluginGrid.propTypes = {
  plugins: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      category: PropTypes.string,
      description: PropTypes.string,
      tags: PropTypes.arrayOf(PropTypes.string),
      parameters: PropTypes.object,
    })
  ).isRequired,
  selectedId: PropTypes.string,
  onSelect: PropTypes.func.isRequired,
};
