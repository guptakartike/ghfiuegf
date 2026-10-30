import { useEffect, useState } from "react";
import { apiRequest } from "./lib/api";
import type { HealthResponse } from "./lib/types";

function App() {
  const [status, setStatus] = useState("Connecting...");
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<HealthResponse>("/health")
      .then((data) => setStatus(data.status))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <main className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold">Wind Analytics</h1>
        <p className="mt-4">Backend Status: {status}</p>
        {error && <p className="text-red-600">{error}</p>}
      </div>
    </main>
  );
}

export default App;