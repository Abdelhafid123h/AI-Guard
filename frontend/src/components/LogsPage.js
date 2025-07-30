import React, { useEffect, useState } from "react";

const LogsPage = () => {
  const [logs, setLogs] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchLogs = () => {
    setLoading(true);
    fetch("http://127.0.0.1:8000/logs")
      .then((res) => res.text())
      .then((data) => {
        setLogs(data);
        setLoading(false);
      })
      .catch(() => {
        setLogs("Erreur lors du chargement des logs.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Logs du système</h2>
      <button onClick={fetchLogs} style={{ marginBottom: "1rem" }}>
        Rafraîchir
      </button>
      {loading ? (
        <p>Chargement...</p>
      ) : (
        <pre style={{ background: "#222", color: "#eee", padding: "1rem", borderRadius: "8px", maxHeight: "70vh", overflow: "auto" }}>
          {logs}
        </pre>
      )}
    </div>
  );
};

export default LogsPage;
