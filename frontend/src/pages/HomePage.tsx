import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

export default function HomePage() {
  const [orgName, setOrgName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleCreateOrg = async () => {
    if (!orgName.trim()) {
      setError('Organization name is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const org = await api.createOrg(orgName.trim());
      const cycle = await api.createCycle(org.id);
      navigate(`/cycles/${cycle.id}/questions`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create organization');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '50px auto', padding: '20px' }}>
      <h1 style={{ marginBottom: '30px', fontSize: '2rem' }}>Consulting Engine</h1>
      <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <h2 style={{ marginBottom: '20px' }}>Create Organization</h2>
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            Organization Name
          </label>
          <input
            type="text"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleCreateOrg()}
            placeholder="Enter organization name"
            style={{
              width: '100%',
              padding: '10px',
              fontSize: '1rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
            }}
            disabled={loading}
          />
        </div>
        {error && (
          <div style={{ color: 'red', marginBottom: '20px', fontSize: '0.9rem' }}>
            {error}
          </div>
        )}
        <button
          onClick={handleCreateOrg}
          disabled={loading || !orgName.trim()}
          style={{
            width: '100%',
            padding: '12px',
            fontSize: '1rem',
            backgroundColor: loading ? '#ccc' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Creating...' : 'Create Organization & Start Cycle'}
        </button>
      </div>
    </div>
  );
}
