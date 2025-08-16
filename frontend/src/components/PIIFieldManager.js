import React, { useState, useEffect } from 'react';
import axios from 'axios';

const PIIFieldManager = ({ guardType, onClose }) => {
  const [fields, setFields] = useState([]);
  const [regexPatterns, setRegexPatterns] = useState([]);
  const [nerEntityTypes, setNerEntityTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingField, setEditingField] = useState(null);
  const [formData, setFormData] = useState({
    field_name: '',
    display_name: '',
    detection_type: 'regex',
    example_value: '',
    regex_pattern: '',
  ner_entity_type: ''
  });

  const API_BASE = 'http://127.0.0.1:8000/api/config';

  // Charger les données initiales
  useEffect(() => {
    loadFields();
    loadRegexPatterns();
    loadNerEntityTypes();
  }, [guardType]);

  const loadFields = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/pii-fields/${guardType}`);
      setFields(response.data.fields || []);
      setError(null);
    } catch (err) {
      setError('Erreur lors du chargement des champs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadRegexPatterns = async () => {
    try {
      const response = await axios.get(`${API_BASE}/regex-patterns`);
  const list = response.data.data || response.data.patterns || [];
  setRegexPatterns(list);
    } catch (err) {
      console.error('Erreur chargement patterns:', err);
    }
  };

  const loadNerEntityTypes = async () => {
    try {
      const response = await axios.get(`${API_BASE}/ner-entity-types`);
      setNerEntityTypes(response.data.entity_types || []);
    } catch (err) {
      console.error('Erreur chargement entités NER:', err);
    }
  };

  const resetForm = () => {
    setFormData({
      field_name: '',
      display_name: '',
      detection_type: 'regex',
      example_value: '',
      regex_pattern: '',
  ner_entity_type: ''
    });
    setEditingField(null);
    setShowForm(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    // Mapper les champs frontend vers backend
    const payload = {
      field_name: formData.field_name,
      display_name: formData.display_name,
      type: formData.detection_type,  // detection_type -> type
      example: formData.example_value,  // example_value -> example
  pattern: formData.regex_pattern,
  ner_entity_type: formData.ner_entity_type
    };

    try {
      if (editingField) {
        await axios.put(`${API_BASE}/pii-fields/${editingField.id}`, formData);
      } else {
        // Utiliser la nouvelle route backend
        await axios.post(`${API_BASE}/guard-types/${guardType}/fields`, payload);
      }
      
      await loadFields();
      resetForm();
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la sauvegarde');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (field) => {
    setFormData({
      field_name: field.field_name,
      display_name: field.display_name,
      detection_type: field.detection_type,
      example_value: field.example_value || '',
      regex_pattern: field.regex_pattern || '',
  ner_entity_type: field.ner_entity_type || ''
    });
    setEditingField(field);
    setShowForm(true);
  };

  const handleDelete = async (id, fieldName) => {
    if (!window.confirm(`Êtes-vous sûr de vouloir supprimer le champ "${fieldName}" ?`)) {
      return;
    }

    setLoading(true);
    try {
      await axios.delete(`${API_BASE}/pii-fields/${id}`);
      await loadFields();
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la suppression');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const getDetectionTypeIcon = (type) => {
    switch (type) {
      case 'regex': return '🔤';
      case 'ner': return '🧠';
      case 'hybrid': return '🔬';
      default: return '❓';
    }
  };

  // Confiance & priorité retirées de l'UI (valeurs par défaut gérées côté backend)

  const getFormatExample = () => {
    const example = {
      [formData.field_name || 'field_name']: {
        type: formData.detection_type,
        exemple: formData.example_value || 'exemple...'
      }
    };

    if (formData.detection_type === 'regex' && formData.regex_pattern) {
      example[formData.field_name || 'field_name'].pattern = formData.regex_pattern;
    } else if (formData.detection_type === 'ner' && formData.ner_entity_type) {
      example[formData.field_name || 'field_name'].entity_type = formData.ner_entity_type;
    }

    return JSON.stringify(example, null, 2);
  };

  return (
    <div className="pii-field-manager">
      <div className="manager-header">
        <div>
          <h3>🔧 Champs PII - {guardType}</h3>
          <small>Gestion des champs de détection pour ce type de protection</small>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            className="btn btn-primary"
            onClick={() => setShowForm(!showForm)}
            disabled={loading}
          >
            {showForm ? 'Annuler' : '+ Nouveau Champ'}
          </button>
          <button className="btn btn-secondary" onClick={onClose}>
            ← Retour
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>❌ {error}</span>
        </div>
      )}

      {showForm && (
        <div className="form-container">
          <h4>{editingField ? 'Modifier le Champ' : 'Créer un Nouveau Champ'}</h4>
          
          <form onSubmit={handleSubmit} className="field-form">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="field_name">Nom du Champ *</label>
                <input
                  type="text"
                  id="field_name"
                  name="field_name"
                  value={formData.field_name}
                  onChange={handleInputChange}
                  placeholder="ex: phone, email, address"
                  required
                  disabled={editingField !== null}
                />
                <small>Identifiant unique (non modifiable après création)</small>
              </div>

              <div className="form-group">
                <label htmlFor="display_name">Nom d'Affichage *</label>
                <input
                  type="text"
                  id="display_name"
                  name="display_name"
                  value={formData.display_name}
                  onChange={handleInputChange}
                  placeholder="ex: Numéro de Téléphone"
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="detection_type">Type de Détection *</label>
                <select
                  id="detection_type"
                  name="detection_type"
                  value={formData.detection_type}
                  onChange={handleInputChange}
                  required
                >
                  <option value="regex">🔤 Regex - Expression régulière</option>
                  <option value="ner">🧠 NER - Reconnaissance d'entités</option>
                  <option value="hybrid">🔬 Hybride - Regex + NER</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="example_value">Exemple de Valeur *</label>
                <input
                  type="text"
                  id="example_value"
                  name="example_value"
                  value={formData.example_value}
                  onChange={handleInputChange}
                  placeholder="ex: +33 6 45 67 89 12"
                  required
                />
              </div>
            </div>

            {(formData.detection_type === 'regex' || formData.detection_type === 'hybrid') && (
              <div className="form-group">
                <label htmlFor="regex_pattern">Pattern Regex</label>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <select
                    value={formData.regex_pattern}
                    onChange={(e) => setFormData(prev => ({ ...prev, regex_pattern: e.target.value }))}
                    style={{ flex: 1 }}
                  >
                    <option value="">-- Sélectionner un pattern existant --</option>
                    {regexPatterns.map(pattern => (
                      <option key={pattern.name} value={pattern.name}>
                        {pattern.display_name} ({pattern.name})
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    id="regex_pattern"
                    name="regex_pattern"
                    value={formData.regex_pattern}
                    onChange={handleInputChange}
                    placeholder="ou saisir un pattern personnalisé"
                    style={{ flex: 1 }}
                  />
                </div>
                <small>Sélectionnez un pattern prédéfini ou saisissez un pattern personnalisé</small>
              </div>
            )}

            {(formData.detection_type === 'ner' || formData.detection_type === 'hybrid') && (
              <div className="form-group">
                <label htmlFor="ner_entity_type">Type d'Entité NER</label>
                <select
                  id="ner_entity_type"
                  name="ner_entity_type"
                  value={formData.ner_entity_type}
                  onChange={handleInputChange}
                >
                  <option value="">-- Sélectionner un type d'entité --</option>
                  {nerEntityTypes.map(entity => (
                    <option key={`${entity.model_name}-${entity.entity_type}`} value={entity.entity_type}>
                      {entity.display_name} ({entity.model_name}: {entity.entity_type})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Champ confiance & priorité supprimés de l'interface */}

            <div className="form-preview">
              <h5>📄 Aperçu du Format JSON</h5>
              <pre style={{ 
                background: '#f8f9fa', 
                padding: '15px', 
                borderRadius: '6px',
                fontSize: '12px',
                overflow: 'auto',
                border: '1px solid #e9ecef'
              }}>
                {getFormatExample()}
              </pre>
            </div>

            <div className="form-actions">
              <button type="button" onClick={resetForm} className="btn btn-secondary">
                Annuler
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Sauvegarde...' : (editingField ? 'Modifier' : 'Créer')}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="fields-list">
        <h4>Champs Configurés ({fields.length})</h4>

        {loading && fields.length === 0 ? (
          <div className="loading">
            <div className="spinner"></div>
            <span>Chargement...</span>
          </div>
        ) : (
          <div className="fields-grid">
            {fields.map(field => (
                <div key={field.id} className="field-card">
                  <div className="field-header">
                    <div className="field-info">
                      <span className="field-icon">
                        {getDetectionTypeIcon(field.detection_type)}
                      </span>
                      <div>
                        <h5>{field.display_name}</h5>
                        <small>ID: {field.field_name}</small>
                      </div>
                    </div>
                  </div>

                  <div className="field-details">
                    <div className="field-row">
                      <strong>Type:</strong> 
                      <span className={`type-badge ${field.detection_type}`}>
                        {field.detection_type.toUpperCase()}
                      </span>
                    </div>
                    
                    <div className="field-row">
                      <strong>Exemple:</strong> 
                      <code>{field.example_value}</code>
                    </div>

                    {field.regex_pattern && (
                      <div className="field-row">
                        <strong>Pattern:</strong> 
                        <code>{field.regex_pattern}</code>
                      </div>
                    )}

                    {field.ner_entity_type && (
                      <div className="field-row">
                        <strong>Entité:</strong> 
                        <span className="entity-badge">{field.ner_entity_type}</span>
                      </div>
                    )}

                    {/* Confiance supprimée */}
                  </div>

                  <div className="field-actions">
                    <button
                      className="btn btn-icon btn-secondary"
                      title="Modifier"
                      onClick={() => handleEdit(field)}
                      disabled={loading}
                    >
                      ✏️
                    </button>
                    <button
                      className="btn btn-icon btn-danger"
                      title="Supprimer"
                      onClick={() => handleDelete(field.id, field.display_name)}
                      disabled={loading}
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
          </div>
        )}

        {fields.length === 0 && !loading && (
          <div className="empty-state">
            <p>Aucun champ configuré pour ce type de protection.</p>
            <button 
              className="btn btn-primary"
              onClick={() => setShowForm(true)}
            >
              Créer le premier champ
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default PIIFieldManager;
