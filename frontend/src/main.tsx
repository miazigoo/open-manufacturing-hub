import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { ToastViewport } from './components/toast/ToastViewport';
import { toast } from './components/toast/toastStore';
import { AuthGate } from './features/auth/AuthGate';
import { TourProvider } from './features/tours/TourProvider';
import { I18nProvider } from './i18n/I18nProvider';
import './styles/global.css';
import './styles/docs-print.css';

const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : String(error));
    },
    onSuccess: (_data, _variables, _context, mutation) => {
      const message = mutation.meta?.successMessage;
      if (typeof message === 'string') toast.success(message);
    },
  }),
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const routerBasename = import.meta.env.VITE_PUBLIC_BASE_PATH?.replace(/\/$/, '') || undefined;

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <BrowserRouter basename={routerBasename}>
          <AuthGate>
            <TourProvider>
              <App />
            </TourProvider>
          </AuthGate>
        </BrowserRouter>
        <ToastViewport />
      </I18nProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
