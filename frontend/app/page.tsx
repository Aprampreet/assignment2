import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ClipboardList, HeartPulse, ShieldCheck, Stethoscope, UsersRound } from "lucide-react";
import { Brand } from "@/components/brand";

export default function Home() {
  return <>
    <header className="public-header"><div className="public-wrap header-inner">
      <Brand /><nav aria-label="Main navigation"><a href="#platform">The platform</a><a href="#workflow">How it works</a></nav>
      <div className="actions"><Link href="/login">Sign in</Link><Link className="button" href="/register">Create account</Link></div>
    </div></header>
    <main>
      <section className="public-wrap hero">
        <div className="hero-copy">
          <div className="hero-kicker"><span /> A clearer way to coordinate care</div>
          <h1>Care works<br /><em>better together.</em></h1>
          <p>Keep the people, records and decisions behind every patient journey connected in one secure workspace.</p>
          <div className="actions"><Link className="button" href="/register">Get started <ArrowRight size={17} /></Link><Link className="hero-link" href="/login">Open your workspace <ArrowRight size={16} /></Link></div>
          <div className="hero-trust"><ShieldCheck size={18} /><span>Role based access for every care team member</span></div>
        </div>
        <figure><Image src="/clinician.webp" alt="Illustrative portrait of a clinician in a consultation room" fill preload sizes="(max-width: 760px) 100vw, 52vw" /><figcaption>Illustrative image</figcaption><div className="hero-image-note"><Stethoscope size={21} /><span>People first.<br /><strong>Connected care.</strong></span></div></figure>
      </section>
      <div className="public-wrap service-line"><span>Built around the people who provide and receive care</span><span>01 / 03</span></div>
      <section className="platform" id="platform"><div className="public-wrap">
        <div className="platform-heading"><h2>Every role sees the care that matters.</h2><p>From a patient’s first profile to an active doctor assignment, Medora keeps each step clear and accountable.</p></div>
        <div className="platform-grid">
          <article><span className="feature-number">01</span><HeartPulse /><h3>For patients</h3><p>Keep your details current, find doctors and see the people on your care team.</p><Link href="/register">Create an account <ArrowRight size={16} /></Link></article>
          <article><span className="feature-number">02</span><ClipboardList /><h3>For doctors</h3><p>See your assigned patients and maintain one trusted professional profile.</p><Link href="/register">Request access <ArrowRight size={16} /></Link></article>
          <article><span className="feature-number">03</span><UsersRound /><h3>For supervisors</h3><p>Coordinate records, assignments and approvals with a clear view of activity.</p><Link href="/register">Request access <ArrowRight size={16} /></Link></article>
        </div>
      </div></section>
      <section className="story" aria-labelledby="story-heading"><div className="public-wrap story-grid">
        <div className="story-image"><Image src="/consultation.jpg" alt="Illustrative image of a doctor listening to a patient during a consultation" fill sizes="(max-width: 760px) 100vw, 58vw" /><span>Illustrative image</span></div>
        <div className="story-copy"><div className="story-symbol"><HeartPulse size={30} strokeWidth={1.4} /></div><h2 id="story-heading">Care has context.<br /><em>Your workspace should too.</em></h2>
          <p>Every patient record connects to real people and decisions. Medora makes those connections visible to the team members who need them.</p>
          <div className="story-points"><div><span>01</span><strong>Clear ownership</strong><p>Supervisors know which records and assignments they manage.</p></div><div><span>02</span><strong>Focused access</strong><p>Doctors and patients see the care information relevant to them.</p></div></div>
          <Link href="/login">See your workspace <ArrowRight size={18} /></Link>
        </div>
      </div></section>
      <section className="public-wrap workflow" id="workflow">
        <div className="workflow-intro"><h2>One connected path through care.</h2><p>Good coordination starts with knowing who is responsible for what. Medora gives each person a focused place to act.</p><Link className="text-link" href="/login">Explore your workspace <ArrowRight size={16} /></Link></div>
        <ol><li><span className="step-number">01</span><div><strong>Build the right profile</strong><span>Patients register directly. Clinicians and supervisors request administrator approval.</span></div></li>
          <li><span className="step-number">02</span><div><strong>Connect the care team</strong><span>Supervisors assign active doctors to the patients they support.</span></div></li>
          <li><span className="step-number">03</span><div><strong>Stay in step</strong><span>Each workspace shows the records and responsibilities relevant to its role.</span></div></li></ol>
      </section>
      <section className="closing"><div className="public-wrap closing-inner"><div><h2>Care is a team effort.<br /><em>Make every connection count.</em></h2><p>Get a clear view of the people and decisions behind better coordinated care.</p></div><Link className="button" href="/register">Create your account <ArrowRight size={18} /></Link></div></section>
    </main>
    <footer className="public-footer"><div className="public-wrap"><Brand /><p>Healthcare management software demonstration.</p><Link href="/login">Workspace sign in</Link></div></footer>
  </>;
}
