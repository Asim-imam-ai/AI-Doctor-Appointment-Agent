import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CalendarCheck,
  HeartPulse,
  LockKeyhole,
  Menu,
  MessageCircle,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";

const steps = [
  {
    number: "01",
    title: "Find your doctor",
    text: "Search the live doctor directory by specialty, name, clinic, or location.",
    icon: Search,
  },
  {
    number: "02",
    title: "Choose a time",
    text: "Explore available appointment slots that fit your schedule.",
    icon: CalendarCheck,
  },
  {
    number: "03",
    title: "Review and confirm",
    text: "Approve the appointment details yourself before any booking is made.",
    icon: ShieldCheck,
  },
];
export function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="landing">
      <header className="landing-header">
        <Link to="/" className="brand">
          <span className="brand-icon">
            <HeartPulse size={23} />
          </span>
          <span>
            CarePath<small>Patient portal</small>
          </span>
        </Link>
        <button
          className="icon-button landing-menu-toggle"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? <X /> : <Menu />}
        </button>
        <nav className={menuOpen ? "open" : ""} aria-label="Public navigation">
          <Link onClick={() => setMenuOpen(false)} to="/">
            Home
          </Link>
          <Link onClick={() => setMenuOpen(false)} to="/doctors">
            Find doctors
          </Link>
          <a onClick={() => setMenuOpen(false)} href="#how-it-works">
            How it works
          </a>
          <Link onClick={() => setMenuOpen(false)} to="/login">
            Log in
          </Link>
          <Link
            onClick={() => setMenuOpen(false)}
            to="/register"
            className="button"
          >
            Get started <ArrowRight size={16} />
          </Link>
        </nav>
      </header>
      <main>
        <section className="landing-hero">
          <div>
            <span className="eyebrow">CARE, ON YOUR TERMS</span>
            <h1>
              Find the right doctor.
              <br />
              <em>Book with confidence.</em>
            </h1>
            <p>
              Discover doctors, explore available appointments, and manage
              bookings with an AI-powered assistant. You stay in control of
              every decision.
            </p>
            <div className="landing-actions">
              <Link to="/doctors" className="button">
                Find a doctor <ArrowRight size={18} />
              </Link>
              <Link to="/chat" className="button secondary">
                Explore AI assistant
              </Link>
            </div>
            <div className="landing-trust">
              <ShieldCheck size={19} />
              Your booking is confirmed only after you approve it.
            </div>
          </div>
          <div className="landing-visual" aria-hidden="true">
            <div className="landing-visual-orbit">
              <HeartPulse size={78} strokeWidth={1.2} />
            </div>
            <div className="floating-tile top">
              <Search size={20} />
              <span>Discover care that fits</span>
            </div>
            <div className="floating-tile bottom">
              <CalendarCheck size={20} />
              <span>Choose your own time</span>
            </div>
          </div>
        </section>
        <section id="how-it-works" className="landing-section">
          <span className="eyebrow">SIMPLE FROM START TO FINISH</span>
          <h2>Care in three clear steps</h2>
          <p className="section-intro">
            No uncertainty about what happens next. Every appointment change
            includes a chance to review.
          </p>
          <div className="landing-steps">
            {steps.map((step) => (
              <article key={step.number} className="landing-step">
                <span>{step.number}</span>
                <step.icon size={26} />
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="landing-feature">
          <div>
            <span className="eyebrow">A HELPFUL GUIDE, WHEN YOU NEED ONE</span>
            <h2>Ask, explore, decide.</h2>
            <p>
              Our AI assistant can help you find doctors, check availability,
              and understand approved clinic policies. You approve bookings,
              cancellations, and rescheduling requests yourself.
            </p>
            <Link className="text-button" to="/chat">
              Meet the assistant <ArrowRight size={17} />
            </Link>
          </div>
          <div className="landing-feature-icon">
            <MessageCircle size={70} strokeWidth={1.2} />
          </div>
        </section>
        <section className="landing-section privacy-section">
          <div>
            <LockKeyhole size={33} />
            <span className="eyebrow">YOUR INFORMATION, YOUR CONTROL</span>
            <h2>Built for clarity and privacy.</h2>
            <p>
              Sign in securely with Supabase Auth. Your conversations and
              appointments are connected to your account, and appointment
              changes require your explicit approval.
            </p>
          </div>
        </section>
        <section className="landing-cta">
          <h2>Ready to make your next appointment easier?</h2>
          <p>
            Search the doctor directory or create your account to get started.
          </p>
          <Link to="/register" className="button cream">
            Create your account <ArrowRight size={17} />
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <Link className="brand" to="/">
          <span className="brand-icon">
            <HeartPulse size={20} />
          </span>
          CarePath
        </Link>
        <p>
          For appointment administration and clinic information. This service
          does not provide medical diagnosis or emergency care.
        </p>
      </footer>
    </div>
  );
}
