import React, { useState } from 'react';
import axios from 'axios';
import PIIProtectionForm from './components/PIIProtectionForm';
import ResultDisplay from './components/ResultDisplay';
import GuardTypeInfo from './components/GuardTypeInfo';
import LogsPage from './components/LogsPage';
import './App.css';

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (formData) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post('http://127.0.0.1:8000/process', {
        text: formData.text,
        guard_type: formData.guardType,
        llm_provider: formData.llmProvider
      });

      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors du traitement de la requête');
    } finally {
      setLoading(false);
    }
  };

  const [showLogs, setShowLogs] = useState(false);

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>🛡️ IA Guards</h1>
          <p>Protection des données personnelles pour l'Intelligence Artificielle</p>
        </header>
        <button onClick={() => setShowLogs((v) => !v)} style={{ marginBottom: '1rem', float: 'right' }}>
          {showLogs ? 'Masquer les logs' : 'Afficher les logs'}
        </button>
        {showLogs ? (
          <div className="card">
            {/* Affichage des logs */}
            <LogsPage />
          </div>
        ) : (
          <>
            <GuardTypeInfo />
            <div className="card">
              <PIIProtectionForm onSubmit={handleSubmit} loading={loading} />
            </div>
            {loading && (
              <div className="card">
                <div className="loading">
                  <div className="spinner"></div>
                  <span style={{ marginLeft: '10px' }}>Traitement en cours...</span>
                </div>
              </div>
            )}
            {error && (
              <div className="card">
                <div className="result-item error">
                  <h3>❌ Erreur</h3>
                  <pre>{error}</pre>
                </div>
              </div>
            )}
            {result && (
              <div className="card">
                <ResultDisplay result={result} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default App;
