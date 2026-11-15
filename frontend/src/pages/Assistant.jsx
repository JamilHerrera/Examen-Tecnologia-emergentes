import { useRef, useState } from 'react';
import { api, fmt } from '../api.js';
import { Card } from '../components/Common.jsx';

const EXAMPLES = [
  '¿Cuáles fueron las ventas del último trimestre?',
  '¿Qué categorías tuvieron mayor crecimiento?',
  'Resume los principales cambios respecto al período anterior',
  '¿Qué regiones presentan una disminución relevante?',
  'Explica el indicador ticket promedio',
  '¿Cuál es la predicción de ventas para las próximas semanas?',
  '¿Qué análisis adicional convendría realizar?',
];

function Message({ m }) {
  if (m.role === 'user') return <div className="msg user">{m.text}</div>;
  const r = m.result;
  return (
    <div className="msg bot">
      {m.error ? <div className="state error" role="alert">{m.error}</div> : (
        <>
          <div className="msg-badges">
            <span className="badge ok">Dato historico del DW</span>
            {r.prediction && <span className="badge pred">Incluye PREDICCION</span>}
            {r.period && !r.period.outOfRange && <span className="badge ok">Periodo {r.period.from} a {r.period.to}</span>}
          </div>
          <p className="answer">{r.answer}</p>
          {r.interpretation?.text && (
            <div className="interpretation">
              <span className="badge ai">Interpretacion generada por IA · {r.model}</span>
              <p className="answer">{r.interpretation.text}</p>
              <p className="muted">Puede contener imprecisiones: los datos consultados de arriba son la fuente de referencia.</p>
            </div>
          )}
          {r.interpretation && !r.interpretation.text && (
            <p className="muted">
              {r.interpretation.status === 'llm_unavailable'
                ? 'Interpretacion de IA no disponible (Ollama no responde); se muestran solo los datos consultados.'
                : 'La interpretacion generada se descarto porque no se pudo verificar contra los datos.'}
            </p>
          )}
          {r.sources.length > 0 && (
            <p className="muted">Fuentes: {r.sources.map((s) => `${s.dataset} (${s.period})`).join(' · ')}</p>
          )}
          <p className="muted">
            Datos hasta {r.dataAsOf?.lastOrderDate} · ultima carga {fmt.datetime(r.dataAsOf?.lastLoadedAt)} · {(r.latencyMs / 1000).toFixed(1)} s
          </p>
        </>
      )}
    </div>
  );
}

export default function Assistant() {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const bottom = useRef(null);

  async function send(question) {
    const q = (question ?? text).trim();
    if (!q || busy) return;
    setText('');
    setBusy(true);
    setMessages((prev) => [...prev, { role: 'user', text: q }]);
    try {
      const result = await api('/assistant/ask', { method: 'POST', body: { question: q } });
      setMessages((prev) => [...prev, { role: 'bot', result }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'bot', error: err.message }]);
    } finally {
      setBusy(false);
      setTimeout(() => bottom.current?.scrollIntoView({ behavior: 'smooth' }), 50);
    }
  }

  return (
    <Card title="Asistente analitico (IA generativa)"
          subtitle="Responde con datos del Data Warehouse mediante consultas aprobadas. El texto lo redacta un modelo local (Ollama); las cifras se verifican contra los hechos consultados.">
      <div className="examples">
        {EXAMPLES.map((e) => <button key={e} disabled={busy} onClick={() => send(e)}>{e}</button>)}
      </div>
      <div className="chat" aria-live="polite">
        {messages.length === 0 && <div className="state empty">Haz una pregunta o elige un ejemplo.</div>}
        {messages.map((m, i) => <Message key={i} m={m} />)}
        {busy && <div className="state" role="status">Consultando datos y redactando respuesta… (puede tardar hasta un minuto la primera vez)</div>}
        <div ref={bottom} />
      </div>
      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input value={text} maxLength={300} onChange={(e) => setText(e.target.value)} placeholder="Escribe tu pregunta (max. 300 caracteres)" aria-label="Pregunta" />
        <button className="primary" disabled={busy || !text.trim()}>Enviar</button>
      </form>
    </Card>
  );
}
