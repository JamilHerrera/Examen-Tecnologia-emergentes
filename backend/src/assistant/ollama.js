import { config } from '../config.js';

/** Cliente minimo de Ollama (local): ningun dato sale de la maquina. */
async function post(path, body, timeoutMs = config.ollama.timeoutMs) {
  const res = await fetch(`${config.ollama.url}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) throw new Error(`Ollama respondio ${res.status}`);
  return res.json();
}

export async function ollamaStatus() {
  try {
    const res = await fetch(`${config.ollama.url}/api/tags`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    const installed = (data.models ?? []).some((m) => m.name === config.ollama.model || m.name.startsWith(`${config.ollama.model}:`));
    return { available: installed, model: config.ollama.model, installed };
  } catch {
    return { available: false, model: config.ollama.model, installed: false };
  }
}

export async function chat(messages, { json = false, maxTokens = 400 } = {}) {
  const data = await post('/api/chat', {
    model: config.ollama.model,
    messages,
    stream: false,
    keep_alive: '30m',
    ...(json ? { format: 'json' } : {}),
    options: { temperature: 0.1, num_predict: maxTokens },
  });
  return data.message?.content?.trim() ?? '';
}
