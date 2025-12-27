const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5500';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:5500';

export const api = {
  async getAgents() {
    const response = await fetch(`${API_URL}/agents`);
    return response.json();
  },

  async getSessions() {
    const response = await fetch(`${API_URL}/sessions`);
    return response.json();
  },

  async createSession(agentName) {
    const response = await fetch(`${API_URL}/sessions?agent_name=${agentName}`, {
      method: 'POST',
    });
    return response.json();
  },

  async getSession(sessionId) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}`);
    return response.json();
  },

  async stopSession(sessionId) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}/stop`, {
      method: 'POST',
    });
    return response.json();
  },

  async restartSession(sessionId) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}/restart`, {
      method: 'POST',
    });
    return response.json();
  },

  async deleteSession(sessionId) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  async getMessages(sessionId) {
    const response = await fetch(`${API_URL}/sessions/${sessionId}/messages`);
    return response.json();
  },

  createWebSocket(sessionId) {
    return new WebSocket(`${WS_URL}/ws/${sessionId}`);
  }
};
