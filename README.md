# Plataforma Integral de Ingeniería de Datos y Analítica Inteligente

**Estado**: 🚀 En desarrollo (Fase 1: Descubrimiento)

## 📋 Descripción del Proyecto

Plataforma end-to-end que transforma datos operacionales de **WideWorldImporters** en análisis descriptivo, predicciones inteligentes y explicaciones generativas. Integra:

- **ETL/ELT**: Extracción, transformación y carga de datos
- **Data Warehouse**: Modelo dimensional (Star Schema)
- **Business Intelligence**: Dashboard web interactivo
- **Machine Learning**: Modelo predictivo de ventas
- **Generative AI**: Asistente analítico inteligente
- **Automatización**: Alertas y notificaciones

---

## 🎯 Objetivos

1. ✅ Analizar base relacional e identificar entidades y oportunidades
2. ✅ Diseñar ETL con staging raw + clean
3. ✅ Construir Data Warehouse dimensional (SQL Server)
4. ✅ Crear dashboard web consultando el DW
5. ✅ Entrenar modelo ML con evaluación correcta
6. ✅ Integrar IA generativa para consultas analíticas
7. ✅ Implementar alertas automatizadas
8. ✅ Documentar, probar y demostrar la solución

---

## 🏗️ Arquitectura (Capas)

```
┌─────────────────────────────────────────────────────┐
│          Capa de Presentación (Frontend React)      │
│          Dashboard con KPIs, Filtros, Alertas        │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│           Capa de API (Backend FastAPI)              │
│      Rutas, Autenticación, Lógica de Negocios       │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼────┐  ┌─────▼─────┐  ┌────▼──────┐
│Data    │  │Machine    │  │Generative │
│WH      │  │Learning   │  │AI         │
│(SQL)   │  │(Python)   │  │(Ollama)   │
└────────┘  └───────────┘  └───────────┘
```

---

## 🗂️ Estructura del Repositorio

```
Examen-Tecnologia-emergentes/
├── documentation/          # Documentación técnica
│   ├── ARQUITECTURA.md
│   ├── MODELO_DIMENSIONAL.md
│   ├── GUIA_INSTALACION.md
│   ├── ERD.md
│   └── DICCIONARIO_DATOS.md
├── database/              # Scripts SQL
│   ├── init/              # Creación de bases
│   ├── staging/           # Tablas raw + clean
│   └── warehouse/         # Modelo dimensional
├── etl/                   # Pipeline de datos (Python)
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   ├── audit.py
│   └── requirements.txt
├── backend/               # API FastAPI
│   ├── main.py
│   ├── app/
│   │   ├── routes.py
│   │   ├── schemas.py
│   │   └── database.py
│   └── requirements.txt
├── frontend/              # React
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   ├── components/
│   │   └── services/
│   ├── package.json
│   └── .env.example
├── machine-learning/      # Modelo predictivo
│   ├── train_model.py
│   ├── model.pkl
│   └── requirements.txt
├── generative-ai/         # Asistente IA
│   ├── ai_assistant.py
│   └── requirements.txt
├── tests/                 # Pruebas unitarias
├── deployment/            # Docker & Compose
│   └── docker-compose.yml
├── .env.example           # Variables de entorno
├── README.md              # Este archivo
└── .gitignore
```

---

## 🚀 Inicio Rápido (Docker Compose)

### Prerequisitos
- Docker Desktop instalado
- Git configurado

### Pasos

1. **Clonar repositorio**
```bash
git clone https://github.com/JamilHerrera/Examen-Tecnologia-emergentes.git
cd Examen-Tecnologia-emergentes
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
# Edita .env con tus valores
```

3. **Iniciar servicios con Docker Compose**
```bash
docker-compose -f deployment/docker-compose.yml up -d
```

4. **Esperar a que SQL Server esté listo (~30 segundos)**
```bash
docker-compose -f deployment/docker-compose.yml logs mssql
```

5. **Ejecutar scripts de inicialización**
```bash
# Desde dentro del contenedor o con sqlcmd
docker-compose -f deployment/docker-compose.yml exec mssql sqlcmd -S localhost -U sa -P YourSecurePassword123! -i /init/01_create_databases.sql
```

6. **Ejecutar ETL**
```bash
cd etl
python -m pip install -r requirements.txt
python main.py --phase extract
python main.py --phase transform
python main.py --phase load
```

7. **Iniciar Backend**
```bash
cd backend
python -m pip install -r requirements.txt
python main.py
# Backend disponible en http://localhost:8000
```

8. **Iniciar Frontend**
```bash
cd frontend
npm install
npm start
# Frontend disponible en http://localhost:3000
```

---

## 📊 Fases del Proyecto (3 días)

| Fase | Duración | Actividades |
|------|----------|------------|
| **1. Descubrimiento** | 3-4h | Dataset, ERD, Diccionario, Preguntas analíticas |
| **2. Diseño** | 2-3h | Arquitectura, Modelo Dimensional, Stack |
| **3. ETL & Calidad** | 12-15h | Extracción, Staging, Limpieza, Auditoría |
| **4. Data Warehouse** | 8-10h | FactSales + Dimensiones, Carga, Reconciliación |
| **5. BI Dashboard** | 10-12h | API + Frontend, KPIs, Filtros |
| **6. ML** | 6-8h | Modelo Predictivo, Baseline, Evaluación |
| **7. GenAI + Alertas** | 5h | Asistente IA, Alertas Automáticas |
| **8. Cierre** | 3-4h | Documentación, README, Pruebas, Video |

---

## 🛢️ Dataset

**WideWorldImporters** (SQL Server) - Base comercial con:
- Clientes, proveedores, productos
- Órdenes de venta y compra
- Inventario, movimientos
- Personas, ciudades, entidades

→ Ideal para análisis de ventas, predicciones y segmentación.

---

## 🔐 Seguridad & Buenas Prácticas

✅ `.env.example` sin credenciales  
✅ Contraseñas en variables de entorno  
✅ Consultas parametrizadas (sin SQL injection)  
✅ Mínimo privilegio en cuentas de BD  
✅ Backend consume DW, no frontend directo  
✅ GenAI consulta datos autorizados  
✅ Repositorio libre de secretos  

---

## 🧪 Pruebas

```bash
# Ejecutar suite de pruebas
pytest tests/ -v

# Pruebas específicas
pytest tests/test_etl.py -v
pytest tests/test_api.py -v
pytest tests/test_ml.py -v
```

---

## 📖 Documentación

Consulta la carpeta `documentation/` para:
- `ARQUITECTURA.md` - Diagrama e integración de capas
- `MODELO_DIMENSIONAL.md` - Grano, hechos, dimensiones, SCD
- `GUIA_INSTALACION.md` - Pasos detallados de despliegue
- `ERD.md` - Entity Relationship Diagram (origen)
- `DICCIONARIO_DATOS.md` - Definición de campos y tablas

---

## 🤝 Contribuciones

Este es un proyecto académico. Para cambios:
1. Crea una rama: `git checkout -b feature/tu-feature`
2. Realiza commits descriptivos
3. Push y crea Pull Request

---

## 📝 Notas de Desarrollo

- **Staging**: Conserva raw (original) y clean (procesado)
- **Idempotencia**: Reejecutar ETL no duplica datos
- **Reconciliación**: Valida conteos origen → staging → DW
- **Data Leakage**: ML solo usa train/val, nunca test
- **Logs**: Todo proceso registra ejecución y errores

---

## 🎬 Demo Final

Video de 5 minutos demostrando:
- Caso de uso y arquitectura
- ETL extrayendo y transformando
- Modelo dimensional y consultas
- Dashboard interactivo con KPIs
- Modelo ML con predicción
- Asistente GenAI respondiendo preguntas
- Alerta automatizada disparándose

---

## 📧 Contacto

**Desarrollo**: Jamil Herrera  
**Correo**: [email del usuario]  
**Repositorio**: https://github.com/JamilHerrera/Examen-Tecnologia-emergentes

---

**Última actualización**: Noviembre 2026  
**Versión**: 1.0 (En desarrollo)
