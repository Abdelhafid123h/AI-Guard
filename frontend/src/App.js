import React, { useState } from 'react';
import axios from 'axios';
import PIIProtectionForm from './components/PIIProtectionForm';
import ResultDisplay from './components/ResultDisplay';
import GuardTypeInfo from './components/GuardTypeInfo';
import GuardTypeManager from './components/GuardTypeManager';
import HistoryPage from './components/HistoryPage';
import './App.css';

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('protection'); // 'protection', 'management', 'history'

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

  const renderTabContent = () => {
    switch (activeTab) {
      case 'protection':
        return (
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
        );
      
      case 'management':
        return (
          <div className="card">
            <GuardTypeManager />
          </div>
        );
      
      case 'history':
        return (
          <div className="card">
            <HistoryPage />
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>🛡️ IA Guards</h1>
          <p>Protection des données personnelles pour l'Intelligence Artificielle</p>
        </header>

        {/* Navigation par onglets */}
        <div className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === 'protection' ? 'active' : ''}`}
            onClick={() => setActiveTab('protection')}
          >
            🛡️ Protection PII
          </button>
          <button
            className={`nav-tab ${activeTab === 'management' ? 'active' : ''}`}
            onClick={() => setActiveTab('management')}
          >
            🔧 Gestion des Types
          </button>
          <button
            className={`nav-tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            📊 Historique
          </button>
        </div>

        {/* Contenu selon l'onglet actif */}
        {renderTabContent()}
      </div>
    </div>
  );
}

export default App;
