# Commercial pilot — AI Agent Content Manager

## Technical state

The product core is designed around:

**catalog → MAX → content → publication → lead/order → analytics → next MAX action**

The current MAX layer is deterministic/free-first. Persistent tenant/user AI usage metering is enabled so future paid-provider calls can be priced per request and per token.

## Pilot acceptance criteria

A pilot shop is considered activated only after all of these are true:

1. Owner can register and enter the shop.
2. At least one real product exists.
3. MAX produces a useful next action.
4. Owner prepares content and publishes at least one item.
5. A real lead/order reaches CRM.
6. Owner returns and uses MAX again.
7. AI/infrastructure cost is recorded.
8. Owner can state a measurable benefit: time saved, more content produced, more leads, or more orders.

## Commercial metrics

Track per tenant:

- activation rate;
- time to first value;
- MAX actions per active shop;
- content prepared/published;
- leads;
- orders;
- revenue;
- AI requests;
- input/output tokens;
- estimated AI cost in RUB;
- gross margin;
- 7/30-day retention.

## Go/no-go rule

Do not scale acquisition before a pilot demonstrates repeated use and a clear willingness to pay.

Technical readiness is not the same as commercial proof. Real users and real provider credentials are required for the pilot/payment stage.
