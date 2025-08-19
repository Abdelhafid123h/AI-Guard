import React, { useState, useEffect } from 'react';
import axios from 'axios';

const PIIProtectionForm = ({ onSubmit, loading }) => {
  const [guardTypes, setGuardTypes] = useState([]); // 🆕 Types dynamiques
  const [formData, setFormData] = useState({
    text: '',
    guardType: '',  // Sera défini après chargement des types
    llmProvider: 'openai'
  });

  const [exampleTexts, setExampleTexts] = useState({
    TypeA: "Bonjour, je suis Jean Dupont, né le 15/03/1980 à Lyon. Mon numéro de sécurité sociale est 1 80 03 69 123 456 78.",
    TypeB: "Ma carte bancaire est 4111 1111 1111 1111 et mon IBAN est FR76 3000 6000 0112 3456 7890 189.",
    InfoPerso: "Contactez-moi à jean.dupont@example.com ou au +33 6 12 34 56 78. J'habite au 123 Rue de la République, 75001 Paris."
  });

  // 🆕 NOUVEAU : Charger les types de protection depuis l'API
  useEffect(() => {
    const loadGuardTypes = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:8000/api/config/guard-types');
        const types = response.data.guard_types || [];
        setGuardTypes(types);
        
        // Définir le premier type comme défaut si aucun n'est sélectionné
        if (types.length > 0 && !formData.guardType) {
          setFormData(prev => ({ ...prev, guardType: types[0].name }));
        }
      } catch (error) {
        console.error('Erreur lors du chargement des types de protection:', error);
        // Fallback vers types statiques
        setGuardTypes([
          { name: 'TypeA', display_name: 'TypeA - Données Personnelles Identifiantes' },
          { name: 'TypeB', display_name: 'TypeB - Données Financières' },
          { name: 'InfoPerso', display_name: 'InfoPerso - Données de Contact' }
        ]);
        setFormData(prev => ({ ...prev, guardType: 'TypeA' }));
      }
    };

    loadGuardTypes();
  }, []);

  // 🆕 NOUVEAU : Charger les exemples depuis le backend (JSON)
  useEffect(() => {
    if (guardTypes.length === 0) return; // Attendre que les types soient chargés
    
    const loadExamples = async () => {
      try {
        const newExamples = {};
        
        for (const guardType of guardTypes) {
          try {
            const response = await axios.get(`http://127.0.0.1:8000/examples/${guardType.name}`);
            newExamples[guardType.name] = response.data.example_text;
          } catch (error) {
            console.warn(`Impossible de charger l'exemple pour ${guardType.name}, utilisation valeur par défaut`);
            // Garder la valeur par défaut si erreur
          }
        }
        
        // Mettre à jour seulement les exemples récupérés avec succès
        setExampleTexts(prev => ({ ...prev, ...newExamples }));
        
      } catch (error) {
        console.warn('Erreur chargement exemples depuis JSON, utilisation valeurs par défaut');
      }
    };

    loadExamples();
  }, [guardTypes]); // Dépendance sur guardTypes au lieu de []

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.text.trim()) {
      alert('Veuillez saisir un texte à analyser');
      return;
    }
    onSubmit(formData);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const loadExample = () => {
    setFormData({
      ...formData,
      text: exampleTexts[formData.guardType]
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>🔐 Analyseur de Protection des Données</h2>
      
      <div className="form-group">
        <label htmlFor="guardType">Type de Protection</label>
        <select
          id="guardType"
          name="guardType"
          value={formData.guardType}
          onChange={handleChange}
          required
        >
          {guardTypes.length === 0 ? (
            <option value="">Chargement des types...</option>
          ) : (
            guardTypes.map(type => (
              <option key={type.name} value={type.name}>
                {type.display_name || type.name}
              </option>
            ))
          )}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="llmProvider">Fournisseur IA</label>
        <select
          id="llmProvider"
          name="llmProvider"
          value={formData.llmProvider}
          onChange={handleChange}
          required
        >
          <option value="openai">OpenAI GPT</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="text">Texte à analyser</label>
        <textarea
          id="text"
          name="text"
          value={formData.text}
          onChange={handleChange}
          placeholder="Saisissez le texte contenant des informations sensibles..."
          rows="6"
          required
        />
        <button 
          type="button" 
          onClick={loadExample}
          className="btn example-btn"
          style={{
            marginTop: '10px',
            padding: '8px 16px',
            fontSize: '14px',
            background: 'transparent',
            border: '2px solid #667eea',
            color: '#667eea'
          }}
        >
          📝 Charger un exemple pour {formData.guardType}
        </button>
      </div>

      <button 
        type="submit" 
        className="btn" 
        disabled={loading}
        style={{ width: '100%', marginTop: '20px' }}
      >
        {loading ? '🔄 Analyse en cours...' : '🛡️ Analyser et Protéger'}
      </button>
    </form>
  );
};

export default PIIProtectionForm;
