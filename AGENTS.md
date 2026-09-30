# Repository instructions

## Work with the user

- Respond in Korean. Follow the latest intent and distinguish confirmed decisions, proposals, and open questions.
- Complete authorized, reversible work without repeatedly asking permission. Ask only when a consequential missing decision blocks the task; continue independent work.
- Inspect `git status --short` before edits. Preserve unrelated changes, including `.claude/settings.local.json`.
- Do not spawn agents unless explicitly requested. Writing `AGENTS.md` does not authorize delegation.
- Never put credentials, production records, or personal conversation data in docs, fixtures, logs, or commits.

## Active product: AI shaman

- Read [product direction and handoff](docs/ai-shaman/README.md) before new-product work.
- Build a **mobile-first responsive web app**, usable in a mobile browser without installation. Read [BRAND.md](BRAND.md) and [DESIGN.md](DESIGN.md) for UI work, checking their decision status first. Mobile touch and narrow screens are primary; desktop must also work. Native apps, installable PWA, offline support, and push are not implied requirements.
- On 2026-09-30 the user said the deployed home resembles Poomang too much and requested brand planning before more redesign. Retain readable mobile discovery, but do not treat the reference's banner/chip/card/mascot arrangement as the permanent design system. The user confirmed keeping the brand name 새롱. The user subsequently authorized applying the calm, warm ink/coral direction to the homepage. Individual service names, final logo, and character remain undecided.
- The user proposed women in their 30s–50s as a possible audience and requested an appropriate brand impression. This is a hypothesis to assess, not verified demand or a universal aesthetic preference. The current recommendation is initial validation with women in their 30s–40s, usability through the 50s, and a calm, warm, trustworthy impression. See BRAND.md for evidence and limits; do not infer authorization to build every mentioned fortune/saju/naming service.
- The user authorized the brand redesign. Homepage, browsing, saved items, and scripted preview now use shared [semantic tokens](static/css/brand-tokens.css) in local code; deployment has not occurred. The [review board](docs/brand/preview.html) shares the same tokens but its result screen is still only a sample.
- Reuse semantic color, type, spacing, and component rules. `static/css/brand-tokens.css` is the single value source; the old docs token path is an import-only compatibility entry.
- The current homepage has four explicitly scripted conversation examples, category/search controls, and browser-local saved card IDs. Those example topics are not a confirmed production domain or four independently implemented AI services. Do not store conversation answers.
- The product is an **AI shaman character that adaptively asks questions and infers the concern the user has in mind**. Akinator is an interaction reference: update candidate concerns after answers, select useful next questions, and offer a guess the user can confirm or correct. Do not claim to reproduce its proprietary algorithm.
- The evolving question-and-inference experience is central. Do not replace it with a fixed personality quiz, generic chatbot, or birth-date form followed by a long generated fortune report.
- Fortune-telling, saju, and naming were exploratory examples, not an approved feature list. Do not build a multi-menu fortune portal or add saju/naming requirements by default.
- The goal is a small independently operated business earning a few million KRW monthly with gradual marketing. Exact target, revenue versus profit, budget, pricing, and acquisition channels remain undecided. Earlier numerical examples are not forecasts or requirements.
- The former [data-service proposal](docs/data-service/README.md) is historical and inactive. Its architecture, tasks, field selection, and model handoff prompts are not the current plan. Resume it only if requested.

## Design and implementation discipline

- Distinguish concern hypotheses, answers, next-question selection, stopping/confirmation logic, and character presentation. The concrete implementation is still a design proposal.
- Prefer a small inspectable inference mechanism before model training or complex infrastructure. An LLM may phrase questions and interpretations; fluent prose must not masquerade as tracked inference state.
- Questions should help distinguish remaining hypotheses. Avoid repetition or simply asking the exact answer and presenting it as a surprising discovery.
- Handle uncertainty, skipped or contradictory answers, corrections, overlapping concerns, and concerns outside the candidate set. Do not force a confident guess when evidence is weak.
- Internal weights are not measured accuracy or a scientific diagnosis. Do not display invented confidence percentages or claim supernatural knowledge of private facts.
- Preserve the shaman persona while making results identifiable as answer-based entertainment. Do not use fabricated dangers or guaranteed outcomes to pressure payment.
- Treat free text as untrusted data. Collect only necessary personal information; birth details, names, and permanent storage of sensitive concerns are not default requirements.
- Keep one complete experience first. Do not silently treat a proposed concern domain, question count, price, model, payment provider, retention period, or deployment target as user-confirmed.
- Define difficult contracts and acceptance examples so a less expensive model can implement bounded tasks. Read only task-relevant documents. Do not change model settings without a request.
- The user authorized implementing the mobile-first homepage, removing Work service routes, and moving TDM to `/tdm/` without homepage links. The AI inference engine and payments remain unimplemented. Keep actual feature status explicit; do not deploy without session authorization.
- Update the active handoff with actual progress and unresolved decisions. Proposed code, simulated metrics, and untested algorithms are not implemented or validated features.

## Existing application

- This repository serves an existing FastAPI application, including the new brand homepage and a clearly labeled scripted conversation preview. The AI shaman inference product is not implemented here.
- Existing stack: FastAPI, SQLAlchemy async/PostgreSQL, Alembic, Jinja2, JavaScript modules, and CSS. See [README](README.md). This does not automatically determine the new product stack.
- Preserve existing routes, tables, authentication, ML dependencies, and deployment behavior in unrelated work. `/dusttest/` was removed.
- Work and farm routers are retired from the public application; do not restore them unintentionally. Keep their stored data and uploads intact. TDM lives at `/tdm/`; legacy `/tdmprediction/*` redirects preserve request methods. Keep TDM authentication and exclude it from homepage navigation.
- [Deployment notes](deploy/README.md) and `CLAUDE_SESSION_CONTEXT.md` contain historical information. Verify current configuration before deployment.
- Do not use the production database for new-product tests or migrations.

## Validation and completion

- Documentation: check local links, conflicting decisions, unresolved requirements, and `git diff --check`. Do not run application or production checks solely for prose changes.
- Inference code: check different answer paths, ambiguity/no match, contradictory answers, corrections, repeated-question avoidance, and bounded termination. Model calls need failure handling and usage bounds.
- Separate algorithm simulation from user evidence. Synthetic scenarios do not prove users feel understood, will pay, or return.
- Once relevant checks pass, avoid repeated broad tests without a new concern.
- Report changes, verification, and material uncertainty. Never claim a deployment or model switch that did not happen.
