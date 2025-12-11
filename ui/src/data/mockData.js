export const defaultPlugins = [
  {
    id: 'pitch-track',
    name: 'Pitch Tracker',
    description: 'Detects fundamental frequency contours for monophonic sources with optional smoothing.',
    category: 'Pitch',
    tags: ['monophonic', 'real-time'],
    parameters: {
      smoothing: 0.6,
      hopSize: 512,
      window: 'Hann',
    },
  },
  {
    id: 'mel-spectrogram',
    name: 'Mel Spectrogram',
    description: 'Generates a mel-frequency spectrogram suitable for machine learning front-ends.',
    category: 'Spectral',
    tags: ['analysis', 'dense'],
    parameters: {
      fftSize: 2048,
      melBands: 96,
      overlap: 0.5,
    },
  },
  {
    id: 'onset-detector',
    name: 'Onset Detector',
    description: 'High-resolution onset curve with dynamic thresholding for transient-heavy material.',
    category: 'Timing',
    tags: ['transients', 'streaming'],
    parameters: {
      sensitivity: 0.55,
      adaptivity: 0.25,
      lookaheadMs: 25,
    },
  },
];

export const demoJobs = [
  {
    id: 'demo-job-1',
    name: 'Violin phrase A3',
    source: 'samples/violin.wav',
    plugin: 'Pitch Tracker',
    status: 'complete',
    summary: '45 s • 44100 Hz • 16-bit PCM',
    updated: '2m ago',
  },
  {
    id: 'demo-job-2',
    name: 'Podcast intro FX',
    source: 'samples/podcast-intro.wav',
    plugin: 'Onset Detector',
    status: 'processing',
    summary: '10 s • stereo • 48 kHz',
    updated: 'live',
  },
];
