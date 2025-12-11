export async function fetchPlugins() {
  try {
    const response = await fetch('/api/plugins');
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }
    const payload = await response.json();
    if (!Array.isArray(payload)) {
      throw new Error('Plugin payload must be an array');
    }
    return payload;
  } catch (error) {
    console.info('Falling back to bundled plugin definitions', error);
    return null;
  }
}

export async function submitAnalysis(requestBody) {
  try {
    const response = await fetch('/api/analyse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const payload = await response.json();
    if (!payload?.id) {
      throw new Error('Missing job id in response');
    }

    return payload;
  } catch (error) {
    console.info('Using local task simulation; hook up your Python binding to replace this.', error);
    return {
      id: `job-${Date.now()}`,
      accepted: true,
      status: 'queued',
    };
  }
}
