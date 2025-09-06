import { useEffect, useState, useCallback } from "react";
import userApiService from "../services/userApiService";
import { useAuth } from "../contexts/AuthContext";

export default function useAssistantCards(refreshKey = 0) {
  const { isAuthenticated } = useAuth();
  const [cards, setCards] = useState({ profile: null, cv: null, job: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    setError(null);
    try {
      const data = await userApiService.getAssistantCards();
      setCards(data.cards || { profile: null, cv: null, job: null });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => { refresh(); }, [refresh, refreshKey, isAuthenticated]);

  return { cards, loading, error, refresh };
}
