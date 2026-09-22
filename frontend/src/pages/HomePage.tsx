import CarStage from "../components/home/CarStage";
import QueryBox from "../components/home/QueryBox";
import Wordmark from "../components/home/Wordmark";
import { navigate } from "../router";
import "./home.css";

export default function HomePage() {
  const handleSubmit = (query: string) => navigate(`/chat?q=${encodeURIComponent(query)}`);

  return (
    <div className="home">
      <CarStage />
      <header className="home__header">
        <Wordmark />
        <span className="home__divider" aria-hidden="true" />
        <p className="home__tagline">Real owners choose their cars through reviews</p>
      </header>
      <main className="home__main">
        <h1 className="home__title">
          <span className="home__title-white">Ask. Compare.</span>{" "}
          <span className="home__title-gold">Choose Smarter.</span>
        </h1>
        <QueryBox onSubmit={handleSubmit} />
      </main>
    </div>
  );
}
