const FIELDS = [
  ['category', 'Categoria de producto', 'categories'],
  ['region', 'Region', 'regions'],
  ['customerCategory', 'Categoria de cliente', 'customerCategories'],
];

export default function Filters({ meta, filters, onChange, onReset }) {
  const { freshness, dimensions } = meta;
  const set = (patch) => onChange({ ...filters, ...patch });
  return (
    <div className="filters">
      <label>Desde
        <input type="date" value={filters.from} min={freshness.firstOrderDate} max={filters.to}
               onChange={(e) => set({ from: e.target.value })} />
      </label>
      <label>Hasta
        <input type="date" value={filters.to} min={filters.from} max={freshness.lastOrderDate}
               onChange={(e) => set({ to: e.target.value })} />
      </label>
      {FIELDS.map(([key, label, list]) => (
        <label key={key}>{label}
          <select value={filters[key] ?? ''} onChange={(e) => set({ [key]: e.target.value })}>
            <option value="">Todas</option>
            {dimensions[list].map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>
      ))}
      {filters.product && (
        <span className="chip">Producto: {filters.product}
          <button aria-label="Quitar producto" onClick={() => set({ product: '' })}>×</button>
        </span>
      )}
      <button onClick={onReset}>Restablecer</button>
    </div>
  );
}
