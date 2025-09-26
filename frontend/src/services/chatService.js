import api from './api';

export const chatService = {
  async sendMessage(message, language = 'en') {
    try {
      const formData = new URLSearchParams();
      formData.append('message', message);
      formData.append('language', language);

      const response = await api.post('/api/chat', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('Send message error:', error);
      return {
        success: false,
        message: error.response?.data?.message || 'Failed to send message'
      };
    }
  },

  async getChatHistory() {
    try {
      const response = await api.get('/api/chat');
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('Get chat history error:', error);
      return {
        success: false,
        message: error.response?.data?.message || 'Failed to get chat history'
      };
    }
  },

  async startVoiceRecording() {
    try {
      const response = await api.post('/api/voice/start', {});
      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('Start voice recording error:', error);
      return {
        success: false,
        message: error.response?.data?.message || 'Failed to start voice recording'
      };
    }
  },

  async transcribeAudio(audioBlob) {
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.wav');

      const response = await api.post('/api/voice/transcribe', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return {
        success: true,
        data: response.data
      };
    } catch (error) {
      console.error('Transcribe audio error:', error);
      return {
        success: false,
        message: error.response?.data?.message || 'Failed to transcribe audio'
      };
    }
  }
};
