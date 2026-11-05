import { approaches, limits } from "../lib/results";
import { ThemeToggle } from "../components/theme-toggle";
import { Verdict } from "../components/verdict";
import { ResultsExplorer } from "../components/results-explorer";
import { LiveRun } from "../components/live-run";

function SectionHeading({
  label,
  title,
  children,
}: {
  label: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <p className="eyebrow">{label}</p>
        <h2>{title}</h2>
      </div>
      <p>{children}</p>
    </div>
  );
}

export default function Home() {
  const mock = process.env.NEXT_PUBLIC_API_MODE === "mock";
  return (
    <>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <header className="nav-shell">
        <nav className="nav wrap" aria-label="Main navigation">
          <a className="brand" href="#main">
            <span className="brand-icon" aria-hidden="true">
              ≡
            </span>
            Supplier Document Checker
          </a>
          <div className="nav-links">
            <a href="#workflow">Workflow</a>
            <a href="#journey">The approaches</a>
            <a href="#results">Results</a>
            <a href="#run">Try a check</a>
          </div>
          <ThemeToggle />
        </nav>
      </header>
      <main id="main">
        <section className="hero wrap" aria-labelledby="hero-title">
          <div className="hero-kicker">
            <p className="eyebrow">An experiment in careful procurement</p>
            <span className="tag">BIAI / interview demo</span>
          </div>
          <h1 id="hero-title">
            Read the quotation.
            <br />
            <span>See the reason behind the decision.</span>
          </h1>
          <div className="hero-intro">
            <p>
              Check supplier PDFs against a purchase request and company rules.
              Follow the evidence to an approval, a rejection, or a person who
              can resolve the doubt.
            </p>
            <a className="primary" href="#run">
              Explore a document check <span aria-hidden="true">↗</span>
            </a>
          </div>
          <div className="workspace hero-workspace">
            <div className="workspace-heading">
              <span>
                ▤ &nbsp; Sample review / <strong>supplier-pack-03.pdf</strong>
              </span>
              <span className="tag">Recorded / Approach 4</span>
            </div>
            <div className="workspace-body">
              <article className="source">
                <p className="eyebrow">Source evidence</p>
                <h2>SUPPLIER QUOTATION</h2>
                <div className="source-line">
                  <span>Extracted field</span>
                  <strong>unit_price</strong>
                </div>
                <div className="source-line">
                  <span>Exact source excerpt</span>
                  <mark>229.00</mark>
                </div>
                <div className="source-line">
                  <span>Requested maximum</span>
                  <strong>210</strong>
                </div>
                <p className="source-note">
                  Actual excerpt from fictional pack 03. An evidence view of the
                  quotation.
                </p>
              </article>
              <article className="procedure">
                <p className="eyebrow">Fixed procedure</p>
                <ol>
                  {[
                    "Read PDF",
                    "Agent 1 extracts facts",
                    "Code annotates warnings",
                    "Agent 2 judges",
                    "Report the decision",
                  ].map((step) => (
                    <li key={step}>
                      <span aria-hidden="true">✓</span>
                      {step}
                    </li>
                  ))}
                </ol>
              </article>
              <article className="decision">
                <p className="eyebrow">Recorded result</p>
                <Verdict value="Reject" />
                <h3>
                  The unit price exceeds
                  <br />
                  the requested maximum.
                </h3>
                <p>
                  229 is above the maximum of 210. The decision stays beside the
                  number that supports it.
                </p>
                <a className="text-link" href="#results">
                  Inspect the sample ↗
                </a>
              </article>
            </div>
            <div className="workspace-foot">
              <span>Fictional document · Source → procedure → decision</span>
              <span>
                {mock
                  ? "Mock API ready / no live model calls"
                  : "Live API mode / temporary key required for AI"}
              </span>
            </div>
          </div>
          <div className="stats">
            <div>
              <strong>10</strong>
              <span>fictional supplier PDFs</span>
            </div>
            <div>
              <strong>4</strong>
              <span>approaches, one problem</span>
            </div>
            <div>
              <strong>9 / 10</strong>
              <span>final development verdicts matched</span>
              <small>
                Includes a later policy change. Not like for like with earlier
                approaches.
              </small>
            </div>
          </div>
        </section>
        <section className="section wrap" id="workflow">
          <SectionHeading
            label="The workflow"
            title="A fixed path through the uncertainty."
          >
            The same order every time. Evidence first, rules next. Unresolved
            cases are intended to go to a person.
          </SectionHeading>
          <ol className="workflow">
            {[
              ["Read the PDF", "Start with the supplier’s actual words."],
              ["Extract facts", "Capture values, quotes and uncertainty."],
              ["Check the rules", "Compare with the request and policy."],
              ["Make a decision", "Approve, reject, or request review."],
              ["Report the evidence", "Show why. Let a person resolve doubt."],
            ].map(([title, body], index) => (
              <li key={title}>
                <span className="step-number">
                  0{index + 1} <span aria-hidden="true">→</span>
                </span>
                <h3>{title}</h3>
                <p>{body}</p>
              </li>
            ))}
          </ol>
          <p className="section-note">
            This is the intended review behavior. Model judgments can still be
            wrong; the limits are part of the result.
          </p>
        </section>
        <section className="section wrap" id="journey">
          <SectionHeading
            label="Four approaches"
            title="Better questions. More useful answers."
          >
            We started with plain code, then tested where AI helped and where
            the hand-off broke.
          </SectionHeading>
          <div className="journey-layout">
            <div>
              {approaches.map((a, index) => (
                <article className="approach" key={a.id}>
                  <span className="approach-number">{index + 1}</span>
                  <div>
                    <div className="approach-heading">
                      <h3>{a.name}</h3>
                      <span>{a.question}</span>
                    </div>
                    <p>{a.idea}</p>
                    <p className="got-right">
                      <span aria-hidden="true">✓</span> {a.right}
                    </p>
                    <p className="got-wrong">
                      <span aria-hidden="true">!</span> {a.wrong}
                    </p>
                    <dl className="metrics">
                      <div>
                        <dt>Verdicts</dt>
                        <dd>{a.verdicts}/10</dd>
                      </div>
                      <div>
                        <dt>Rule sets</dt>
                        <dd>{a.ruleSets}/10</dd>
                      </div>
                      <div>
                        <dt>Facts</dt>
                        <dd>{a.facts}/270</dd>
                      </div>
                      <div>
                        <dt>All ten PDFs</dt>
                        <dd>
                          {index ? "about " : ""}
                          {a.seconds} s · {a.costLabel}
                        </dd>
                      </div>
                    </dl>
                  </div>
                </article>
              ))}
            </div>
            <figure className="chart">
              <figcaption>
                Verdicts that matched
                <span>Recorded development run / out of 10</span>
              </figcaption>
              <div className="bars">
                {approaches.map((a, index) => (
                  <div className="bar-row" key={a.id}>
                    <span>A{index + 1}</span>
                    <div className="bar-track">
                      <div
                        className={index === 3 ? "bar final" : "bar"}
                        style={{ width: `${a.verdicts * 10}%` }}
                      />
                    </div>
                    <strong>
                      {a.verdicts}
                      {index === 3 ? "*" : ""}
                    </strong>
                  </div>
                ))}
              </div>
              <p className="policy-note">
                *A4 includes a policy change after seeing packs 06 and 08. The 9
                versus 7 comparison is not like for like.
              </p>
            </figure>
          </div>
          <div className="audit-strip">
            <strong>0 unsafe approvals in all four observed runs.</strong>
            <span>
              Narrow development evidence, not a safety guarantee. Time and cost
              cover ten PDFs.
            </span>
          </div>
        </section>
        <section className="section wrap" id="results">
          <SectionHeading
            label="The results explorer"
            title="Every sample. Every verdict."
          >
            Compare each answer with the expected verdict. Open a pack to
            inspect the recorded decisions and their source evidence.
          </SectionHeading>
          <ResultsExplorer />
        </section>
        <section className="section wrap" id="run">
          <SectionHeading
            label="The review workspace"
            title="Follow a check from source to result."
          >
            {mock
              ? "Try the streaming mock API, or replay a saved answer locally. Neither calls an AI model."
              : "Run a sample through the same-origin API with your temporary key. Saved replay is always available."}
          </SectionHeading>
          <LiveRun mock={mock} />
        </section>
        <section className="section wrap limits-layout" id="limits">
          <div className="limits-intro">
            <p className="eyebrow">Honest limits</p>
            <h2>
              What these results
              <br />
              can’t tell us.
            </h2>
            <p>
              A useful demonstration should show its boundaries as clearly as
              its best result.
            </p>
            <a href="#results">Revisit the evidence ↑</a>
          </div>
          <div>
            {limits.map(([title, body], index) => (
              <article className="limit" key={title}>
                <span>0{index + 1}</span>
                <div>
                  <h3>{title}</h3>
                  <p>{body}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>
      <footer className="wrap footer">
        <span>Supplier Document Checker / BIAI interview demo</span>
        <div>
          <a href="#" aria-label="GitHub repository, placeholder">
            GitHub ↗ <span className="muted">(placeholder)</span>
          </a>
          <a href="/roadmap.md">Roadmap ↗</a>
          <a href="#main">Back to top ↑</a>
        </div>
      </footer>
    </>
  );
}
