import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BookOpen, HeartPulse, MessageCircle } from "lucide-react";
import { useAuth } from "../../lib/auth";
import { appointments, conversations, patients } from "../../lib/services";
import {
  PageHeader,
  LoadingState,
  ErrorState,
  EmptyState,
} from "../../components/common";
import { AppointmentCard } from "../appointments/AppointmentPages";
export function Dashboard() {
  const { session } = useAuth();
  const profile = useQuery({
    queryKey: ["patient", session?.user.id],
    queryFn: patients.me,
  });
  const data = useQuery({
    queryKey: ["appointments", session?.user.id],
    queryFn: appointments.list,
  });
  const history = useQuery({
    queryKey: ["conversations", session?.user.id],
    queryFn: conversations.list,
  });
  const upcoming =
    data.data
      ?.filter(
        (a) =>
          ["PENDING", "CONFIRMED", "RESCHEDULED"].includes(a.status) &&
          new Date(a.start_time) > new Date(),
      )
      .sort((a, b) => a.start_time.localeCompare(b.start_time)) ?? [];
  return (
    <>
      <PageHeader
        eyebrow="YOUR CARE AT A GLANCE"
        title="Welcome back"
        description={
          profile.data?.name
            ? `Hello, ${profile.data.name}. Everything you need to plan your next visit is here.`
            : "Everything you need to plan your next visit, right here."
        }
      />
      <div className="welcome-card">
        <div>
          <span className="eyebrow">YOUR NEXT STEP</span>
          <h2>Good care starts with a simple plan.</h2>
          <p>
            Search trusted doctors, explore available times, or ask our
            assistant for help.
          </p>
          <Link className="button cream" to="/doctors">
            Find a doctor <ArrowRight size={18} />
          </Link>
        </div>
        <div className="welcome-art">
          <HeartPulse size={86} strokeWidth={1.3} />
        </div>
      </div>
      <div className="section-heading">
        <h2>Upcoming appointments</h2>
        <Link to="/appointments">
          View all <ArrowRight size={16} />
        </Link>
      </div>
      {data.isLoading ? (
        <LoadingState />
      ) : data.isError ? (
        <ErrorState
          message="Appointments could not be loaded."
          retry={() => void data.refetch()}
        />
      ) : upcoming.length ? (
        <div className="card-grid">
          {upcoming.slice(0, 2).map((a) => (
            <AppointmentCard key={a.id} appointment={a} />
          ))}
        </div>
      ) : (
        <EmptyState>
          No upcoming appointments yet. <Link to="/doctors">Find a doctor</Link>{" "}
          to get started.
        </EmptyState>
      )}
      <div className="quick-grid">
        <Link to="/doctors" className="quick-card">
          <HeartPulse />
          <strong>Book an appointment</strong>
          <span>Choose a doctor and time</span>
          <ArrowRight size={18} />
        </Link>
        <Link to="/appointments" className="quick-card">
          <strong>My appointments</strong>
          <span>View and manage visits</span>
          <ArrowRight size={18} />
        </Link>
        <Link to="/chat" className="quick-card">
          <MessageCircle />
          <strong>Ask the assistant</strong>
          <span>Get help finding care</span>
          <ArrowRight size={18} />
        </Link>
        <Link to="/knowledge" className="quick-card">
          <BookOpen />
          <strong>Clinic guide</strong>
          <span>Answers from approved policies</span>
          <ArrowRight size={18} />
        </Link>
      </div>
      <div className="section-heading">
        <h2>Recent conversations</h2>
        <Link to="/chat">
          Open assistant <ArrowRight size={16} />
        </Link>
      </div>
      {history.isLoading ? (
        <LoadingState />
      ) : history.isError ? (
        <ErrorState
          message="Conversations could not be loaded."
          retry={() => void history.refetch()}
        />
      ) : history.data?.length ? (
        <div className="card details-card">
          {history.data.slice(0, 3).map((conversation) => (
            <p key={conversation.id}>
              <Link
                to={`/chat?conversation=${encodeURIComponent(conversation.id)}`}
              >
                {conversation.title}
              </Link>
            </p>
          ))}
        </div>
      ) : (
        <EmptyState>
          No conversations yet. <Link to="/chat">Ask the assistant</Link>.
        </EmptyState>
      )}
    </>
  );
}
