# Production acceptance checklist

## Automated

- [ ] Regression suite green
- [ ] Dependency audit green
- [ ] Security hardening green
- [ ] RLS isolation suite green
- [ ] Browser/WebMCP smoke green
- [ ] Provider smoke green
- [ ] Observability check green
- [ ] Python syntax/compile checks green

## Operational evidence

- [ ] Main branch protection enabled with required status checks
- [ ] Billing webhook deployed and `/readyz` returns success
- [ ] Backup created and restore drill passed
- [ ] Monitoring/alert destination tested
- [ ] Production deployment URL verified

## Commercial/legal

- [ ] Pricing, limits, renewal, cancellation and refund rules published
- [ ] Privacy Policy reviewed for actual processing jurisdictions
- [ ] Terms reviewed for actual pricing/payment model
- [ ] DPA and subprocessor register reviewed
- [ ] Retention periods approved and operationally implemented

## Final rule

A green CI pipeline is necessary but not sufficient for a 10/10 production rating. Manual operational evidence must be attached to the release record before calling the product production-ready.
