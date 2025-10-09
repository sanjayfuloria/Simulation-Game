"use client";

import React, { useState, FormEvent } from "react";
import DatePicker from "react-datepicker";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import {
  Protect,
  UserButton,
  SignInButton,
  SignedIn,
  SignedOut,
  useAuth,
} from "@clerk/nextjs";

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="container mx-auto px-4 py-12">
          <h2 className="text-2xl font-bold text-red-600 mb-4">An error occurred</h2>
          <pre className="whitespace-pre-wrap bg-gray-100 dark:bg-gray-900 p-4 rounded-md text-sm overflow-auto">
            {this.state.error?.stack || this.state.error?.message}
          </pre>
          <p className="mt-4 text-gray-600">Please copy the stack trace above and paste it here so I can inspect it.</p>
        </div>
      );
    }
    return this.props.children as React.ReactElement;
  }
}

function ConsultationForm() {
  const { getToken } = useAuth();

  const [patientName, setPatientName] = useState("");
  const [visitDate, setVisitDate] = useState<Date | null>(new Date());
  const [notes, setNotes] = useState("");

  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setOutput("");
    setLoading(true);

    const jwt = await getToken();
    if (!jwt) {
      setOutput("Authentication required");
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    let buffer = "";

    try {
      await fetchEventSource("/api/stream", {
        signal: controller.signal,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${jwt}`,
        },
        body: JSON.stringify({
          patient_name: patientName,
          date_of_visit: visitDate?.toISOString().slice(0, 10),
          notes,
        }),
        onmessage(ev) {
          try {
            const parsed = JSON.parse(ev.data || "{}");
            if (parsed && typeof parsed.chunk === "string") {
              buffer += parsed.chunk;
              setOutput(buffer);
            }
          } catch {
            buffer += ev.data;
            setOutput(buffer);
          }
        },
        onclose() {
          setLoading(false);
        },
        onerror(err) {
          console.error("SSE error:", err);
          controller.abort();
          setLoading(false);
        },
      });
    } catch (err) {
      console.error("FetchEventSource failed:", err);
      setLoading(false);
    }
  }

  return (
    <div id="consultation" className="container mx-auto px-4 py-12 max-w-3xl">
      <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100 mb-8">Consultation Notes</h1>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
        <div className="space-y-2">
          <label htmlFor="patient" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Patient Name</label>
          <input id="patient" type="text" required value={patientName} onChange={(e) => setPatientName(e.target.value)} className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white" placeholder="Enter patient's full name" />
        </div>

        <div className="space-y-2">
          <label htmlFor="date" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Date of Visit</label>
          <DatePicker id="date" selected={visitDate} onChange={(d: Date | null) => setVisitDate(d)} dateFormat="yyyy-MM-dd" placeholderText="Select date" required className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white" />
        </div>

        <div className="space-y-2">
          <label htmlFor="notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Consultation Notes</label>
          <textarea id="notes" required rows={8} value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white" placeholder="Enter detailed consultation notes..." />
        </div>

        <button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200">{loading ? "Generating Summary..." : "Generate Summary"}</button>
      </form>

      {output && (
        <section className="mt-8">
          <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-tr from-indigo-600 to-blue-500 rounded-md flex items-center justify-center text-white font-bold">MN</div>
                <div>
                  <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">Consultation Summary</div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">AI-generated — {new Date().toLocaleString()}</div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    try { navigator.clipboard?.writeText(output); } catch {}
                  }}
                  className="px-3 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-200"
                >
                  Copy
                </button>
                <button
                  onClick={() => {
                    const blob = new Blob([output], { type: "text/markdown;charset=utf-8" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `consultation-summary-${Date.now()}.md`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                  }}
                  className="px-3 py-1 rounded-md bg-blue-600 text-white text-sm hover:bg-blue-700"
                >
                  Download
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-6">
              <div className="md:col-span-2">
                <div className="markdown-content prose prose-slate dark:prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{output}</ReactMarkdown>
                </div>
              </div>

              <aside className="md:col-span-1 border-l border-gray-100 dark:border-gray-800 pl-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Actions & Details</h4>
                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-2">
                  <li><strong>Model:</strong> gpt-4o-mini</li>
                  <li><strong>Tokens:</strong> approx {Math.max(100, Math.min(800, Math.ceil(output.length / 4)))}</li>
                  <li><strong>Format:</strong> Markdown</li>
                </ul>
                <div className="mt-4">
                  <button onClick={() => window.print()} className="w-full bg-gray-100 dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-200 py-2 rounded-md hover:bg-gray-200">Print</button>
                </div>
              </aside>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function PricingFallback() {
  const [showTrial, setShowTrial] = useState(false);

  return (
    <div className="container mx-auto px-4 py-12">
      <header className="text-center mb-12">
        <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-4">Healthcare Professional Plan</h1>
        <p className="text-gray-600 dark:text-gray-400 text-lg mb-8">Streamline your patient consultations with AI-powered summaries</p>
      </header>

      <div className="max-w-4xl mx-auto">
        <div id="signup-notice" className="mb-6 p-4 rounded-lg bg-yellow-50 dark:bg-yellow-900 border border-yellow-200 dark:border-yellow-800">
          <p className="text-yellow-800 dark:text-yellow-200">To use the Consultation Assistant you need an active subscription. Click &quot;Start Free Trial&quot; to try the assistant for a limited time, or contact sales to upgrade.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-semibold mb-2">Starter</h3>
            <p className="text-3xl font-bold text-blue-600 mb-2">Free</p>
            <ul className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              <li>✓ 10 summaries / month</li>
              <li>✓ Basic AI model</li>
              <li>✓ Email support</li>
            </ul>
            <SignedOut>
              <SignInButton mode="redirect" fallbackRedirectUrl="/product">
                <button className="w-full bg-gray-200 text-gray-800 py-2 rounded-md">Get Started</button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <button onClick={() => document.getElementById('signup-notice')?.scrollIntoView({behavior: 'smooth'})} className="w-full bg-gray-200 text-gray-800 py-2 rounded-md">Get Started</button>
            </SignedIn>
          </div>

          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border-2 border-blue-600">
            <h3 className="text-xl font-semibold mb-2">Pro</h3>
            <p className="text-3xl font-bold text-blue-600 mb-2">$10<span className="text-base text-gray-600">/month</span></p>
            <ul className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              <li>✓ Unlimited idea generation</li>
              <li>✓ Advanced AI models</li>
              <li>✓ Priority support</li>
            </ul>
            <SignedOut>
              <SignInButton mode="redirect" fallbackRedirectUrl="/product">
                <button className="w-full bg-blue-600 text-white py-2 rounded-md">Start Free Trial</button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <button onClick={() => { setShowTrial(true); setTimeout(()=>document.getElementById('consultation')?.scrollIntoView({behavior: 'smooth'}), 120); }} className="w-full bg-blue-600 text-white py-2 rounded-md">Start Free Trial</button>
            </SignedIn>
          </div>

          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-md border border-gray-200 dark:border-gray-700">
            <h3 className="text-xl font-semibold mb-2">Enterprise</h3>
            <p className="text-3xl font-bold text-blue-600 mb-2">Contact</p>
            <ul className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              <li>✓ SSO & advanced security</li>
              <li>✓ Dedicated support</li>
              <li>✓ Custom integrations</li>
            </ul>
            <SignedOut>
              <SignInButton mode="redirect" fallbackRedirectUrl="/product">
                <button className="w-full bg-gray-800 text-white py-2 rounded-md">Contact Sales</button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <button onClick={() => document.getElementById('signup-notice')?.scrollIntoView({behavior: 'smooth'})} className="w-full bg-gray-800 text-white py-2 rounded-md">Contact Sales</button>
            </SignedIn>
          </div>
        </div>

        {showTrial && (
          <div className="mt-8">
            <ConsultationForm />
          </div>
        )}
      </div>
    </div>
  );
}

export default function Product() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="absolute top-4 right-4">
        <UserButton showName={true} />
      </div>

      <ErrorBoundary>
        <Protect plan="premium_subscription" fallback={<PricingFallback />}>
          <ConsultationForm />
        </Protect>
      </ErrorBoundary>
    </main>
  );
}
