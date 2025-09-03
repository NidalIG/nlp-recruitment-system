// src/services/userApiService.js
class UserApiService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';
  }

  // Récupération du token d'authentification
  getAuthHeaders = () => {
    const token = sessionStorage.getItem('authToken');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  };

  // Gestion générique des erreurs
  handleResponse = async (response) => {
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Une erreur est survenue');
    }
    return response.json();
  };

  // ===== GESTION DU PROFIL UTILISATEUR =====
  
  getUserProfile = async () => {
    try {
      const response = await fetch(`${this.baseURL}/user/profile`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de la récupération du profil: ${error.message}`);
    }
  };

  updateUserProfile = async (profileData) => {
    try {
      const response = await fetch(`${this.baseURL}/user/profile`, {
        method: 'PUT',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(profileData)
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de la mise à jour du profil: ${error.message}`);
    }
  };

  // ===== GESTION CV PARSING =====
  
  uploadAndParseCV = async (cvFile) => {
    try {
      const formData = new FormData();
      formData.append('cv', cvFile);

      const token = sessionStorage.getItem('authToken');
      const response = await fetch(`${this.baseURL}/user/cv/parse`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors du parsing du CV: ${error.message}`);
    }
  };

  getCVParsings = async () => {
    try {
      const response = await fetch(`${this.baseURL}/user/cv/history`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de la récupération des CV parsés: ${error.message}`);
    }
  };

  // ===== GESTION JOB MATCHING =====
  
  searchJobs = async (searchCriteria) => {
    try {
      const response = await fetch(`${this.baseURL}/user/jobs/search`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(searchCriteria)
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de la recherche d'emplois: ${error.message}`);
    }
  };

  getJobMatchings = async () => {
    try {
      const response = await fetch(`${this.baseURL}/user/jobs/matches`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de la récupération des matchings: ${error.message}`);
    }
  };

  saveJobMatching = async (matchingData) => {
    try {
      const response = await fetch(`${this.baseURL}/user/jobs/matches`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(matchingData)
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de la sauvegarde du matching: ${error.message}`);
    }
  };

  // ===== GESTION DES QUIZ =====
  
  startQuiz = async (quizType) => {
    try {
      const response = await fetch(`${this.baseURL}/user/quiz/start`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ quizType })
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors du démarrage du quiz: ${error.message}`);
    }
  };

  submitQuizAnswer = async (quizId, answers) => {
    try {
      const response = await fetch(`${this.baseURL}/user/quiz/${quizId}/submit`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ answers })
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de la soumission des réponses: ${error.message}`);
    }
  };

  getQuizResults = async () => {
    try {
      const response = await fetch(`${this.baseURL}/user/quiz/results`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de la récupération des résultats: ${error.message}`);
    }
  };

  // ===== GESTION DE L'ASSISTANT IA =====
  
  getChatHistory = async () => {
    try {
      const response = await fetch(`${this.baseURL}/user/assistant/chat/history`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de la récupération de l'historique: ${error.message}`);
    }
  };

  sendMessageToAssistant = async (message) => {
    try {
      const response = await fetch(`${this.baseURL}/user/assistant/chat`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({ message })
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors de l'envoi du message: ${error.message}`);
    }
  };

  // ===== DASHBOARD DATA =====
  
  getDashboardData = async () => {
    try {
      const response = await fetch(`${this.baseURL}/user/dashboard`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      return this.handleResponse(response);
    } catch (error) {
      throw new Error(`Erreur lors du chargement du dashboard: ${error.message}`);
    }
  };

  // ===== EXPORT DATA =====
  
  exportUserData = async (format = 'json') => {
    try {
      const response = await fetch(`${this.baseURL}/user/export?format=${format}`, {
        method: 'GET',
        headers: this.getAuthHeaders()
      });
      
      if (!response.ok) {
        throw new Error('Erreur lors de l\'export');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `user-data.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      return { success: true };
    } catch (error) {
      throw new Error(`Erreur lors de l'export: ${error.message}`);
    }
  };
}

// Instance singleton
const userApiService = new UserApiService();
export default userApiService;