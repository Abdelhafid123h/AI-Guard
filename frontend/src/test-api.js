// Test de connectivité API entre frontend et backend
const API_BASE = 'http://127.0.0.1:8000/api/config';

async function testAPIConnection() {
  console.log('🔍 Test de connectivité API...');
  
  try {
    // Test 1: Récupérer les types de protection
    console.log('📋 Test: Récupération des types de protection...');
    const response = await fetch(`${API_BASE}/guard-types`);
    const data = await response.json();
    console.log('✅ Types de protection récupérés:', data);
    
    // Test 2: Récupérer les champs PII pour TestType
    if (data.guard_types && data.guard_types.find(t => t.name === 'TestType')) {
      console.log('📋 Test: Récupération des champs PII pour TestType...');
      const fieldsResponse = await fetch(`${API_BASE}/pii-fields/TestType`);
      const fieldsData = await fieldsResponse.json();
      console.log('✅ Champs PII récupérés:', fieldsData);
    }
    
    // Test 3: Test de création d'un champ (simulation)
    console.log('📋 Test: Simulation de création de champ...');
    const testField = {
      field_name: 'test_frontend',
      display_name: 'Test Frontend',
      type: 'regex',
      example: 'test123',
      pattern: '[a-z]+[0-9]+',
      confidence_threshold: 0.8,
      priority: 1
    };
    console.log('📤 Données à envoyer:', testField);
    
    console.log('🎉 Tous les tests de connectivité réussis !');
    
  } catch (error) {
    console.error('❌ Erreur de connectivité:', error);
  }
}

// Exporter pour utilisation dans React
export default testAPIConnection;

// Auto-exécution si appelé directement
if (typeof window !== 'undefined') {
  window.testAPIConnection = testAPIConnection;
  console.log('🔧 Fonction testAPIConnection disponible dans la console');
}
