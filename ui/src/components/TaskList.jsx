import PropTypes from 'prop-types';

const statusColor = {
  complete: 'var(--green-500)',
  processing: 'var(--amber-400)',
  queued: 'var(--indigo-400)',
  idle: 'var(--muted)',
};

export default function TaskList({ tasks }) {
  return (
    <ul className="task-list">
      {tasks.map((task) => (
        <li key={task.id} className="task-item">
          <span
            className="status-dot"
            style={{ backgroundColor: statusColor[task.status] || statusColor.idle }}
            aria-label={task.status}
          />
          <div>
            <p className="task-title">{task.name}</p>
            <p className="task-meta">
              {task.plugin} • {task.source} • {task.summary}
            </p>
          </div>
          <p className="task-updated">{task.updated}</p>
        </li>
      ))}
    </ul>
  );
}

TaskList.propTypes = {
  tasks: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      plugin: PropTypes.string.isRequired,
      source: PropTypes.string,
      summary: PropTypes.string,
      updated: PropTypes.string,
      status: PropTypes.string,
    })
  ).isRequired,
};
