import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export default function RegisterForm({ toggleForm }) {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { register, logout } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas');
      return;
    }
    if (formData.password.length < 6) {
      setError('Le mot de passe doit contenir au moins 6 caractères');
      return;
    }

    setLoading(true);
    try {
      const result = await register({
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        password: formData.password
      });

      if (result.success) {
        // Évite une auto-connexion qui vous renverrait ailleurs
        logout?.();

        // 👉 Si AuthPage fournit toggleForm, on bascule en place vers le Login
        if (typeof toggleForm === 'function') {
          toggleForm(); // passe à Login sur AuthPage
        } else {
          // 👉 Sinon on navigue vers la route /login
          navigate('/login', {
            replace: true,
            state: { justRegistered: true, email: formData.email }
          });
        }
      } else {
        setError(result.error || "Erreur lors de l'inscription");
      }
    } catch (e) {
      setError(e?.message || "Erreur lors de l'inscription");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  return (
    <div className="max-w-md mt-10 mx-auto bg-white p-8 border border-gray-300 rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">Inscription</h2>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="firstName" className="block text-gray-700 text-sm font-bold mb-2">Prénom</label>
          <input
            type="text" id="firstName" name="firstName" required
            value={formData.firstName} onChange={handleChange}
            autoComplete="given-name"
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="mb-4">
          <label htmlFor="lastName" className="block text-gray-700 text-sm font-bold mb-2">Nom</label>
          <input
            type="text" id="lastName" name="lastName" required
            value={formData.lastName} onChange={handleChange}
            autoComplete="family-name"
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="mb-4">
          <label htmlFor="email" className="block text-gray-700 text-sm font-bold mb-2">Email</label>
          <input
            type="email" id="email" name="email" required
            value={formData.email} onChange={handleChange}
            autoComplete="email"
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="mb-4">
          <label htmlFor="password" className="block text-gray-700 text-sm font-bold mb-2">Mot de passe</label>
          <input
            type="password" id="password" name="password" required minLength={6}
            value={formData.password} onChange={handleChange}
            autoComplete="new-password"
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="mb-6">
          <label htmlFor="confirmPassword" className="block text-gray-700 text-sm font-bold mb-2">Confirmer le mot de passe</label>
          <input
            type="password" id="confirmPassword" name="confirmPassword" required minLength={6}
            value={formData.confirmPassword} onChange={handleChange}
            autoComplete="new-password"
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
          />
        </div>

        <button
          type="submit" disabled={loading}
          className="w-full bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:opacity-50"
        >
          {loading ? 'Inscription...' : "S'inscrire"}
        </button>
      </form>

      <div className="text-center mt-4">
        <p className="text-gray-600">
          Déjà un compte ?{' '}
          <button
            type="button"
            onClick={() => {
              if (typeof toggleForm === 'function') {
                toggleForm(); // 👉 bascule vers Login sur AuthPage
              } else {
                navigate('/login'); // fallback si RegisterForm est utilisé hors AuthPage
              }
            }}
            className="text-blue-600 underline"
          >
            Connectez-vous
          </button>
        </p>
      </div>
    </div>
  );
}
