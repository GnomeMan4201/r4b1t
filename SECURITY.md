# Security Policy

## Reporting a vulnerability

Do **not** open a public issue for a suspected vulnerability that could expose credentials, browsing data, backend controls, or users of the deployed application.

Preferred reporting path:

1. Use **Security → Report a vulnerability** for this repository when GitHub private vulnerability reporting is available.
2. Otherwise email **badbanana@proton.me** with the subject `r4b1t security report`.

Include the affected commit/deployment surface, reproduction steps, expected and observed behavior, impact, and any proposed mitigation. Do not include unrelated credentials, private browsing history, or third-party sensitive data.

## Security-relevant scope

Reports are especially useful for issues involving:

- backend/proxy origin or authorization controls;
- unintended disclosure of request/session data;
- XSS or unsafe rendering of third-party metadata;
- service-worker/PWA cache behavior that exposes stale or unintended content;
- open redirects or URL-handling bugs with a meaningful exploit path;
- rate-limit or cache-boundary failures in deployed metadata/proxy services;
- CI/deployment workflows with unnecessary write or secret access;
- dependency issues affecting the maintained browser test/deployment tooling.

Third-party URLs in the discovery corpus are external resources, not code maintained by this repository. A vulnerability on one of those sites should be reported to that site's operator, not as an r4b1t vulnerability unless r4b1t itself handles the resource unsafely.

## Supported state

Report findings against the current default branch and, for deployment-specific behavior, include the observed deployment URL and date. Corpus reachability changes are normal maintenance events and are not security defects by themselves.

## Disclosure

I aim to acknowledge reproducible reports within seven days. Validation and remediation timing depends on severity and reproducibility; no fixed patch deadline is promised before triage.

Confirmed fixes should be documented when practical. Reporter credit is welcome unless anonymity is requested.
