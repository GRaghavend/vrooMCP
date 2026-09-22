import App from "./App";
import HomePage from "./pages/HomePage";
import { usePathname } from "./router";

export default function Root() {
  // `/chat` is the existing chat + evidence app, untouched; everything else is the homepage.
  return usePathname().startsWith("/chat") ? <App /> : <HomePage />;
}
