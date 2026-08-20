# Monitoring System Frontend

Angular frontend for the monitoring dashboard, monitor management, incidents, users, authentication profiles, real-time updates, and public status pages.

## Development

Install dependencies and start the development server:

```bash
npm install
npm start
```

The application is available at `http://localhost:4200` and proxies `/api` requests to the backend at `http://127.0.0.1:8000`.

## Verification

```bash
npm test -- --watch=false
npm run build
```
