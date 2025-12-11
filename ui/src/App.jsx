import { useEffect, useMemo, useState } from 'react';
import Card from './components/Card.jsx';
import PluginGrid from './components/PluginGrid.jsx';
import TaskList from './components/TaskList.jsx';
import { defaultPlugins, demoJobs } from './data/mockData.js';
import { fetchPlugins, submitAnalysis } from './services/api.js';

export default function App() {
  const [plugins, setPlugins] = useState(defaultPlugins);
  const [selectedPluginId, setSelectedPluginId] = useState(defaultPlugins[0].id);
  const [analysisParams, setAnalysisParams] = useState({
    sensitivity: 0.58,
    hopSize: 512,
    channels: 'stereo',
    smoothing: 0.5,
    notes: 'Ready to forward to Python bridge.',
  });
  const [tasks, setTasks] = useState(demoJobs);
  const [sourceFile, setSourceFile] = useState(null);
  const [statusMessage, setStatusMessage] = useState('Waiting for input');

  useEffect(() => {
    let cancelled = false;
    fetchPlugins().then((remotePlugins) => {
      if (!cancelled && Array.isArray(remotePlugins) && remotePlugins.length) {
        setPlugins(remotePlugins);
        setSelectedPluginId(remotePlugins[0].id);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const selectedPlugin = useMemo(
    () => plugins.find((plugin) => plugin.id === selectedPluginId),
    [plugins, selectedPluginId]
  );

  const updateParam = (name, value) => {
    setAnalysisParams((current) => ({ ...current, [name]: value }));
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    setSourceFile(file ?? null);
  };

  const enqueueTask = async () => {
    const requestBody = {
      plugin: selectedPlugin?.id,
      parameters: analysisParams,
      source: sourceFile?.name ?? 'Live input / remote source',
    };

    const response = await submitAnalysis(requestBody);
    const newTask = {
      id: response.id,
      name: sourceFile?.name ?? 'Live stream',
      source: requestBody.source,
      plugin: selectedPlugin?.name ?? 'Unknown plugin',
      status: response.status ?? 'queued',
      summary: 'Awaiting processing…',
      updated: 'just now',
    };

    setStatusMessage('Queued analysis; hand-off ready for your Python bridge.');
    setTasks((current) => [newTask, ...current]);

    setTimeout(() => {
      setTasks((current) =>
        current.map((task) =>
          task.id === newTask.id ? { ...task, status: 'processing', summary: 'Processing frames…' } : task
        )
      );
    }, 800);

    setTimeout(() => {
      setTasks((current) =>
        current.map((task) =>
          task.id === newTask.id
            ? { ...task, status: 'complete', summary: 'Complete • tap to open in Sonic Visualiser' }
            : task
        )
      );
    }, 1800);
  };

  return (
    <main className="page">
      <header className="page__header">
        <div>
          <p className="eyebrow">React control surface</p>
          <h1>Sonic Visualiser UI</h1>
          <p className="lede">
            Prototype React dashboard wired for a Python-friendly API layer. Drop in your bindings and
            route analysis jobs directly into the C++ engine.
          </p>
          <div className="badge-row">
            <span className="pill">Ready for local or remote sources</span>
            <span className="pill">Plugin-aware</span>
            <span className="pill">Mock data bundled</span>
          </div>
        </div>
        <div className="status-card">
          <p className="kicker">Status</p>
          <p className="status-card__value">{statusMessage}</p>
          <p className="status-card__note">Connect /api/plugins and /api/analyse to your Python bridge.</p>
        </div>
      </header>

      <div className="grid">
        <Card
          title="1. Choose audio source"
          kicker="Input"
          action={<span className="pill pill--subtle">Optional drag-and-drop</span>}
        >
          <div className="file-picker">
            <label className="file-picker__drop" htmlFor="fileInput">
              <strong>{sourceFile ? sourceFile.name : 'Select or drop an audio file'}</strong>
              <span>WAV, MP3, AIFF • routed to Python for decoding</span>
            </label>
            <input id="fileInput" type="file" accept="audio/*" onChange={handleFileChange} />
            <div className="file-picker__notes">
              <span className="pill">Live streams supported via API</span>
              <span className="pill">Network paths ok</span>
            </div>
          </div>
        </Card>

        <Card title="2. Select analysis plugin" kicker="Vamp / custom">
          <PluginGrid plugins={plugins} selectedId={selectedPluginId} onSelect={setSelectedPluginId} />
        </Card>

        <Card
          title="3. Configure parameters"
          kicker="Tweak before sending"
          action={<button className="ghost-button" onClick={enqueueTask}>Queue analysis</button>}
        >
          <div className="controls">
            <label>
              <span>Detection sensitivity</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={analysisParams.sensitivity}
                onChange={(event) => updateParam('sensitivity', Number(event.target.value))}
              />
              <em>{Math.round(analysisParams.sensitivity * 100)}%</em>
            </label>
            <label>
              <span>Hop size</span>
              <input
                type="number"
                value={analysisParams.hopSize}
                onChange={(event) => updateParam('hopSize', Number(event.target.value))}
              />
            </label>
            <label>
              <span>Channels</span>
              <select
                value={analysisParams.channels}
                onChange={(event) => updateParam('channels', event.target.value)}
              >
                <option value="mono">Mono</option>
                <option value="stereo">Stereo</option>
                <option value="surround">Surround</option>
              </select>
            </label>
            <label>
              <span>Smoothing</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={analysisParams.smoothing}
                onChange={(event) => updateParam('smoothing', Number(event.target.value))}
              />
              <em>{Math.round(analysisParams.smoothing * 100)}%</em>
            </label>
            <label className="notes">
              <span>Notes for Python binding</span>
              <textarea
                rows="3"
                value={analysisParams.notes}
                onChange={(event) => updateParam('notes', event.target.value)}
              />
            </label>
          </div>
        </Card>

        <Card title="Task queue" kicker="Recent submissions">
          <TaskList tasks={tasks} />
        </Card>

        <Card title="Preview" kicker="Latest analysis">
          {selectedPlugin ? (
            <div className="preview">
              <div>
                <p className="kicker">Plugin</p>
                <strong>{selectedPlugin.name}</strong>
                <p className="dimmed">{selectedPlugin.description}</p>
              </div>
              <div>
                <p className="kicker">Parameters</p>
                <ul className="preview__params">
                  {Object.entries(analysisParams).map(([key, value]) => (
                    <li key={key}>
                      <span>{key}</span>
                      <strong>{String(value)}</strong>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="kicker">Bridge</p>
                <p className="dimmed">
                  Hook this panel up to your Python binding to send JSON payloads with the structure shown
                  above.
                </p>
              </div>
            </div>
          ) : (
            <p>Select a plugin to see its details.</p>
          )}
        </Card>
      </div>
    </main>
  );
}
