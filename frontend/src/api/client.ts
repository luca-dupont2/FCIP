import axios from 'axios';
import { notifications } from '@mantine/notifications';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Unknown error';
    notifications.show({
      title: 'Error',
      message,
      color: 'red',
    });
    return Promise.reject(error);
  }
);

export default client;
