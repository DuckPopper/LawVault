"""Terms & Conditions shown (and scroll-gated) at sign-up. Bump TERMS_VERSION whenever the text changes.

NOTE: this is a solid starting text for a SaaS legal workspace, not legal advice. Have a lawyer review it, and set
LEGAL_ENTITY, SUPPORT_EMAIL and GOVERNING_LAW in .env before going live."""
import html, re
import config
from views.policy import policy

TERMS_VERSION = "2026-11-26"

_TERMS = """
#### 1. Who we are and what this is
These Terms & Conditions ("Terms") are an agreement between you and **{entity}** ("LawVault", "we", "us"). They govern
your use of the LawVault web application and everything in it: cases, documents, calendar, files, news, the AI
assistant, the AI-text detector and voice input (together, the "Service"). By creating an account you confirm you have
read and accepted these Terms and the Privacy Policy below.

#### 2. Not legal advice
LawVault is a workspace and productivity tool. Everything produced by AI features, legal reference text, deadline
calculators and summaries is **general information, not legal advice**, and may be incomplete, outdated or wrong.
Nothing here creates a lawyer-client relationship between you and us. You are responsible for checking outputs against
primary sources and for your own professional judgement.

#### 3. Eligibility and your account
You must be at least 18 and able to enter a binding contract. Give accurate information, keep your password and
authenticator private, and tell us at once if you suspect unauthorised access. You are responsible for activity under
your account. One person per account; do not share logins. We may require two-step sign-in for any account.

#### 4. Your content
You keep all rights to the cases, documents, messages and files you put into LawVault ("Your Content"). You give us a
limited licence to host, encrypt, back up, process and display Your Content solely to run the Service for you and the
people you choose to share with. We do not sell Your Content or use it to train AI models. You confirm that you have
the right to upload it and that doing so does not breach confidentiality, privilege, data-protection or
intellectual-property rules. If you are a lawyer or work with client data, **you** remain responsible for your
professional confidentiality duties and for deciding what is appropriate to upload or send to an AI provider.

#### 5. AI features and third parties
AI features send masked text to third-party AI providers, and voice input sends audio to a speech-to-text provider, as
described in the Privacy Policy. Optional integrations (Google Docs, Google or Apple Calendar, news sources) are
governed by those providers' own terms. The AI-text detector gives a probability estimate only; it can be wrong and
must not be used as the sole basis for any accusation or decision about a person.

#### 6. Acceptable use
You agree not to: break the law or use the Service to help others do so; upload malware; probe, scan or attack the
Service or other users' accounts; try to bypass rate limits, plan limits or security controls; scrape or resell the
Service; upload content you have no right to hold; harass others; or use AI output to mislead a court, regulator or
client. We may suspend or remove accounts that put the Service or other users at risk.

#### 7. Plans, payment and cancellation
Free and paid plans, their limits and prices are shown in the app and may change with reasonable notice. Paid plans
renew until cancelled; you can cancel at any time and keep access until the end of the paid period. Unless the law
says otherwise, fees already paid are non-refundable. Taxes are added where required.

#### 8. Availability and security
We use encryption at rest, hashed passwords, two-step sign-in, session controls and audit logging, and we work to keep
the Service available. No online service is perfectly secure or uninterrupted. The Service is provided as is, and we
may change, pause or retire features. Keep your own copies of anything important; you can export your data at any time
from Settings → Privacy.

#### 9. Ending your account
You may delete your account at any time from Settings → Account; this permanently deletes Your Content from our active
systems. We may suspend or end your access if you break these Terms or the law, with notice where reasonable.
Sections that by nature should survive (for example 2, 4, 10, 11 and 12) survive termination.

#### 10. Disclaimers
To the maximum extent the law allows, the Service is provided **"as is" and "as available"**, without warranties of
any kind, including accuracy, fitness for a particular purpose and non-infringement. Nothing in these Terms limits
rights you have under mandatory consumer or data-protection law.

#### 11. Limitation of liability
To the maximum extent the law allows, we are not liable for indirect, incidental or consequential loss, loss of profit,
missed deadlines, lost cases or reliance on AI output. Our total liability for any claim relating to the Service is
limited to the amount you paid us in the 12 months before the claim (or, on the free plan, a nominal sum). This does not
exclude liability that cannot be excluded by law, such as for fraud or wilful misconduct.

#### 12. Changes, law and contact
We may update these Terms; for material changes we will ask you to accept the new version, and continuing to use the
Service after that means you accept it. These Terms are governed by the laws of {law}, and the courts of that
jurisdiction have exclusive jurisdiction, subject to any mandatory consumer rights where you live. Questions, privacy
requests or legal notices: {contact}.

#### Privacy Policy
"""


def _md(text: str) -> str:
    """Tiny markdown -> HTML for the policy text ('#### ' headings, **bold**, paragraphs)."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if block.startswith("#### "):
            head, _, rest = block.partition("\n")
            out.append(f"<h4>{html.escape(head[5:])}</h4>")
            block = rest.strip()
            if not block:
                continue
        esc = html.escape(block).replace("\n", " ")
        out.append("<p>" + re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc) + "</p>")
    return "".join(out)


def terms_html() -> str:
    contact = config.SUPPORT_EMAIL or "the support contact shown in the app"
    body = _TERMS.format(entity=config.LEGAL_ENTITY, law=config.GOVERNING_LAW, contact=contact)
    return (f'<h3>Terms &amp; Conditions</h3><p class="m">Version {TERMS_VERSION}</p>'
            + _md(body) + _md(policy()))
