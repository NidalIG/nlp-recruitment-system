// src/components/layout/MyCareerAILanding.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, Users, MessageCircle, GraduationCap, Clock, Shield, Zap, ChevronRight, Brain, Target } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import DemoPage from '../../components/layout/DemoPage';

const HomePage = () => {
  const navigate = useNavigate();
  const { user } = useAuth(); // récupération de l'utilisateur connecté
  const [isVisible, setIsVisible] = useState(false);
  
  useEffect(() => {
    setIsVisible(true);
  }, []);

  const features = [
    {
      icon: <Target className="w-8 h-8 text-blue-400" />,
      title: "Matching CV ↔ Emploi",
      description: "L'IA analyse les compétences et les compare aux exigences des postes pour des correspondances parfaites.",
      gradient: "from-blue-500 to-cyan-400"
    },
    {
      icon: <Brain className="w-8 h-8 text-purple-400" />,
      title: "Quiz Automatisés",
      description: "Générez des quiz personnalisés adaptés aux postes spécifiques pour évaluer les candidats.",
      gradient: "from-purple-500 to-pink-400"
    },
    {
      icon: <MessageCircle className="w-8 h-8 text-green-400" />,
      title: "Recommandations Chatbot",
      description: "Recommandations de formation intelligentes et orientation de carrière pour les candidats.",
      gradient: "from-green-500 to-emerald-400"
    },
    {
      icon: <GraduationCap className="w-8 h-8 text-orange-400" />,
      title: "Assistant Pédagogique",
      description: "Compagnon d'apprentissage intelligent pour guider les candidats dans leur développement professionnel.",
      gradient: "from-orange-500 to-yellow-400"
    }
  ];

  const benefits = [
    {
      icon: <Clock className="w-6 h-6 text-blue-400" />,
      title: "Gain de Temps pour les Recruteurs",
      description: "Automatisez les processus de sélection et concentrez-vous sur l'essentiel."
    },
    {
      icon: <Shield className="w-6 h-6 text-green-400" />,
      title: "Expérience Équitable pour les Candidats",
      description: "Éliminez les biais avec des évaluations objectives pilotées par l'IA."
    },
    {
      icon: <Zap className="w-6 h-6 text-purple-400" />,
      title: "Outils IA et NLP Modernes",
      description: "Technologie de pointe pour l'excellence du recrutement."
    }
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white overflow-hidden">
      {/* Hero Section */}
      <section className="relative pt-20 pb-32 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-blue-900/20 to-purple-900/20">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        </div>
        
        <div className={`relative z-10 max-w-7xl mx-auto px-6 text-center transition-all duration-1000 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}>
          <h2 className="text-5xl md:text-7xl font-bold mb-8 leading-tight">
            <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              Boostez Votre Carrière
            </span>
            <br />
            <span className="text-white">avec l'Assistance IA</span>
          </h2>
          
          <p className="text-xl md:text-2xl text-gray-300 mb-12 max-w-3xl mx-auto leading-relaxed">
            Obtenez des correspondances d'emploi personnalisées, préparez-vous avec des quiz alimentés par l'IA, 
            et propulsez votre carrière vers de nouveaux sommets grâce à la technologie NLP intelligente.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-6">
            {/* Get Started → Register or user space */}
            <button 
              onClick={() => user ? navigate(`/app/${user.id}`) : navigate('/register')} 
              className="px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl font-semibold text-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-200 transform hover:scale-105 shadow-2xl hover:shadow-3xl flex items-center space-x-2"
            >
              <span>Commencer</span>
              <ChevronRight className="w-5 h-5" />
            </button>

            {/* Watch Demo → si connecté → espace utilisateur */}
            <button 
              onClick={() => navigate('/demo')} 
              className="px-8 py-4 border border-gray-600 rounded-xl font-semibold text-lg hover:border-gray-400 hover:bg-gray-800/50 transition-all duration-200 transform hover:scale-105"
            >
              Voir la Démo
            </button>
          </div>
        </div>
      </section>

      {/* Key Features Section */}
      <section className="py-24 bg-gray-800/50">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h3 className="text-4xl md:text-5xl font-bold mb-6">
              <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Fonctionnalités Clés
              </span>
            </h3>
            <p className="text-xl text-gray-300 max-w-2xl mx-auto">
              Outils puissants pilotés par l'IA conçus pour transformer votre expérience de recrutement
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div 
                key={index}
                className={`group relative p-8 rounded-2xl bg-gray-800/60 backdrop-blur-sm border border-gray-700 hover:border-gray-600 transition-all duration-300 transform hover:-translate-y-2 hover:shadow-2xl ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
                style={{ transitionDelay: `${index * 100}ms` }}
              >
                <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity duration-300`}></div>
                <div className="relative z-10">
                  <div className="mb-4 p-3 bg-gray-700/50 rounded-xl w-fit">
                    {feature.icon}
                  </div>
                  <h4 className="text-xl font-semibold mb-3 text-white group-hover:text-blue-300 transition-colors duration-200">
                    {feature.title}
                  </h4>
                  <p className="text-gray-300 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h3 className="text-4xl md:text-5xl font-bold mb-6">
              <span className="bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent">
                Pourquoi Nous Choisir ?
              </span>
            </h3>
            <p className="text-xl text-gray-300 max-w-2xl mx-auto">
              Découvrez les avantages de la technologie de recrutement de nouvelle génération
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {benefits.map((benefit, index) => (
              <div 
                key={index}
                className={`group p-8 rounded-2xl bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm border border-gray-700 hover:border-gray-600 transition-all duration-300 transform hover:scale-105 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
                style={{ transitionDelay: `${index * 150}ms` }}
              >
                <div className="flex items-start space-x-4">
                  <div className="flex-shrink-0 p-3 bg-gray-700/50 rounded-xl">
                    {benefit.icon}
                  </div>
                  <div>
                    <h4 className="text-xl font-semibold mb-3 text-white group-hover:text-green-300 transition-colors duration-200">
                      {benefit.title}
                    </h4>
                    <p className="text-gray-300 leading-relaxed">
                      {benefit.description}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600/20 to-purple-600/20">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h3 className="text-3xl md:text-4xl font-bold mb-6">
            Prêt à Transformer Votre Recrutement ?
          </h3>
          <p className="text-xl text-gray-300 mb-8">
            Rejoignez des milliers d'entreprises qui utilisent déjà My Career AI pour trouver les candidats parfaits.
          </p>
          <button 
            onClick={() => user ? navigate(`/app/${user.id}`) : navigate('/register')}
            className="px-10 py-4 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl font-semibold text-lg hover:from-blue-600 hover:to-purple-700 transition-all duration-200 transform hover:scale-105 shadow-2xl hover:shadow-3xl"
          >
            Commencez Votre Essai Gratuit
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 border-t border-gray-800 py-12">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="col-span-2">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-600 rounded-lg flex items-center justify-center">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  My Career AI
                </h1>
              </div>
              <p className="text-gray-400 mb-6 max-w-md">
                Révolutionner le recrutement grâce à l'IA avancée et à la technologie NLP. 
                Construire des processus d'embauche plus intelligents et plus équitables pour l'avenir.
              </p>
              <div className="text-gray-400">
                <p>Contact : team@mycareerai.com</p>
                <p className="mt-2">Projet de Recherche Universitaire</p>
              </div>
            </div>
            
            <div>
              <h4 className="text-lg font-semibold mb-4 text-white">Entreprise</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors duration-200">À Propos</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors duration-200">Politique de Confidentialité</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors duration-200">Conditions d'Utilisation</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="text-lg font-semibold mb-4 text-white">Support</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors duration-200">Centre d'Aide</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors duration-200">Contacter le Support</a></li>
                <li><a href="#" className="text-gray-400 hover:text-white transition-colors duration-200">Documentation</a></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-gray-800 mt-12 pt-8 text-center">
            <p className="text-gray-400">
              © 2025 My Career AI. Tous droits réservés. Conçu avec ❤️ pour un meilleur recrutement.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;