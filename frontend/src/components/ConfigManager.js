import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './ConfigManager.css';

const ConfigManager = () => {
  const [activeTab, setActiveTab] = useState('guard-types');
  const [guardTypes, setGuardTypes] = useState([]);
  const [regexPatterns, setRegexPatterns] = useState([]);
  const [nerEntityTypes, setNerEntityTypes] = useState([]);
  const [selectedGuardType, setSelectedGuardType] = useState(null);
  const [guardFields, setGuardFields] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Formulaires
  const [showCreateGuardForm, setShowCreateGuardForm] = useState(false);
  const [showCreateFieldForm, setShowCreateFieldForm] = useState(false);
  const [showCreatePatternForm, setShowCreatePatternForm] = useState(false);

  const API_BASE = 'http://127.0.0.1:8000/api/config';

  useEffect(() => {
    loadGuardTypes();
    loadRegexPatterns();
    loadNerEntityTypes();
  }, []);

  const showMessage = (message, type = 'success') => {
    if (type === 'success') {
      setSuccess(message);
      setError(null);
    } else {
      setError(message);
      setSuccess(null);
    }
    setTimeout(() => {
      setSuccess(null);
      setError(null);
    }, 5000);
  };

  // =================== CHARGEMENT DES DONNÉES ===================

  const loadGuardTypes = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/guard-types`);
      setGuardTypes(response.data.data);
    } catch (err) {
      showMessage(`Erreur chargement types: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadRegexPatterns = async () => {
    try {
      const response = await axios.get(`${API_BASE}/regex-patterns`);
      setRegexPatterns(response.data.data);
    } catch (err) {
      console.error('Erreur chargement patterns:', err);
    }
  };

  const loadNerEntityTypes = async () => {
    try {
      const response = await axios.get(`${API_BASE}/ner-entity-types`);
      setNerEntityTypes(response.data.data);
    } catch (err) {
      console.error('Erreur chargement types NER:', err);
    }
  };

  const loadGuardFields = async (guardName) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/guard-types/${guardName}/fields`);
      setGuardFields(response.data.data);
      setSelectedGuardType(guardName);
    } catch (err) {
      showMessage(`Erreur chargement champs: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // =================== COMPOSANT FORMULAIRE TYPE DE PROTECTION ===================

  const CreateGuardTypeForm = () => {
    const [formData, setFormData] = useState({
      name: '',
      display_name: '',
      description: '',
      icon: '🛡️',
      color: '#666666'
    });

    const handleSubmit = async (e) => {
      e.preventDefault();
      try {
        setLoading(true);
        const response = await axios.post(`${API_BASE}/guard-types`, formData);
        showMessage(response.data.message);
        setShowCreateGuardForm(false);
        setFormData({ name: '', display_name: '', description: '', icon: '🛡️', color: '#666666' });
        loadGuardTypes();
      } catch (err) {
        showMessage(err.response?.data?.detail || 'Erreur création type', 'error');
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="form-overlay">
        <div className="form-container">
          <h3>🆕 Créer un Type de Protection</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Nom technique *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="ex: TypeC"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Nom d'affichage *</label>
              <input
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                placeholder="ex: 📋 Données Médicales"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Description du type de protection"
                rows="3"
              />
            </div>
            
            <div className="form-row">
              <div className="form-group">
                <label>Icône</label>
                <input
                  type="text"
                  value={formData.icon}
                  onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                  placeholder="🛡️"
                />
              </div>
              
              <div className="form-group">
                <label>Couleur</label>
                <input
                  type="color"
                  value={formData.color}
                  onChange={(e) => setFormData({ ...formData, color: e.target.value })}
                />
              </div>
            </div>
            
            <div className="form-actions">
              <button type="button" onClick={() => setShowCreateGuardForm(false)} className="btn-secondary">
                Annuler
              </button>
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Création...' : 'Créer'}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  // =================== COMPOSANT FORMULAIRE CHAMP PII ===================

  const CreateFieldForm = () => {
    const [formData, setFormData] = useState({
      field_name: '',
      display_name: '',
      type: 'regex',
      example: '',
      pattern: '',
      ner_entity_type: '',
      confidence_threshold: 0.7,
      priority: 1
    });

    const handleSubmit = async (e) => {
      e.preventDefault();
      try {
        setLoading(true);
        const response = await axios.post(`${API_BASE}/guard-types/${selectedGuardType}/fields`, formData);
        showMessage(response.data.message);
        setShowCreateFieldForm(false);
        setFormData({
          field_name: '',
          display_name: '',
          type: 'regex',
          example: '',
          pattern: '',
          ner_entity_type: '',
          confidence_threshold: 0.7,
          priority: 1
        });
        loadGuardFields(selectedGuardType);
      } catch (err) {
        showMessage(err.response?.data?.detail || 'Erreur création champ', 'error');
      } finally {
        setLoading(false);
      }
    };

    return (
      <div className="form-overlay">
        <div className="form-container">
          <h3>🆕 Créer un Champ PII pour {selectedGuardType}</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Nom technique du champ *</label>
              <input
                type="text"
                value={formData.field_name}
                onChange={(e) => setFormData({ ...formData, field_name: e.target.value })}
                placeholder="ex: medical_id"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Nom d'affichage *</label>
              <input
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                placeholder="ex: Numéro Médical"
                required
              />
            </div>
            
            <div className="form-group">
              <label>Type de détection *</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                required
              >
                <option value="regex">Regex uniquement</option>
                <option value="ner">NER uniquement</option>
                <option value="hybrid">Hybrid (Regex + NER)</option>
              </select>
            </div>
            
            <div className="form-group">
              <label>Exemple de valeur *</label>
              <input
                type="text"
                value={formData.example}
                onChange={(e) => setFormData({ ...formData, example: e.target.value })}
                placeholder="ex: MED123456789"
                required
              />
            </div>
            
            {(formData.type === 'regex' || formData.type === 'hybrid') && (
              <div className="form-group">
                <label>Pattern Regex *</label>
                <select
                  value={formData.pattern}
                  onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
                  required={formData.type === 'regex' || formData.type === 'hybrid'}
                >
                  <option value="">Sélectionner un pattern existant</option>
                  {regexPatterns.map(pattern => (
                    <option key={pattern.id} value={pattern.name}>
                      {pattern.display_name} ({pattern.name})
                    </option>
                  ))}
                </select>
                <small>Ou tapez un pattern personnalisé directement</small>
                <input
                  type="text"
                  value={formData.pattern}
                  onChange={(e) => setFormData({ ...formData, pattern: e.target.value })}
                  placeholder="\\d{3}[A-Z]{3}\\d{6}"
                />
              </div>
            )}
            
            {(formData.type === 'ner' || formData.type === 'hybrid') && (
              <div className="form-group">
                <label>Type d'entité NER *</label>
                <select
                  value={formData.ner_entity_type}
                  onChange={(e) => setFormData({ ...formData, ner_entity_type: e.target.value })}
                  required={formData.type === 'ner' || formData.type === 'hybrid'}
                >
                  <option value="">Sélectionner un type NER</option>
                  {nerEntityTypes.map(entity => (
                    <option key={`${entity.model_name}-${entity.entity_type}`} value={entity.entity_type}>
                      {entity.display_name} ({entity.model_name} - {entity.entity_type})
                    </option>
                  ))}
                </select>
              </div>
            )}
            
            <div className="form-row">
              <div className="form-group">
                <label>Seuil de confiance</label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.confidence_threshold}
                  onChange={(e) => setFormData({ ...formData, confidence_threshold: parseFloat(e.target.value) })}
                />
              </div>
              
              <div className="form-group">
                <label>Priorité</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                />
              </div>
            </div>
            
            <div className="form-actions">
              <button type="button" onClick={() => setShowCreateFieldForm(false)} className="btn-secondary">
                Annuler
              </button>
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Création...' : 'Créer'}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  // =================== COMPOSANT PRINCIPAL ===================

  return (
    <div className="config-manager">
      <div className="config-header">
        <h1>⚙️ Gestionnaire de Configuration AI-Guards</h1>
        <p>Configuration dynamique des types de protection et champs PII</p>
      </div>

      {/* Messages */}
      {success && <div className="alert alert-success">{success}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Onglets */}
      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'guard-types' ? 'active' : ''}`}
          onClick={() => setActiveTab('guard-types')}
        >
          🛡️ Types de Protection
        </button>
        <button 
          className={`tab ${activeTab === 'patterns' ? 'active' : ''}`}
          onClick={() => setActiveTab('patterns')}
        >
          🔧 Patterns Regex
        </button>
      </div>

      {/* Contenu des onglets */}
      <div className="tab-content">
        {activeTab === 'guard-types' && (
          <div className="guard-types-section">
            <div className="section-header">
              <h2>Types de Protection</h2>
              <button 
                className="btn-primary" 
                onClick={() => setShowCreateGuardForm(true)}
              >
                ➕ Nouveau Type
              </button>
            </div>

            <div className="guard-types-grid">
              {guardTypes.map(guardType => (
                <div key={guardType.id} className="guard-type-card">
                  <div className="card-header">
                    <span className="icon" style={{ color: guardType.color }}>
                      {guardType.icon}
                    </span>
                    <h3>{guardType.display_name}</h3>
                  </div>
                  <p className="description">{guardType.description}</p>
                  <div className="card-actions">
                    <button 
                      className="btn-secondary"
                      onClick={() => loadGuardFields(guardType.name)}
                    >
                      📋 Voir Champs
                    </button>
                    <button className="btn-danger">🗑️</button>
                  </div>
                </div>
              ))}
            </div>

            {/* Section des champs du type sélectionné */}
            {selectedGuardType && (
              <div className="fields-section">
                <div className="section-header">
                  <h3>Champs PII pour {selectedGuardType}</h3>
                  <button 
                    className="btn-primary"
                    onClick={() => setShowCreateFieldForm(true)}
                  >
                    ➕ Nouveau Champ
                  </button>
                </div>

                <div className="fields-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Nom</th>
                        <th>Type</th>
                        <th>Exemple</th>
                        <th>Pattern/NER</th>
                        <th>Priorité</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {guardFields.map(field => (
                        <tr key={field.id}>
                          <td>
                            <strong>{field.display_name}</strong>
                            <br />
                            <small>{field.field_name}</small>
                          </td>
                          <td>
                            <span className={`badge badge-${field.detection_type}`}>
                              {field.detection_type}
                            </span>
                          </td>
                          <td>
                            <code>{field.example_value}</code>
                          </td>
                          <td>
                            {field.pattern && <div><strong>Pattern:</strong> {field.regex_pattern}</div>}
                            {field.ner_entity_type && <div><strong>NER:</strong> {field.ner_entity_type}</div>}
                          </td>
                          <td>{field.priority}</td>
                          <td>
                            <button className="btn-small btn-secondary">✏️</button>
                            <button className="btn-small btn-danger">🗑️</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'patterns' && (
          <div className="patterns-section">
            <div className="section-header">
              <h2>Patterns Regex</h2>
              <button 
                className="btn-primary"
                onClick={() => setShowCreatePatternForm(true)}
              >
                ➕ Nouveau Pattern
              </button>
            </div>

            <div className="patterns-table">
              <table>
                <thead>
                  <tr>
                    <th>Nom</th>
                    <th>Pattern</th>
                    <th>Description</th>
                    <th>Exemples</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {regexPatterns.map(pattern => (
                    <tr key={pattern.id}>
                      <td>
                        <strong>{pattern.display_name}</strong>
                        <br />
                        <small>{pattern.name}</small>
                      </td>
                      <td>
                        <code>{pattern.pattern}</code>
                      </td>
                      <td>{pattern.description}</td>
                      <td>
                        {pattern.test_examples.slice(0, 2).map((example, idx) => (
                          <div key={idx}><code>{example}</code></div>
                        ))}
                      </td>
                      <td>
                        <button className="btn-small btn-secondary">✏️</button>
                        <button className="btn-small btn-danger">🗑️</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Formulaires modaux */}
      {showCreateGuardForm && <CreateGuardTypeForm />}
      {showCreateFieldForm && <CreateFieldForm />}
    </div>
  );
};

export default ConfigManager;
