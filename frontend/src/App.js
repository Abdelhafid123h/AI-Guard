import React, { useState } from 'react';
import axios from 'axios';
import PIIProtectionForm from './components/PIIProtectionForm';
import ResultDisplay from './components/ResultDisplay';
import GuardTypeInfo from './components/GuardTypeInfo';
import GuardTypeManager from './components/GuardTypeManager';
import HistoryPage from './components/HistoryPage';
import MaskedReview from './components/MaskedReview';
import './App.css';

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('protection'); // 'protection', 'management', 'history'
  const [review, setReview] = useState(null); // { original, masked, tokens, guardType }

  const handleSubmit = async (formData) => {
    // Étape 1: obtenir le texte masqué sans appeler le LLM
    setLoading(true);
    setError(null);
    setResult(null);
    setReview(null);
    try {
      const resp = await axios.post('http://127.0.0.1:8000/mask-only', {
        text: formData.text,
        guard_type: formData.guardType
      });
      setReview({
        original: resp.data.original,
        masked: resp.data.masked,
        tokens: resp.data.tokens,
        guardType: formData.guardType
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors du masquage');
    } finally {
      setLoading(false);
    }
  };

  const handleFinalize = async (masked, tokens, guardType) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
  const resp = await axios.post('http://127.0.0.1:8000/finalize', {
        masked,
        tokens,
        guard_type: guardType
      });
  // Preserve original text if backend doesn't echo it in finalize
  setResult({ original: review?.original || '', ...resp.data });
      setReview(null);
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur lors de l'envoi au LLM");
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
              {!review ? (
                <PIIProtectionForm onSubmit={handleSubmit} loading={loading} />
              ) : (
                <MaskedReview
                  original={review.original}
                  masked={review.masked}
                  tokens={review.tokens}
                  guardType={review.guardType}
                  loading={loading}
                  onFinalize={handleFinalize}
                  onCancel={() => setReview(null)}
                />
              )}
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
