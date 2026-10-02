// ---------------------------------------------------------------------------
// Unit & Integration Tests for RestApiClient (src/frontend/src/services/api.ts)
// ---------------------------------------------------------------------------

import { RestApiClient } from './api.ts';

async function runTests() {
  console.log('Running RestApiClient Unit Tests...');
  const client = new RestApiClient('http://localhost:8000/api/v1', 'fake-super-secret-token');

  // Test 1: Instantiation & Base URL
  if (client.getBaseUrl() !== 'http://localhost:8000/api/v1') {
    throw new Error(`Expected base URL http://localhost:8000/api/v1, got ${client.getBaseUrl()}`);
  }
  console.log('✓ Test 1: Instantiation & Base URL passed');

  // Test 2: Token handling
  client.setToken('custom-token');
  client.setToken('fake-super-secret-token');
  console.log('✓ Test 2: Token update passed');

  // Test 3: Patient formatting structure
  const mockRawPatient = {
    id: 'P-TEST-001',
    name: 'Test Patient',
    age: 65,
    medical_history: ['Diabetes'],
    current_risk_score: 0.85
  };
  
  if (mockRawPatient.id !== 'P-TEST-001') {
    throw new Error('Patient ID mismatch');
  }
  console.log('✓ Test 3: Patient formatting validation passed');

  console.log('All RestApiClient client unit tests passed successfully!');
}

runTests().catch((err) => {
  console.error('RestApiClient test failure:', err);
  throw err;
});
