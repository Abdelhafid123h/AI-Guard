import React, { useState, useEffect } from 'react';
import axios from 'axios';
import PIIFieldManager from './PIIFieldManager';

const GuardTypeManager = () => {
  const [guardTypes, setGuardTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editingType, setEditingType] = useState(null);
  const [selectedType, setSelectedType] = useState(null); // Pour la gestion des champs
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    icon: '',
    color: '#3498db'
  });

  const API_BASE = 'http://127.0.0.1:8000/api/config';

  // Charger tous les types de protection
  const loadGuardTypes = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/guard-types`);
      setGuardTypes(response.data.guard_types || []);
      setError(null);
    } catch (err) {
      setError('Erreur lors du chargement des types de protection');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGuardTypes();
  }, []);

  // Réinitialiser le formulaire
  const resetForm = () => {
    setFormData({
      name: '',
      display_name: '',
      description: '',
      icon: '',
      color: '#3498db'
    });
    setEditingType(null);
    setShowForm(false);
  };

  // Soumettre le formulaire (création ou modification)
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (editingType) {
        // Modification (utiliser le name comme identifiant dans l'URL)
        const updatePayload = {
          display_name: formData.display_name,
          description: formData.description,
          icon: formData.icon,
          color: formData.color
        };
        await axios.put(`${API_BASE}/guard-types/${editingType.name}`, updatePayload);
      } else {
        // Création
        await axios.post(`${API_BASE}/guard-types`, formData);
      }
      
      await loadGuardTypes();
      resetForm();
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la sauvegarde');
    } finally {
      setLoading(false);
    }
  };

  // Modifier un type
  const handleEdit = (guardType) => {
    setFormData({
      name: guardType.name,
      display_name: guardType.display_name,
      description: guardType.description || '',
      icon: guardType.icon || '',
      color: guardType.color || '#3498db'
    });
    setEditingType(guardType);
    setShowForm(true);
  };

  // Supprimer un type
  const handleDelete = async (id, name) => {
    if (!window.confirm(`Êtes-vous sûr de vouloir supprimer le type "${name}" ?`)) {
      return;
    }

    setLoading(true);
    try {
      await axios.delete(`${API_BASE}/guard-types/${id}`);
      await loadGuardTypes();
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la suppression');
    } finally {
      setLoading(false);
    }
  };

  // Gestion des changements dans le formulaire
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  // Icônes prédéfinies
  const iconOptions = [
    '🆔', '💳', '📍', '🏢', '📞', '💌', '🔐', '🏠', 
    '🚗', '✈️', '🏥', '📚', '💼', '🎓', '⚖️', '🛡️'
  ];

  // Si un type est sélectionné pour la gestion des champs
  if (selectedType) {
    return (
      <PIIFieldManager 
        guardType={selectedType} 
        onClose={() => setSelectedType(null)}
      />
    );
  }

  return (
    <div className="guard-type-manager">
      <div className="manager-header">
        <h2>🔧 Gestion des Types de Protection</h2>
        <button 
          className="btn btn-primary"
          onClick={() => setShowForm(!showForm)}
          disabled={loading}
        >
          {showForm ? 'Annuler' : '+ Nouveau Type'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>❌ {error}</span>
        </div>
      )}

      {showForm && (
        <div className="form-container">
          <h3>{editingType ? 'Modifier le Type' : 'Créer un Nouveau Type'}</h3>
          <form onSubmit={handleSubmit} className="guard-type-form">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="name">Nom du Type *</label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="ex: TypeC"
                  required
                  disabled={editingType !== null} // Ne pas modifier le nom existant
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
                  placeholder="ex: Données Professionnelles"
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="description">Description</label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                placeholder="Description du type de protection..."
                rows="3"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="icon">Icône</label>
                <div className="icon-selector">
                  <input
                    type="text"
                    id="icon"
                    name="icon"
                    value={formData.icon}
                    onChange={handleInputChange}
                    placeholder="Emoji ou icône"
                  />
                  <div className="icon-options">
                    {iconOptions.map(icon => (
                      <button
                        key={icon}
                        type="button"
                        className={`icon-option ${formData.icon === icon ? 'selected' : ''}`}
                        onClick={() => setFormData(prev => ({ ...prev, icon }))}
                      >
                        {icon}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="color">Couleur</label>
                <div className="color-input">
                  <input
                    type="color"
                    id="color"
                    name="color"
                    value={formData.color}
                    onChange={handleInputChange}
                  />
                  <input
                    type="text"
                    value={formData.color}
                    onChange={handleInputChange}
                    name="color"
                    placeholder="#3498db"
                  />
                </div>
              </div>
            </div>

            <div className="form-preview">
              <h4>Aperçu</h4>
              <div 
                className="type-preview"
                style={{ 
                  backgroundColor: formData.color + '20',
                  borderLeft: `4px solid ${formData.color}`
                }}
              >
                <span className="preview-icon">{formData.icon}</span>
                <span className="preview-name">{formData.display_name || 'Nom du type'}</span>
                <p className="preview-description">{formData.description || 'Description du type...'}</p>
              </div>
            </div>

            <div className="form-actions">
              <button type="button" onClick={resetForm} className="btn btn-secondary">
                Annuler
              </button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Sauvegarde...' : (editingType ? 'Modifier' : 'Créer')}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="types-list">
        <h3>Types de Protection Existants ({guardTypes.length})</h3>
        
        {loading && guardTypes.length === 0 ? (
          <div className="loading">
            <div className="spinner"></div>
            <span>Chargement...</span>
          </div>
        ) : (
          <div className="types-grid">
            {guardTypes.map(type => (
              <div key={type.id} className="type-card">
                <div className="type-header">
                  <div className="type-info">
                    <span 
                      className="type-icon"
                      style={{ color: type.color }}
                    >
                      {type.icon}
                    </span>
                    <div>
                      <h4>{type.display_name}</h4>
                      <small className="type-name">ID: {type.name}</small>
                    </div>
                  </div>
                  <div className="type-status">
                    <span className={`status ${type.is_active ? 'active' : 'inactive'}`}>
                      {type.is_active ? '✅ Actif' : '❌ Inactif'}
                    </span>
                  </div>
                </div>

                <p className="type-description">{type.description}</p>

                <div className="type-stats">
                  <small>
                    Créé: {new Date(type.created_at).toLocaleDateString()}
                    {type.updated_at !== type.created_at && (
                      <> • Modifié: {new Date(type.updated_at).toLocaleDateString()}</>
                    )}
                  </small>
                </div>

                <div className="type-actions">
                  <button
                    className="btn btn-icon btn-primary"
                    title="Gérer les Champs"
                    onClick={() => setSelectedType(type.name)}
                    disabled={loading}
                  >
                    🔧
                  </button>
                  <button
                    className="btn btn-icon btn-secondary"
                    title="Modifier"
                    onClick={() => handleEdit(type)}
                    disabled={loading}
                  >
                    ✏️
                  </button>
                  <button
                    className="btn btn-icon btn-danger"
                    title="Supprimer"
                    onClick={() => handleDelete(type.id, type.display_name)}
                    disabled={loading}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {guardTypes.length === 0 && !loading && (
          <div className="empty-state">
            <p>Aucun type de protection trouvé.</p>
            <button 
              className="btn btn-primary"
              onClick={() => setShowForm(true)}
            >
              Créer le premier type
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default GuardTypeManager;
