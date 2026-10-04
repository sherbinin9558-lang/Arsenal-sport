# Arsenal Sport

Professional digital sales and content workspace for a sports store.

## Current core

- Product catalog and product cards
- Smart catalog search
- Content generation for Instagram, Telegram and VK
- Reels workflow
- Content planning
- Basic analytics
- MAX workspace
- Rule-based AI seller
- Telegram seller integration prepared

## Product direction

Arsenal Sport is being developed as a single sales core:

**Catalog → stock → search → AI recommendation → cart → order → CRM → analytics → channels**

### Catalog

Each product can contain:

- name
- brand
- article
- sport
- category
- purpose
- sizes
- size-level stock
- color
- characteristics
- product images
- price
- source
- availability status

Prices are kept in the internal catalog and are not printed on promotional product cards.

### Search and recommendations

The search layer should understand natural customer requests such as:

> бутсы Nike 42 для искусственного поля

and combine product, sport, size, purpose, brand, color, budget and availability signals.

### Sales flow

The target customer flow is:

1. Find a product
2. Open product details
3. Select size
4. Select quantity
5. Add to cart
6. Create an order request
7. Store the lead/order in CRM
8. Notify the manager
9. Track order status

### CRM

Planned statuses:

- New
- Contacted
- Awaiting payment
- Paid
- Preparing
- Shipped
- Completed
- Cancelled

### Analytics

The system should track operational metrics such as:

- searches
- product views
- requests
- cart additions
- order requests
- stock alerts
- content activity
- customer source

## Architecture

The catalog is the source of truth. Content generation, the AI seller, Telegram and future Instagram integrations should use the same product data instead of maintaining separate catalogs.

## Development priorities

1. Professional catalog data model
2. Size-level inventory
3. Advanced filters
4. Better natural-language search
5. Product recommendation
6. Cart and order requests
7. CRM
8. Analytics
9. Telegram channel integration
10. Instagram/Meta integration

## Important

The repository currently contains demonstration catalog data. Real store inventory should be imported later rather than manually recreated inside the application.

## Secrets and local setup

The application reads credentials from Streamlit Secrets or environment variables; real credentials are never required in the repository.

- Local development: create `.streamlit/secrets.toml` and keep it untracked.
- Streamlit Community Cloud: put the same values in the app's Secrets settings.
- Required Supabase keys for production: `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
- Server-side/payment integrations additionally use `SUPABASE_SERVICE_ROLE_KEY` only from server configuration.
- A safe template is provided in `secrets.example.toml`; it contains placeholders only.

## Automated verification

The test suite includes Streamlit `AppTest` smoke coverage for the main application and MAX sections, plus unit/regression coverage for data safety, tenant isolation, concurrency, WebMCP, billing-safe paths, and P2/P3 operations. CI runs Python compilation and the complete unittest suite. Browser/provider smoke checks are read-only and require explicit production secrets before performing live external checks.
