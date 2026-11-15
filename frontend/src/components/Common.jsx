export function Status({ loading, error, empty, onRetry, children, height = 120 }) {
  if (loading) return <div className="state" style={{ minHeight: height }} role="status">Cargando…</div>;
  if (error) {
    return (
      <div className="state error" style={{ minHeight: height }} role="alert">
        <span>No se pudo cargar: {error}</span>
        {onRetry && <button onClick={onRetry}>Reintentar</button>}
      </div>
    );
  }
  if (empty) return <div className="state empty" style={{ minHeight: height }}>No hay datos para los filtros seleccionados.</div>;
  return children;
}

export function Card({ title, subtitle, actions, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      <header className="card-head">
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
        {actions}
      </header>
      {children}
    </section>
  );
}
