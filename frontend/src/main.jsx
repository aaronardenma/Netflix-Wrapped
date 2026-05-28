import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import { store } from "./store/store";
import { authExpired } from "./store/authSlice";
import { setUnauthorizedHandler } from "./services/api";
import { Provider } from "react-redux";
import './index.css'

setUnauthorizedHandler(() => {
  store.dispatch(authExpired());
});

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </StrictMode>,
)
